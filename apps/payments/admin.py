from django.contrib import admin
from .models import (
    Order, OrderItem, Payment, CommissionRule, 
    TicketSale, Invoice, PaymentMethod, RefundRequest
)

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('ticket_type', 'quantity', 'price_at_purchase', 'created_at')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'event', 'total_amount', 'currency', 'status', 'created_at')
    list_filter = ('status', 'currency', 'created_at', 'event')
    search_fields = ('id', 'user__username', 'event__title')
    readonly_fields = ('id', 'created_at', 'updated_at')
    inlines = [OrderItemInline]
    raw_id_fields = ('user', 'event')
    ordering = ('-created_at',)

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'ticket_type', 'quantity', 'price_at_purchase', 'created_at')
    raw_id_fields = ('order', 'ticket_type')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'user', 'amount', 'currency', 'status', 'transaction_id', 'created_at')
    list_filter = ('status', 'currency', 'created_at')
    search_fields = ('id', 'order__id', 'user__username', 'transaction_id')
    readonly_fields = ('id', 'created_at')
    raw_id_fields = ('order', 'user')
    ordering = ('-created_at',)

@admin.register(CommissionRule)
class CommissionRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'commission_type', 'deduction_model', 'percentage', 'fixed_amount', 'subscription_tier', 'is_active')
    list_filter = ('commission_type', 'deduction_model', 'subscription_tier', 'is_active')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(TicketSale)
class TicketSaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'event', 'buyer', 'ticket_quantity', 'total_amount_paid', 'payment_status', 'created_at')
    list_filter = ('payment_status', 'currency', 'created_at', 'event')
    search_fields = ('id', 'buyer__email', 'event__title', 'transaction_id')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('event', 'buyer', 'commission_rule', 'order')
    ordering = ('-created_at',)

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'invoice_type', 'buyer', 'seller', 'total_amount', 'currency', 'issued_at')
    list_filter = ('invoice_type', 'currency', 'issued_at')
    search_fields = ('invoice_number', 'buyer__email', 'seller__name')
    readonly_fields = ('created_at', 'updated_at', 'issued_at')
    raw_id_fields = ('ticket_sale', 'buyer', 'seller')
    ordering = ('-issued_at',)

@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('user', 'method_type', 'display_name', 'is_default', 'is_active')
    list_filter = ('method_type', 'is_default', 'is_active')
    search_fields = ('user__email', 'display_name', 'token')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('user',)

@admin.register(RefundRequest)
class RefundRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket_sale', 'requester', 'refund_amount', 'status', 'requested_at')
    list_filter = ('status', 'refund_reason', 'requested_at')
    search_fields = ('id', 'requester__email', 'ticket_sale__id')
    readonly_fields = ('requested_at', 'processed_at')
    raw_id_fields = ('ticket_sale', 'requester', 'reviewed_by')
    ordering = ('-requested_at',)
