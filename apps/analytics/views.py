from rest_framework import viewsets, permissions, status, filters
from rest_framework.response import Response
from .models import EventView, EventAnalyticsDaily, ActivityLog
from .serializers import EventViewSerializer, EventAnalyticsDailySerializer, ActivityLogSerializer
from apps.core.permissions import IsAdmin

# ──────────── Event Views ────────────
class EventViewViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = EventView.objects.all().order_by('-viewed_at')
    serializer_class = EventViewSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]  # admin seulement

    def get_queryset(self):
        qs = super().get_queryset()
        event_id = self.request.query_params.get('event_id')
        if event_id:
            qs = qs.filter(event_id=event_id)
        return qs

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ──────────── Daily Analytics ────────────
class EventAnalyticsDailyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = EventAnalyticsDaily.objects.all().order_by('-date')
    serializer_class = EventAnalyticsDailySerializer
    permission_classes = [permissions.IsAuthenticated]  # accessible aux organisateurs
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['date', 'views', 'revenue']

    def get_queryset(self):
        qs = super().get_queryset()
        event_id = self.request.query_params.get('event_id')
        if event_id:
            qs = qs.filter(event_id=event_id)
        date_from = self.request.query_params.get('date_from')
        if date_from:
            qs = qs.filter(date__gte=date_from)
        date_to = self.request.query_params.get('date_to')
        if date_to:
            qs = qs.filter(date__lte=date_to)
        return qs


# ──────────── Activity Logs ────────────
class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ActivityLog.objects.all().order_by('-created_at')
    serializer_class = ActivityLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)