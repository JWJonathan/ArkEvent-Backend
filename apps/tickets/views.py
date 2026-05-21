from rest_framework import viewsets, status, views
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Ticket
from .serializers import TicketSerializer
from .services import TicketService

class TicketViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer

    def get_queryset(self):
        return self.queryset.filter(owner_id=self.request.user.id)

    @action(detail=True, methods=['get'])
    def qr(self, request, pk=None):
        ticket = self.get_object()
        qr_base64 = TicketService.generate_qr_base64(ticket.token)
        return Response({'qr_code': qr_base64})

class CheckInView(views.APIView):
    def post(self, request):
        token = request.data.get('token')
        if not token:
            return Response({'detail': 'Token is required'}, status=status.HTTP_400_BAD_REQUEST)

        success, message = TicketService.validate_checkin(token)
        if success:
            return Response({'message': message})
        return Response({'detail': message}, status=status.HTTP_400_BAD_REQUEST)
