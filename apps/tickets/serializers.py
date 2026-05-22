from rest_framework import serializers
from .models import TicketType, Ticket, TicketHold, TicketTransfer
from .services import TicketService  # si nécessaire pour QR code

class TicketTypeSerializer(serializers.ModelSerializer):
    event_title = serializers.ReadOnlyField(source='event.title')

    class Meta:
        model = TicketType
        fields = [
            'id', 'event_id', 'event_title', 'name', 'description',
            'price', 'quantity', 'available_from', 'available_to',
            'tier_name', 'max_per_order', 'is_donation', 'is_free',
            'is_visible', 'color', 'sort_order', 'requires_approval',
            'brings_plus_one', 'sales_channel', 'hidden_until',
            'min_age', 'max_age', 'restrictions', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'event_title', 'created_at', 'updated_at']


class TicketSerializer(serializers.ModelSerializer):
    ticket_type_name = serializers.ReadOnlyField(source='ticket_type.name')
    event_title = serializers.ReadOnlyField(source='ticket_type.event.title')
    event_date = serializers.ReadOnlyField(source='ticket_type.event.start_date')
    owner_name = serializers.ReadOnlyField(source='owner.profile.full_name')
    qr_code = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = [
            'id', 'ticket_type_id', 'ticket_type_name', 'event_title',
            'event_date', 'status', 'token', 'qr_code', 'owner_id',
            'owner_name', 'reserved_until', 'held_by', 'seat_label',
            'checkin_at', 'checkin_method', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'token', 'qr_code', 'created_at', 'updated_at']

    def get_qr_code(self, obj):
        if obj.status in ['confirmed', 'used']:
            return TicketService.generate_qr_base64(obj.token)
        return None


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
        