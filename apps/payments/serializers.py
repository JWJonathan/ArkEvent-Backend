from rest_framework import serializers
from .models import Order, OrderItem, Payment

class OrderItemSerializer(serializers.ModelSerializer):
    ticket_type_name = serializers.ReadOnlyField(source='ticket_type.name')

    class Meta:
        model = OrderItem
        fields = ['id', 'ticket_type_id', 'ticket_type_name', 'quantity', 'price_at_purchase']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    event_title = serializers.ReadOnlyField(source='event.title')

    class Meta:
        model = Order
        fields = [
            'id', 'user_id', 'event_id', 'event_title', 'total_amount',
            'currency', 'status', 'items', 'created_at', 'updated_at'
        ]
