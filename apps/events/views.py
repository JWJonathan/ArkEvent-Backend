from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Event, Category
from .serializers import EventSerializer, CategorySerializer
from .services import EventService
from apps.core.permissions import IsOrganizer, IsEventOwner

class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all().prefetch_related('ticket_types') # Added prefetch_related
    serializer_class = EventSerializer

    def get_permissions(self):
        if self.action in ['create']:
            return [IsOrganizer()]
        if self.action in ['update', 'partial_update', 'destroy', 'publish', 'cancel']:
            return [IsEventOwner()]
        return super().get_permissions()

    def perform_create(self, serializer):
        event = EventService.create_event(self.request.user.id, serializer.validated_data)
        serializer.instance = event

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        try:
            event = EventService.publish_event(pk)
            return Response(EventSerializer(event).data)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        event = EventService.cancel_event(pk)
        return Response(EventSerializer(event).data)

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
