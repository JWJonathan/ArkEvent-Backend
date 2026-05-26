from rest_framework import serializers
from .models import TicketType, Ticket, TicketHold, TicketTransfer
from .services import TicketService  # si nécessaire pour QR code

class TicketTypeSerializer(serializers.ModelSerializer):
    event_title = serializers.ReadOnlyField(source='event.title')

    class Meta:
        model = TicketType
        fields = [
            'id', 'event', 'event_id', 'event_title', 'name', 'description',
            'price', 'quantity', 'is_visible', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'event_title', 'created_at', 'updated_at']
        extra_kwargs = {'event': {'required': False}}


class TicketSerializer(serializers.ModelSerializer):
    ticket_type_name = serializers.ReadOnlyField(source='ticket_type.name')
    event_title = serializers.ReadOnlyField(source='ticket_type.event.title')
    owner_name = serializers.ReadOnlyField(source='owner.profile.full_name')

    class Meta:
        model = Ticket
        fields = [
            'id', 'ticket_type_id', 'ticket_type_name', 'event_title',
            'status', 'token', 'owner_id',
            'owner_name', 'reserved_until', 'checkin_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'token', 'created_at', 'updated_at']


class TicketHoldSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source='user.profile.full_name')
    ticket_type_name = serializers.ReadOnlyField(source='ticket_type.name')

    class Meta:
        model = TicketHold
        fields = ['id', 'user_id', 'user_name', 'ticket_type_id',
                  'ticket_type_name', 'quantity', 'expires_at', 'created_at']


class TicketTransferSerializer(serializers.ModelSerializer):
    from_user_name = serializers.ReadOnlyField(source='from_user.profile.full_name')
    to_user_name = serializers.ReadOnlyField(source='to_user.profile.full_name')

    class Meta:
        model = TicketTransfer
        fields = [
            'id', 'ticket_id', 'from_user_id', 'from_user_name',
            'to_user_id', 'to_user_name', 'to_email', 'status',
            'message', 'transfer_token', 'expires_at', 'completed_at', 'created_at'
        ]
        read_only_fields = ['id', 'from_user_id', 'created_at']
        