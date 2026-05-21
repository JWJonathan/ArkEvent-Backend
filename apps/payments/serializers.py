from rest_framework import serializers
from .models import Order, Payment, OrderItem
from apps.tickets.models import TicketType

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['ticket_type', 'quantity']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = ['id', 'user_id', 'event', 'total_amount', 'currency', 'status', 'items', 'created_at']
        read_only_fields = ['id', 'user_id', 'total_amount', 'status', 'created_at']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        order = Order.objects.create(**validated_data)
        total_amount = 0
        for item_data in items_data:
            tt = item_data['ticket_type']
            quantity = item_data['quantity']
            price = tt.price
            OrderItem.objects.create(
                order=order,
                ticket_type=tt,
                quantity=quantity,
                price_at_purchase=price
            )
            total_amount += (price * quantity)

        order.total_amount = total_amount
        order.save()
        return order

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'
