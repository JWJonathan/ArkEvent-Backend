from rest_framework import serializers
from .models import Ticket

class TicketSerializer(serializers.ModelSerializer):
    qr_code = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = '__all__'

    def get_qr_code(self, obj):
        from .services import TicketService
        return TicketService.generate_qr_base64(obj.token)
