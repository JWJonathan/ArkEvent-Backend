from django.contrib import admin
from .models import Order, OrderItem, Payment

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('ticket', 'price_at_purchase', 'created_at')

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
    list_display = ('order', 'ticket', 'price_at_purchase', 'created_at')
    raw_id_fields = ('order', 'ticket')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'user', 'amount', 'currency', 'status', 'transaction_id', 'created_at')
    list_filter = ('status', 'currency', 'created_at')
    search_fields = ('id', 'order__id', 'user__username', 'transaction_id')
    readonly_fields = ('id', 'created_at')
    raw_id_fields = ('order', 'user')
    ordering = ('-created_at',)
