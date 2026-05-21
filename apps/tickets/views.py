from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Ticket
from .serializers import TicketSerializer, ReservationSerializer
from .services import ReservationService

class TicketViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Ticket.objects.filter(owner_id=self.request.user.id)

class ReservationViewSet(viewsets.GenericViewSet):
    serializer_class = ReservationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            order = ReservationService.reserve_tickets(
                user_id=request.user.id,
                event_id=serializer.validated_data['event_id'],
                items_data=serializer.validated_data['items']
            )
            from apps.payments.serializers import OrderSerializer
            return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
