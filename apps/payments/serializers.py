"""
DRF Serializers for Payments
"""

from rest_framework import serializers
from .models import (
    CommissionRule, TicketSale, Invoice, PaymentMethod, RefundRequest, Order, Payment, OrderItem
)


class CommissionRuleSerializer(serializers.ModelSerializer):
    commission_type_display = serializers.CharField(source='get_commission_type_display', read_only=True)
    deduction_model_display = serializers.CharField(source='get_deduction_model_display', read_only=True)
    
    class Meta:
        model = CommissionRule
        fields = [
            'id', 'name', 'description', 'commission_type', 'commission_type_display',
            'deduction_model', 'deduction_model_display', 'percentage', 'fixed_amount',
            'fixed_currency', 'subscription_tier', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TicketSaleSerializer(serializers.ModelSerializer):
    event_title = serializers.CharField(source='event.title', read_only=True)
    buyer_name = serializers.CharField(source='buyer.get_full_name', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    
    class Meta:
        model = TicketSale
        fields = [
            'id', 'event', 'event_title', 'buyer', 'buyer_name',
            'ticket_quantity', 'ticket_price_per_unit', 'currency',
            'subtotal', 'platform_fee', 'commission_amount', 'organizer_net_revenue',
            'total_amount_paid', 'payment_status', 'payment_status_display', 'transaction_id',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'platform_fee', 'commission_amount', 'organizer_net_revenue',
            'total_amount_paid', 'created_at', 'updated_at'
        ]


class InvoiceSerializer(serializers.ModelSerializer):
    invoice_type_display = serializers.CharField(source='get_invoice_type_display', read_only=True)
    buyer_email = serializers.CharField(source='buyer.email', read_only=True)
    seller_name = serializers.CharField(source='seller.name', read_only=True, allow_null=True)
    
    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'invoice_type', 'invoice_type_display',
            'ticket_sale', 'buyer', 'buyer_email',
            'seller', 'seller_name', 'subtotal', 'tax_amount', 'discount_amount',
            'total_amount', 'currency', 'issued_at', 'due_date', 'paid_at',
            'description', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'invoice_number', 'created_at', 'updated_at']


class PaymentMethodSerializer(serializers.ModelSerializer):
    method_type_display = serializers.CharField(source='get_method_type_display', read_only=True)
    
    class Meta:
        model = PaymentMethod
        fields = [
            'id', 'method_type', 'method_type_display', 'is_default', 'is_active',
            'display_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'token', 'created_at', 'updated_at']


class RefundRequestSerializer(serializers.ModelSerializer):
    refund_status_display = serializers.CharField(source='get_status_display', read_only=True)
    refund_reason_display = serializers.CharField(source='get_refund_reason_display', read_only=True)
    requester_name = serializers.CharField(source='requester.get_full_name', read_only=True)
    
    class Meta:
        model = RefundRequest
        fields = [
            'id', 'ticket_sale', 'requester', 'requester_name',
            'refund_amount', 'refund_reason', 'refund_reason_display', 'reason_description',
            'status', 'refund_status_display', 'reviewed_by', 'review_notes',
            'requested_at', 'processed_at'
        ]
        read_only_fields = [
            'id', 'status', 'reviewed_by', 'review_notes', 'requested_at', 'processed_at'
        ]


class OrderItemSerializer(serializers.ModelSerializer):
    ticket_type_name = serializers.CharField(source='ticket_type.name', read_only=True)
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'order', 'ticket_type', 'ticket_type_name',
            'quantity', 'price_at_purchase', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class OrderSerializer(serializers.ModelSerializer):
    event_title = serializers.CharField(source='event.title', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'user', 'user_email', 'event', 'event_title',
            'total_amount', 'currency', 'status', 'items',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'user_email', 'event_title', 'total_amount', 'currency', 'status', 'created_at', 'updated_at', 'items']
        extra_kwargs = {'event': {'read_only': False}}


class PaymentSerializer(serializers.ModelSerializer):
    order_data = OrderSerializer(source='order', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'order', 'order_data', 'user', 'user_email',
            'amount', 'currency', 'transaction_id', 'status',
            'metadata', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
