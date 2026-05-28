"""
Subscription ViewSets for Django REST Framework
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from .models import SubscriptionPlan, UserSubscription, PremiumFeature, UserPremiumFeature
from .serializers import (
    SubscriptionPlanSerializer, UserSubscriptionSerializer,
    PremiumFeatureSerializer, UserPremiumFeatureSerializer
)
from .services import SubscriptionService, PremiumFeatureService, SubscriptionAnalyticsService
from apps.core.permissions import IsSubscriptionOwner


class SubscriptionPlanViewSet(viewsets.ReadOnlyModelViewSet):
    """View all available subscription plans."""
    queryset = SubscriptionPlan.objects.filter(is_active=True)
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [permissions.AllowAny]

    def list(self, request, *args, **kwargs):
        """List subscription plans with user-specific eligibility info."""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        # Add eligibility info for each plan
        for plan_data in serializer.data:
            plan_id = plan_data['id']
            plan = SubscriptionPlan.objects.get(id=plan_id)
            plan_data['is_eligible'] = SubscriptionService.is_user_eligible_for_plan(request.user, plan)
        
        return Response(serializer.data)
    
    def retrieve(self, request, *args, **kwargs):
        """Retrieve a subscription plan with eligibility info."""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        plan_data = serializer.data
        plan_data['is_eligible'] = SubscriptionService.is_user_eligible_for_plan(request.user, instance.id)
        return Response(plan_data)
    
    @action(detail=True, methods=['get'], url_path='features', permission_classes=[permissions.IsAuthenticated])
    def features(self, request, *args, **kwargs):
        """Get features included in a subscription plan."""
        instance = self.get_object()
        features = SubscriptionService.get_plan_features(instance)
        return Response(features)
    
    @action(detail=True, methods=['get'], url_path='eligibility', permission_classes=[permissions.IsAuthenticated])
    def eligibility(self, request, *args, **kwargs):
        """Check if user is eligible for a subscription plan."""
        instance = self.get_object()
        is_eligible = SubscriptionService.is_user_eligible_for_plan(request.user, instance.id)
        return Response({'is_eligible': is_eligible})
    
    @action(detail=True, methods=['get'], url_path='pricing', permission_classes=[permissions.AllowAny])
    def pricing(self, request, *args, **kwargs):
        """Get pricing details for a subscription plan."""
        instance = self.get_object()
        pricing = SubscriptionService.get_plan_pricing(instance)
        return Response(pricing)
    
    


class UserSubscriptionViewSet(viewsets.ViewSet):
    """User subscription management."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSubscriptionSerializer
    
    @action(detail=False, methods=['get'], url_path='my-subscription', permission_classes=[permissions.IsAuthenticated])
    def my_subscription(self, request):
        """Get current user's active subscription."""
        subscription = SubscriptionService.get_active_subscription(request.user)
        if subscription:
            serializer = UserSubscriptionSerializer(subscription)
            return Response(serializer.data)
        return Response({'subscription': None, 'tier': 'free'})
    
    @action(detail=False, methods=['post'], url_path='subscribe', permission_classes=[permissions.IsAuthenticated])
    def subscribe(self, request):
        """Subscribe user to a plan."""
        plan_tier = request.data.get('plan_tier')
        currency = request.data.get('currency', 'HTG')
        
        try:
            plan = SubscriptionPlan.objects.get(tier=plan_tier, is_active=True)
            subscription = SubscriptionService.subscribe_user(
                request.user,
                plan,
                currency=currency
            )
            serializer = UserSubscriptionSerializer(subscription)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except SubscriptionPlan.DoesNotExist:
            return Response({'error': 'Plan not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], url_path='cancel', permission_classes=[permissions.IsAuthenticated])
    def cancel(self, request):
        """Cancel active subscription."""
        subscription = SubscriptionService.get_active_subscription(request.user)
        
        if not subscription:
            return Response({'error': 'No active subscription'}, status=status.HTTP_400_BAD_REQUEST)
        
        SubscriptionService.cancel_subscription(subscription)
        return Response({'status': 'subscription cancelled'})
    
    @action(detail=False, methods=['post'], url_path='pause', permission_classes=[permissions.IsAuthenticated])
    def pause(self, request):
        """Pause active subscription."""
        subscription = SubscriptionService.get_active_subscription(request.user)
        
        if not subscription:
            return Response({'error': 'No active subscription'}, status=status.HTTP_400_BAD_REQUEST)
        
        SubscriptionService.pause_subscription(subscription)
        return Response({'status': 'subscription paused'})
    
    @action(detail=False, methods=['post'], url_path='resume', permission_classes=[permissions.IsAuthenticated])
    def resume(self, request):
        """Resume paused subscription."""
        subscription = SubscriptionService.get_active_subscription(request.user)
        
        if not subscription or subscription.status != 'paused':
            return Response(
                {'error': 'No paused subscription to resume'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        SubscriptionService.resume_subscription(subscription)
        return Response({'status': 'subscription resumed'})
    
    @action(detail=False, methods=['get'], url_path='features', permission_classes=[permissions.IsAuthenticated])
    def features(self, request):
        """Get available features for user's subscription."""
        features = SubscriptionAnalyticsService.get_user_subscription_features(request.user)
        return Response(features)

    @action(detail=False, methods=['post'], url_path='verify-iap', permission_classes=[permissions.IsAuthenticated])
    def verify_iap(self, request):
        """Verify Google Play In-App Purchase and update subscription."""
        token = request.data.get('purchase_token')
        product_id = request.data.get('product_id')  # e.g., "arkevent_pro_monthly"
        package_name = request.data.get('package_name', "com.arkevent.app")
        
        if not token or not product_id:
            return Response(
                {'error': 'purchase_token and product_id are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # 1. Validate with Google
            result = verify_google_purchase(package_name, product_id, token)

            # 2. Extract expiration date
            expiry_millis = int(result.get('expiryTimeMillis', 0))
            expiry_date = datetime.fromtimestamp(expiry_millis / 1000.0, tz=timezone.utc)

            if expiry_date < datetime.now(timezone.utc):
                return Response({'error': 'Subscription has expired'}, status=status.HTTP_400_BAD_REQUEST)

            # 3. Identify the corresponding plan
            target_tier = None
            for tier, _ in SubscriptionPlan.TIER_CHOICES:
                if tier != 'free' and tier in product_id.lower():
                    target_tier = tier
                    break
            
            if not target_tier:
                target_tier = 'pro'
                
            try:
                plan = SubscriptionPlan.objects.get(tier=target_tier)
            except SubscriptionPlan.DoesNotExist:
                return Response({'error': f'Plan tier {target_tier} not found in database'}, status=status.HTTP_404_NOT_FOUND)

            # 4. Create or update subscription
            from django.utils import timezone as django_timezone
            
            subscription, created = UserSubscription.objects.update_or_create(
                user=request.user,
                defaults={
                    'plan': plan,
                    'status': 'active',
                    'purchase_token': token,
                    'order_id': result.get('orderId'),
                    'expiry_date': expiry_date,
                    'renewal_date': expiry_date.date(),
                    'end_date': expiry_date.date(),
                    'amount_paid': 0,
                    'currency': 'USD',
                }
            )
            
            if created or not subscription.start_date:
                subscription.start_date = django_timezone.now().date()
                subscription.save()

            serializer = UserSubscriptionSerializer(subscription)
            return Response(serializer.data)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PremiumFeatureViewSet(viewsets.ReadOnlyModelViewSet):
    """Browse available premium features."""
    queryset = PremiumFeature.objects.filter(is_active=True)
    serializer_class = PremiumFeatureSerializer
    permission_classes = [permissions.AllowAny]


class UserPremiumFeatureViewSet(viewsets.ViewSet):
    """Purchase and manage premium features."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserPremiumFeatureSerializer
    
    @action(detail=False, methods=['post'], url_path='purchase', permission_classes=[permissions.IsAuthenticated])
    def purchase(self, request):
        """Purchase a premium feature."""
        feature_id = request.data.get('feature_id')
        event_id = request.data.get('event_id')
        currency = request.data.get('currency', 'HTG')
        
        try:
            feature = PremiumFeature.objects.get(id=feature_id)
            event = None
            if event_id:
                from apps.events.models import Event
                event = Event.objects.get(id=event_id)
            
            user_premium = PremiumFeatureService.purchase_premium_feature(
                request.user,
                feature,
                event=event,
                currency=currency
            )
            serializer = UserPremiumFeatureSerializer(user_premium)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], url_path='my-features', permission_classes=[permissions.IsAuthenticated])
    def my_features(self, request):
        """Get user's active premium features."""
        features = PremiumFeatureService.get_active_premium_features(request.user)
        serializer = UserPremiumFeatureSerializer(features, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='my-event-features', permission_classes=[permissions.IsAuthenticated])
    def my_event_features(self, request):
        """Get premium features for specific event."""
        event_id = request.query_params.get('event_id')
        
        if not event_id:
            return Response({'error': 'event_id required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from apps.events.models import Event
            event = Event.objects.get(id=event_id)
            features = PremiumFeatureService.get_active_premium_features(request.user, event=event)
            serializer = UserPremiumFeatureSerializer(features, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], url_path='available-for-purchase', permission_classes=[permissions.IsAuthenticated])
    def available_for_purchase(self, request):
        """Get features available to purchase."""
        features = PremiumFeature.objects.filter(is_active=True)
        serializer = PremiumFeatureSerializer(features, many=True)
        return Response(serializer.data)
