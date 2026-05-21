from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from .models import Event
from .serializers import EventSerializer
from apps.core.permissions import IsAdmin, IsOrganizer, IsEventOwner

class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    lookup_field = 'slug'

    def get_permissions(self):
        if self.action in ['create']:
            return [permissions.IsAuthenticated(), IsOrganizer()]
        if self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsEventOwner()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        serializer.save(created_by_id=self.request.user.id)
