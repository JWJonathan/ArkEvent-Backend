from rest_framework import serializers
from .models import TicketType, Ticket
from .services import TicketService

class TicketTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketType
        fields = ['id', 'event_id', 'name', 'description', 'price', 'quantity']

class TicketSerializer(serializers.ModelSerializer):
    ticket_type_name = serializers.ReadOnlyField(source='ticket_type.name')
    event_title = serializers.ReadOnlyField(source='ticket_type.event.title')
    qr_code = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = [
            'id', 'ticket_type_id', 'ticket_type_name', 'event_title',
            'status', 'token', 'qr_code', 'reserved_until', 'checkin_at', 'created_at'
        ]

    def get_qr_code(self, obj):
        if obj.status == 'confirmed' or obj.status == 'used':
            return TicketService.generate_qr_base64(obj.token)
        return None

class ReservationItemSerializer(serializers.Serializer):
    ticket_type_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)

class ReservationSerializer(serializers.Serializer):
    event_id = serializers.UUIDField()
    items = ReservationItemSerializer(many=True)
