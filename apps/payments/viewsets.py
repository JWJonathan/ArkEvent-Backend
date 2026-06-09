"""
Merged DRF ViewSets for Payments
Consolidates logic from views.py and original viewsets.py.
"""

from rest_framework import viewsets, status, permissions as drf_permissions, filters, serializers
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated, AllowAny, BasePermission
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db import models, transaction
from django.db.models import Sum
from django.utils import timezone
from django.conf import settings

from apps.events.models import Event, EventOrganizer
from apps.tickets.models import Ticket, TicketType
from apps.wallets.models import Wallet, Deposit
from apps.wallets.services import WalletService
from apps.subscriptions.iap_service import verify_google_purchase
from apps.subscriptions.models import SubscriptionPlan
from apps.marketplace.models import ServiceBooking

from .models import (
    CommissionRule, TicketSale, Invoice, PaymentMethod, RefundRequest, Order, Payment, OrderItem
)
from .serializers import (
    CommissionRuleSerializer, TicketSaleSerializer, InvoiceSerializer,
    PaymentMethodSerializer, RefundRequestSerializer, OrderSerializer, PaymentSerializer, OrderItemSerializer
)
from .services import PaymentService
from .providers.stripe import StripeProvider
from .providers.moncash import MonCashProvider
from .providers.paypal import PayPalProvider
from apps.core.permissions import (
    IsWalletOwner, IsAccountOwner, CanProcessRefund, IsOrganizer, IsAdmin
)

# --- Permissions ---

class IsOrderOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.is_staff or obj.user == request.user


# --- ViewSets ---

class CommissionRuleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API for viewing commission rules.
    Only authenticated users can view.
    """
    queryset = CommissionRule.objects.filter(is_active=True)
    serializer_class = CommissionRuleSerializer
    permission_classes = [drf_permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['commission_type', 'subscription_tier']
    ordering_fields = ['created_at']
    ordering = ['-created_at']


class TicketSaleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API for viewing ticket sales.
    Organizers see their own sales, buyers see their purchases.
    """
    serializer_class = TicketSaleSerializer
    permission_classes = [drf_permissions.IsAuthenticated, IsAccountOwner]
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_fields = ['event', 'payment_status', 'currency']
    ordering_fields = ['created_at', 'total_amount_paid']
    ordering = ['-created_at']
    search_fields = ['event__title', 'buyer__email']
    
    def get_queryset(self):
        user = self.request.user
        # Buyers see their purchases
        buyer_sales = TicketSale.objects.filter(buyer=user)
        # Organizers see sales for their events
        org_sales = TicketSale.objects.filter(
            event__organization__created_by=user
        )
        # Admin sees all
        if user.is_staff:
            return TicketSale.objects.all()
        return buyer_sales | org_sales
    
    @action(detail=False, methods=['get'])
    def my_purchases(self, request):
        """Get current user's ticket purchases."""
        sales = TicketSale.objects.filter(buyer=request.user)
        serializer = self.get_serializer(sales, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_sales(self, request):
        """Get ticket sales for current user's events."""
        sales = TicketSale.objects.filter(
            event__organization__created_by=request.user
        )
        serializer = self.get_serializer(sales, many=True)
        return Response(serializer.data)


class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API for viewing invoices.
    Users see their own invoices.
    """
    serializer_class = InvoiceSerializer
    permission_classes = [drf_permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_fields = ['invoice_type', 'currency']
    ordering_fields = ['issued_at']
    ordering = ['-issued_at']
    search_fields = ['invoice_number', 'buyer__email']
    
    def get_queryset(self):
        user = self.request.user
        # Users see invoices where they're buyer or seller
        if user.is_staff:
            return Invoice.objects.all()
        return Invoice.objects.filter(buyer=user) | Invoice.objects.filter(seller__created_by=user)


class PaymentMethodViewSet(viewsets.ModelViewSet):
    """
    API for managing payment methods.
    Users manage their own payment methods only.
    """
    serializer_class = PaymentMethodSerializer
    permission_classes = [drf_permissions.IsAuthenticated, IsAccountOwner]
    filter_backends = [OrderingFilter]
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return PaymentMethod.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Set payment method as default."""
        payment_method = self.get_object()
        
        # Remove default from all other methods
        PaymentMethod.objects.filter(user=request.user, is_default=True).update(is_default=False)
        
        # Set this as default
        payment_method.is_default = True
        payment_method.save()
        
        return Response({'status': 'default payment method set'})


class RefundRequestViewSet(viewsets.ViewSet):
    """
    API for refund requests.
    Buyers create requests, staff processes them.
    """
    permission_classes = [drf_permissions.IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def request_refund(self, request):
        """Request a refund for a ticket."""
        ticket_sale_id = request.data.get('ticket_sale_id')
        reason = request.data.get('reason')
        description = request.data.get('description', '')
        
        ticket_sale = get_object_or_404(TicketSale, id=ticket_sale_id)
        
        # Verify buyer
        if ticket_sale.buyer != request.user:
            return Response(
                {'error': 'Only the buyer can request a refund'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Create refund request
        refund_request = RefundRequest.objects.create(
            ticket_sale=ticket_sale,
            requester=request.user,
            refund_amount=ticket_sale.total_amount_paid,
            refund_reason=reason,
            reason_description=description,
            status='pending'
        )
        
        serializer = RefundRequestSerializer(refund_request)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'], permission_classes=[drf_permissions.IsAuthenticated])
    def my_refund_requests(self, request):
        """Get user's refund requests."""
        refunds = RefundRequest.objects.filter(requester=request.user)
        serializer = RefundRequestSerializer(refunds, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[CanProcessRefund])
    def pending_refunds(self, request):
        """Get pending refund requests (staff only)."""
        refunds = RefundRequest.objects.filter(status='pending')
        serializer = RefundRequestSerializer(refunds, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], permission_classes=[CanProcessRefund])
    def approve_refund(self, request):
        """Approve a refund request (staff only)."""
        refund_id = request.data.get('refund_id')
        notes = request.data.get('notes', '')
        
        refund = get_object_or_404(RefundRequest, id=refund_id)
        
        if refund.status != 'pending':
            return Response(
                {'error': 'Refund request must be pending'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Process refund
        from .services import PaymentService
        PaymentService.process_refund(
            refund.ticket_sale,
            refund.refund_amount,
            refund.refund_reason
        )
        
        refund.status = 'approved'
        refund.reviewed_by = request.user
        refund.review_notes = notes
        refund.save()
        
        serializer = RefundRequestSerializer(refund)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], permission_classes=[CanProcessRefund])
    def reject_refund(self, request):
        """Reject a refund request (staff only)."""
        refund_id = request.data.get('refund_id')
        notes = request.data.get('notes', '')
        
        refund = get_object_or_404(RefundRequest, id=refund_id)
        
        if refund.status != 'pending':
            return Response(
                {'error': 'Refund request must be pending'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        refund.status = 'rejected'
        refund.reviewed_by = request.user
        refund.review_notes = notes
        refund.save()
        
        serializer = RefundRequestSerializer(refund)
        return Response(serializer.data)


class OrderViewSet(viewsets.ModelViewSet):
    """
    API for managing orders.
    Replaces Flutter methods: getUserOrders, getAllOrders, updateOrder, deleteOrder, etc.
    """
    queryset = Order.objects.filter(deleted_at__isnull=True)
    serializer_class = OrderSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'currency']
    ordering_fields = ['created_at', 'total_amount', 'status']
    ordering = ['-created_at']

    def get_permissions(self):
        if self.action in ['create']:
            return [drf_permissions.IsAuthenticated()]
        if self.action in ['update', 'partial_update', 'destroy']:
            return [drf_permissions.IsAuthenticated(), IsOrderOwnerOrAdmin()]
        return [drf_permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        if user.is_staff:
            return qs

        qs = qs.filter(user=user)
        
        event_id = self.request.query_params.get('event_id')
        if event_id:
            # Check if user is organizer of the event
            if EventOrganizer.objects.filter(event_id=event_id, user=user).exists():
                qs = Order.objects.filter(event_id=event_id)
        
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)

        return qs

    @action(detail=False, methods=['get'], url_path='mine')
    def my_orders(self, request):
        """Equivalent to getUserOrders(userId)"""
        qs = self.get_queryset().filter(user=request.user)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='all', permission_classes=[IsAdmin])
    def all_orders(self, request):
        """Equivalent to getAllOrders() - admin only"""
        qs = Order.objects.filter(deleted_at__isnull=True)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        """
        Création d'une commande avec ses articles (TicketTypes).
        Logique : valide la disponibilité du TicketType, calcule le total, 
        sauvegarde la commande et crée les OrderItems liés au TicketType.
        La création des tickets individuels est différée après paiement.
        """
        ticket_items = self.request.data.get('items', [])
        if not ticket_items:
            raise serializers.ValidationError({"items": "Au moins un ticket est requis."})

        total_amount = 0
        validated_items = []

        with transaction.atomic():
            # 1. Validation et calcul du total
            for item in ticket_items:
                ticket_type_id = item.get('ticket_type_id')
                quantity = item.get('quantity', 1)
                
                # Récupérer et verrouiller le TicketType
                try:
                    ticket_type = TicketType.objects.select_for_update().get(id=ticket_type_id)
                except TicketType.DoesNotExist:
                    raise serializers.ValidationError(f"Le type de ticket (ID: {ticket_type_id}) est introuvable.")
                
                # Vérifier la disponibilité (sold + reserved)
                sold_count = Ticket.objects.filter(ticket_type=ticket_type, status='confirmed').count()
                reserved_count = Ticket.objects.filter(
                    ticket_type=ticket_type,
                    status='reserved',
                    reserved_until__gt=timezone.now()
                ).count()
                
                available = ticket_type.quantity - (sold_count + reserved_count)
                
                if quantity > available:
                    raise serializers.ValidationError(f"Pas assez de billets disponibles pour {ticket_type.name}. Disponible: {available}")
                
                total_amount += (ticket_type.price * quantity)
                validated_items.append({'ticket_type': ticket_type, 'quantity': quantity})

            # 2. Sauvegarde de la commande
            order = serializer.save(
                user=self.request.user,
                status='pending',
                currency=validated_items[0]['ticket_type'].event.currency or 'USD',
                total_amount=total_amount
            )

            # 3. Création des OrderItems liés au TicketType
            for item in validated_items:
                OrderItem.objects.create(
                    order=order,
                    ticket_type=item['ticket_type'],
                    quantity=item['quantity'],
                    price_at_purchase=item['ticket_type'].price
                )

    def perform_update(self, serializer):
        serializer.save(updated_at=timezone.now())

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save()

    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        """Placeholder for manual order payment initiation."""
        order = self.get_object()
        # Implementation depends on specific requirements
        return Response({'status': 'payment initiated', 'order_id': order.id})


class OrderItemViewSet(viewsets.ModelViewSet):
    """
    API for managing order items.
    """
    queryset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        qs = super().get_queryset()
        order_id = self.request.query_params.get('order_id')
        if order_id:
            qs = qs.filter(order_id=order_id)
        return qs

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        instance.delete()


class WebhookView(viewsets.GenericViewSet):
    permission_classes = [AllowAny]

    @action(detail=False, methods=['post'], url_path='stripe')
    def stripe_webhook(self, request):
        provider = StripeProvider()
        event = provider.verify_webhook(request)
        if event:
            data = provider.handle_webhook(event)
            if data:
                PaymentService.process_successful_payment(
                    order_id=data['order_id'],
                    provider_name='stripe',
                    transaction_id=data['transaction_id'],
                    raw_data=data['raw_data']
                )
                return Response({'status': 'success'})
        return Response({'status': 'invalid payload'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='paypal')
    def paypal_webhook(self, request):
        provider = PayPalProvider()
        event = provider.verify_webhook(request)
        if event:
            data = provider.handle_webhook(event)
            if data:
                PaymentService.process_successful_payment(
                    order_id=data['order_id'],
                    provider_name='paypal',
                    transaction_id=data['transaction_id'],
                    raw_data=data['raw_data']
                )
                return Response({'status': 'success'})
        return Response({'status': 'invalid payload'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='moncash')
    def moncash_webhook(self, request):
        provider = MonCashProvider()
        event = provider.verify_webhook(request)
        if event:
            data = provider.handle_webhook(event)
            if data:
                PaymentService.process_successful_payment(
                    order_id=data['order_id'],
                    provider_name='moncash',
                    transaction_id=data['transaction_id'],
                    raw_data=data['raw_data']
                )
                return Response({'status': 'success'})
        return Response({'status': 'invalid payload'}, status=status.HTTP_400_BAD_REQUEST)


class PaymentViewSet(viewsets.ModelViewSet):
    """
    Complete API for managing payments.
    Replaces Flutter methods: getAllPayments, detail, updatePayment, processPayment.
    """
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'currency']
    search_fields = ['transaction_id', 'user__email']
    ordering_fields = ['created_at', 'amount']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(user=self.request.user)
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)
        method = self.request.query_params.get('payment_method')
        if method:
            qs = qs.filter(payment_method=method)
        return qs

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        new_status = request.data.get('status')
        if new_status not in ['succeeded', 'failed', 'refunded']:
            return Response({'error': 'Statut invalide'}, status=status.HTTP_400_BAD_REQUEST)
        instance.status = new_status
        instance.save(update_fields=['status', 'updated_at'])
        return Response(self.get_serializer(instance).data)

    @action(detail=False, methods=['post'], url_path='process')
    def process_payment(self, request):
        order_id = request.data.get('order_id')
        payment_method = request.data.get('payment_method')
        transaction_id = request.data.get('transaction_id')
        gateway = request.data.get('gateway', payment_method)

        if not all([order_id, payment_method, transaction_id]):
            return Response({'error': 'order_id, payment_method et transaction_id sont requis'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            order = Order.objects.get(id=order_id)
        except (Order.DoesNotExist, serializers.ValidationError):
            return Response({'error': 'Commande introuvable'}, status=status.HTTP_404_NOT_FOUND)

        if order.user_id != request.user.id:
            return Response({'error': 'Vous ne pouvez pas payer cette commande'},
                            status=status.HTTP_403_FORBIDDEN)

        if order.status != 'pending':
            return Response({'error': 'La commande n\'est plus en attente de paiement'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                PaymentService.process_successful_payment(
                    order_id=order.id,
                    provider_name=gateway,
                    transaction_id=transaction_id,
                    raw_data=request.data.get('raw_data', {})
                )
            return Response({'status': 'success', 'order_id': order.id})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='create-session', permission_classes=[IsAuthenticated])
    def create_payment_session(self, request):
        obj_id = request.data.get('order_id')
        provider_name = request.data.get('provider')
        
        # Validation ajoutée pour empêcher les requêtes avec ID invalide ou vide
        if not obj_id or str(obj_id).strip() == '':
            return Response({'error': 'ID de commande/objet manquant ou invalide'}, status=400)
            
        # Try to find the object in different models
        obj = None
        for model in [Order, ServiceBooking, SubscriptionPlan, Deposit]:
            try:
                # Use 'customer' for ServiceBooking, 'user' for others
                lookup_kwargs = {'id': obj_id}
                if model == ServiceBooking:
                    lookup_kwargs['customer'] = request.user
                else:
                    # Ajout d'une vérification robuste pour éviter les erreurs de format UUID
                    # Si le modèle n'a pas de champ 'user', cela lèvera une erreur
                    try:
                        lookup_kwargs['user'] = request.user
                    except:
                        pass
                
                obj = model.objects.get(**lookup_kwargs)
                break
            except (model.DoesNotExist, serializers.ValidationError, ValueError):
                continue
        
        if not obj:
            return Response({'error': 'Objet de paiement invalide ou non trouvé'}, status=400)
        
        # Check status if applicable
        if isinstance(obj, Order) and obj.status != 'pending':
            return Response({'error': 'Commande déjà payée'}, status=400)
        
        if provider_name == 'stripe':
            provider = StripeProvider(
                secret_key=settings.STRIPE_SECRET_KEY,
                publishable_key=settings.STRIPE_PUBLISHABLE_KEY
            )
        elif provider_name == 'paypal':
            provider = PayPalProvider()
        else:
            return Response({'error': 'Provider non supporté'}, status=400)
        
        try:
            payment_data = provider.create_payment_session(obj, user=request.user)
            
            if provider_name == 'paypal':
                return Response({
                    'approval_url': payment_data['approval_url'],
                    'payment_id': payment_data['payment_id']
                })
            else:
                return Response({
                    'client_secret': payment_data['client_secret'],
                    'publishable_key': payment_data.get('publishable_key'),
                    'payment_id': payment_data['payment_id']
                })
        except Exception as e:
            return Response({'error': str(e)}, status=500)

    @action(detail=False, methods=['get'], url_path='mine')
    def my_payments(self, request):
        qs = self.get_queryset().filter(user=request.user)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='total-spent')
    def total_spent_post(self, request):
        """Legacy total-spent action (POST)"""
        total = self.get_queryset().filter(user=request.user, status='succeeded').aggregate(
            total=models.Sum('amount')
        )['total'] or 0.00
        return Response({'total_spent': float(total)})

    @action(detail=False, methods=['get'], url_path='mine/total-spent', permission_classes=[IsAuthenticated])
    def total_spent_get(self, request):
        """New financial total-spent action (GET)"""
        total = Payment.objects.filter(user=request.user, status__in=['succeeded', 'completed']).aggregate(
            total_spent=Sum('amount')
        )['total_spent'] or 0
        return Response({'total_spent': total})

    @action(detail=False, methods=['post'], url_path='verify-iap', permission_classes=[IsAuthenticated])
    def verify_iap(self, request):
        order_id = request.data.get('order_id')
        token = request.data.get('purchase_token')
        product_id = request.data.get('product_id')
        package_name = request.data.get('package_name', "com.arkevent.app")

        if not all([order_id, token, product_id]):
            return Response({'error': 'order_id, purchase_token et product_id sont requis'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            order = Order.objects.get(id=order_id, user=request.user)
            result = verify_google_purchase(package_name, product_id, token, is_subscription=False)
            
            if result.get('purchaseState') != 0:
                return Response({'error': 'L\'achat n\'est pas validé par Google Play'}, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                PaymentService.process_successful_payment(
                    order_id=order.id,
                    provider_name='google_play',
                    transaction_id=token,
                    raw_data=result
                )
            
            return Response({'status': 'success', 'order_id': order.id})
            
        except Order.DoesNotExist:
            return Response({'error': 'Commande introuvable'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
