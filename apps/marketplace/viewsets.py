from rest_framework import viewsets, status, filters, permissions, pagination, exceptions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.serializers import ValidationError as DRFValidationError
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models
from django.db.models import Count, Q, Exists, OuterRef, Prefetch, F
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import (
    MarketplaceCategory, MarketplaceProvider, MarketplaceService, 
    ServiceBooking, ServiceReview, ServiceFavorite, MarketplaceMessage,
    ProviderDocument, ServiceImage, ServicePackage, ServiceAvailability
)
from .serializers import *
from .services import BookingManager, MarketplaceServiceManager, ProviderManager, ReviewManager
from .permissions import IsProviderOwner, IsServiceOwner, IsBookingParticipant, IsVerifiedProvider
from .filters import MarketplaceServiceFilter, ProviderFilter
from apps.subscriptions.iap_service import verify_google_purchase

class MarketplacePagination(pagination.PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class MarketplaceCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MarketplaceCategory.objects.filter(is_active=True).annotate(
        children_count=Count('subcategories'),
        services_count=Count('services', filter=Q(services__status='PUBLISHED'))
    ).order_by('name')
    serializer_class = MarketplaceCategoryListSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = []

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return MarketplaceCategoryDetailSerializer
        return self.serializer_class


class MarketplaceProviderViewSet(viewsets.ModelViewSet):
    queryset = MarketplaceProvider.objects.filter(is_deleted=False)
    serializer_class = ProviderListSerializer
    filterset_class = ProviderFilter
    search_fields = ['business_name', 'description', 'city']
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    throttle_classes = []

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == 'retrieve':
            return qs.annotate(
                total_services=Count('services', filter=Q(services__is_deleted=False))
            )
        return qs

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProviderDetailSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return ProviderCreateUpdateSerializer
        return self.serializer_class

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated], url_path='my_profile')
    def my_profile(self, request):
        try:
            provider = request.user.marketplace_profile
            serializer = ProviderDetailSerializer(provider)
            return Response(serializer.data)
        except MarketplaceProvider.DoesNotExist:
            return Response({'error': 'You do not have a provider profile.'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser], url_path='verify')
    def verify(self, request, pk=None):
        provider = self.get_object()
        ProviderManager.verify_provider(provider, reviewer=request.user)
        return Response({'status': 'Provider verified'})



class MarketplaceServiceViewSet(viewsets.ModelViewSet):
    queryset = MarketplaceService.objects.filter(is_deleted=False)
    serializer_class = MarketplaceServiceListSerializer
    filterset_class = MarketplaceServiceFilter
    pagination_class = MarketplacePagination
    ordering_fields = ['created_at', 'base_price', 'average_rating', 'views_count', 'bookings_count']
    search_fields = ['title', 'description', 'summary', 'provider__business_name']
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == 'retrieve':
            qs = qs.prefetch_related(
                'images', 'packages', 'availabilities', 
                Prefetch('reviews', queryset=ServiceReview.objects.select_related('reviewer'))
            )
        
        if self.request.user.is_authenticated:
            is_fav = ServiceFavorite.objects.filter(user=self.request.user, service=OuterRef('pk'))
            qs = qs.annotate(is_favorited=Exists(is_fav))
            
        return qs

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return MarketplaceServiceDetailSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return MarketplaceServiceCreateUpdateSerializer
        return self.serializer_class

    def perform_create(self, serializer):
        if not hasattr(self.request.user, 'marketplace_profile'):
            raise ValidationError({'error': 'You must have a provider profile to create a service.'})
        serializer.save(provider=self.request.user.marketplace_profile)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated], url_path='favorite')
    def favorite(self, request, pk=None):
        service = self.get_object()
        favorite, created = ServiceFavorite.objects.get_or_create(user=request.user, service=service)
        if created:
            service.favorites_count = models.F('favorites_count') + 1
            service.save(update_fields=['favorites_count'])
            return Response({'status': 'Service added to favorites'}, status=status.HTTP_201_CREATED)
        return Response({'status': 'Service already in favorites'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated], url_path='unfavorite')
    def unfavorite(self, request, pk=None):
        service = self.get_object()
        deleted, _ = ServiceFavorite.objects.filter(user=request.user, service=service).delete()
        if deleted:
            service.favorites_count = models.F('favorites_count') - 1
            service.save(update_fields=['favorites_count'])
            return Response({'status': 'Service removed from favorites'}, status=status.HTTP_204_NO_CONTENT)
        return Response({'status': 'Service was not in favorites'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsServiceOwner], url_path='publish')
    def publish(self, request, pk=None):
        service = self.get_object()
        MarketplaceServiceManager.publish_service(service)
        return Response({'status': 'Service published'})

    @action(detail=True, methods=['get', 'post'], permission_classes=[permissions.IsAuthenticated], url_path='availability')
    def availability(self, request, pk=None):
        service = self.get_object()
        
        if request.method == 'GET':
            availabilities = service.availabilities.all()
            serializer = ServiceAvailabilitySerializer(availabilities, many=True)
            return Response(serializer.data)
        
        # POST logic: Manage availability
        if not IsServiceOwner().has_object_permission(request, self, service):
            return Response({'error': 'Seul le propriétaire du service peut modifier la disponibilité.'}, status=status.HTTP_403_FORBIDDEN)
            
        is_many = isinstance(request.data, list)
        serializer = ServiceAvailabilitySerializer(data=request.data, many=is_many)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        if is_many:
            for item in serializer.validated_data:
                ServiceAvailability.objects.update_or_create(
                    service=service,
                    date=item['date'],
                    start_time=item.get('start_time'),
                    defaults={
                        'end_time': item.get('end_time'),
                        'is_available': item.get('is_available', True)
                    }
                )
        else:
            item = serializer.validated_data
            ServiceAvailability.objects.update_or_create(
                service=service,
                date=item['date'],
                start_time=item.get('start_time'),
                defaults={
                    'end_time': item.get('end_time'),
                    'is_available': item.get('is_available', True)
                }
            )
            
        return Response({'status': 'Disponibilité mise à jour'})

    @action(detail=True, methods=['post'], url_path='increment_view')
    def increment_view(self, request, pk=None):
        service = self.get_object()
        MarketplaceServiceManager.increment_view(service)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='featured')
    def featured(self, request):
        featured_services = self.get_queryset().filter(is_featured=True, status='PUBLISHED')[:10]
        serializer = self.get_serializer(featured_services, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='popular')
    def popular(self, request):
        popular_services = self.get_queryset().filter(status='PUBLISHED').annotate(
            popularity_score=F('bookings_count') + F('favorites_count')
        ).order_by('-popularity_score')[:10]
        serializer = self.get_serializer(popular_services, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated], url_path='new')
    def new(self, request):
        return Response({
            'message': 'Ready to create a new service',
            'allowed_methods': ['POST']
        })

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated], url_path='my_services')
    def my_services(self, request):
        if not hasattr(request.user, 'marketplace_profile'):
            return Response({'error': 'You do not have a provider profile.'}, status=status.HTTP_404_NOT_FOUND)
        
        provider = request.user.marketplace_profile
        services = self.get_queryset().filter(provider=provider)
        page = self.paginate_queryset(services)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(services, many=True)
        return Response(serializer.data)


class ServiceReviewViewSet(viewsets.ModelViewSet):
    queryset = ServiceReview.objects.all()
    serializer_class = ServiceReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        """
        Filtre les reviews selon les paramètres de la requête.
        Supporte:
        - service: UUID du service
        - user: ID de l'utilisateur
        - rating: note minimum
        """
        queryset = super().get_queryset()
        
        # Filtrer par service (UUID)
        service_id = self.request.query_params.get('service')
        if service_id:
            queryset = queryset.filter(service_id=service_id)
        
        # Filtrer par utilisateur
        user_id = self.request.query_params.get('user')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Filtrer par note minimum
        min_rating = self.request.query_params.get('min_rating')
        if min_rating:
            try:
                queryset = queryset.filter(rating__gte=int(min_rating))
            except ValueError:
                pass
        
        # Filtrer par note maximum
        max_rating = self.request.query_params.get('max_rating')
        if max_rating:
            try:
                queryset = queryset.filter(rating__lte=int(max_rating))
            except ValueError:
                pass
        
        return queryset

    def get_serializer_class(self):
        if self.action == 'create':
            return ServiceReviewCreateSerializer
        return self.serializer_class

    def perform_create(self, serializer):
        service = serializer.validated_data['service']
        ReviewManager.create_review(service, self.request.user, serializer.validated_data)


class ServiceBookingViewSet(viewsets.ModelViewSet):
    queryset = ServiceBooking.objects.all()
    serializer_class = ServiceBookingListSerializer
    permission_classes = [permissions.IsAuthenticated, IsBookingParticipant]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return super().get_queryset()
        return super().get_queryset().filter(Q(customer=user) | Q(service__provider__user=user))

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ServiceBookingDetailSerializer
        if self.action == 'create':
            return ServiceBookingCreateSerializer
        return self.serializer_class

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self.perform_create(serializer)

    def perform_create(self, serializer):
        service = serializer.validated_data['service']
        result = BookingManager.create_booking(service, self.request.user, serializer.validated_data)
        
        if not result.get('success'):
            return Response({'success': False, 'message': result.get('message')}, status=status.HTTP_200_OK)
        
        return Response({'success': True, 'data': ServiceBookingListSerializer(result.get('booking')).data}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[IsServiceOwner])
    def confirm(self, request, pk=None):
        booking = self.get_object()
        BookingManager.confirm_booking(booking)
        return Response({'status': 'Booking confirmed'})

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        reason = request.data.get('reason', '')
        BookingManager.cancel_booking(booking, reason)
        return Response({'status': 'Booking cancelled'})

    @action(detail=True, methods=['post'], permission_classes=[IsServiceOwner])
    def complete(self, request, pk=None):
        booking = self.get_object()
        BookingManager.complete_booking(booking)
        return Response({'status': 'Booking completed'})

    @action(detail=True, methods=['post'], url_path='verify_google_play_payment')
    def verify_google_play_payment(self, request, pk=None):
        booking = self.get_object()
        package_name = request.data.get('package_name')
        product_id = request.data.get('product_id')
        token = request.data.get('token')
        
        if not all([package_name, product_id, token]):
            return Response({'error': 'Missing parameters'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = verify_google_purchase(package_name, product_id, token, is_subscription=False)
            
            if result.get('purchaseState') == 0:
                BookingManager.process_booking_payment(
                    booking=booking,
                    transaction_id=token,
                    payment_method='google_play',
                    raw_data=result
                )
                return Response({'status': 'success', 'reference': booking.reference})
            return Response({'error': 'L\'achat n\'est pas validé par Google Play.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ServiceFavoriteViewSet(viewsets.ModelViewSet):
    serializer_class = ServiceFavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ServiceFavorite.objects.filter(user=self.request.user).select_related('service', 'service__provider', 'service__category')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def my_favorites(self, request):
        return self.list(request)


class MarketplaceMessageViewSet(viewsets.ModelViewSet):
    serializer_class = MarketplaceMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Privacy fix: Only see messages where I am sender or receiver
        return MarketplaceMessage.objects.filter(
            Q(sender=self.request.user) | Q(receiver=self.request.user)
        ).select_related('sender', 'receiver', 'booking').order_by('created_at')

    def perform_create(self, serializer):
        # Automatically set the sender to the current user
        serializer.save(sender=self.request.user)

    @action(detail=False, methods=['get'])
    def conversation(self, request):
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({'error': 'user_id parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        messages = MarketplaceMessage.objects.filter(
            (Q(sender=self.request.user) & Q(receiver_id=user_id)) |
            (Q(sender_id=user_id) & Q(receiver=self.request.user))
        ).select_related('sender', 'receiver', 'booking').order_by('created_at')
        
        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_chats(self, request):
        # Get all users who have sent or received messages from the current user
        sent_to = MarketplaceMessage.objects.filter(sender=request.user).values_list('receiver', flat=True)
        received_from = MarketplaceMessage.objects.filter(receiver=request.user).values_list('sender', flat=True)
        
        user_ids = set(list(sent_to) + list(received_from))
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        users = User.objects.filter(id__in=user_ids)
        
        chat_list = []
        for user in users:
            last_msg = MarketplaceMessage.objects.filter(
                (Q(sender=request.user) & Q(receiver=user)) |
                (Q(sender=user) & Q(receiver=request.user))
            ).order_by('-created_at').first()
            
            chat_list.append({
                'user_id': user.id,
                'user_name': user.full_name if hasattr(user, 'full_name') else user.username,
                'user_avatar': user.avatar.url if hasattr(user, 'avatar') and user.avatar else None,
                'last_message': last_msg.message if last_msg else "",
                'last_message_time': last_msg.created_at if last_msg else None,
                'unread_count': MarketplaceMessage.objects.filter(sender=user, receiver=request.user, is_read=False).count()
            })
        
        # Sort by last message time
        chat_list.sort(key=lambda x: x['last_message_time'] or timezone.now(), reverse=True)
        
        return Response(chat_list)

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        message = self.get_object()
        if message.receiver == request.user:
            message.is_read = True
            message.save()
            return Response({'status': 'Message marked as read'})
        return Response({'error': 'You are not the receiver of this message'}, status=status.HTTP_403_FORBIDDEN)
