"""
DRF ViewSets for Payments
"""

from rest_framework import viewsets, status, permissions as drf_permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db import models
from django.db.models import Sum

from apps.events import models as events_models

from .models import (
    CommissionRule, TicketSale, Invoice, PaymentMethod, RefundRequest, Order, Payment
)
from .serializers import (
    CommissionRuleSerializer, TicketSaleSerializer, InvoiceSerializer,
    PaymentMethodSerializer, RefundRequestSerializer, OrderSerializer, PaymentSerializer
)
from apps.core.permissions import (
    IsWalletOwner, IsAccountOwner, CanProcessRefund, IsOrganizer
)


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


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API for viewing orders.
    """
    serializer_class = OrderSerializer
    permission_classes = [drf_permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['status', 'currency']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Order.objects.all()
        return Order.objects.filter(user=user)


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API for viewing payments.
    """
    serializer_class = PaymentSerializer
    permission_classes = [drf_permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['status', 'currency']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Payment.objects.all()
        return Payment.objects.filter(user=user)
    
    @action(detail=False, methods=['get'], url_path='mine/total-spent', permission_classes=[drf_permissions.IsAuthenticated])
    def total_spent(self, request):
        """Get total amount spent by user."""
        total = Payment.objects.filter(user=request.user, status='completed').aggregate(
            total_spent=Sum('amount')
        )['total_spent'] or 0
        return Response({'total_spent': total})
