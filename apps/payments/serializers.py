from rest_framework import serializers
from .models import Order, OrderItem, Payment

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'order_id', 'ticket_id', 'ticket_type_name',
                  'price_at_purchase', 'quantity', 'created_at']
        read_only_fields = ['id', 'order_id', 'created_at']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    event_title = serializers.ReadOnlyField(source='event.title')
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'user_id', 'event_id', 'event_title', 'total_amount',
            'discount_amount', 'net_amount', 'currency', 'status',
            'coupon_code', 'gift_card_id', 'affiliate_id', 'metadata',
            'items', 'user_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user_id', 'event_title', 'created_at', 'updated_at']

    def get_user_name(self, obj):
        if obj.user.profile:
            return obj.user.profile.full_name
        return obj.user.email
    
class PaymentSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_id = serializers.UUIDField(source='user.id', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'order_id', 'user_id', 'user_name', 'amount', 'currency',
            'payment_method', 'gateway', 'transaction_id', 'status',
            'metadata', 'created_at'
        ]

    def get_user_name(self, obj):
        # Adaptez selon votre modèle utilisateur (ici on suppose un champ 'email' ou 'full_name')
        if hasattr(obj.user, 'profile') and obj.user.profile:
            return obj.user.profile.full_name
        return obj.user.email