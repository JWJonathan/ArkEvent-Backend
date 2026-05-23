from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import EmailCampaign, EmailSubscriber
from .serializers import EmailCampaignSerializer, EmailSubscriberSerializer
from apps.core.permissions import IsAdmin

class EmailCampaignViewSet(viewsets.ModelViewSet):
    queryset = EmailCampaign.objects.all().order_by('-created_at')
    serializer_class = EmailCampaignSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsAdmin()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_at=timezone.now())

    @action(detail=True, methods=['post'], url_path='send')
    def send_campaign(self, request, pk=None):
        campaign = self.get_object()
        if campaign.status not in ['draft', 'scheduled']:
            return Response({'error': 'Campagne déjà envoyée'}, status=status.HTTP_400_BAD_REQUEST)
        # Simuler l'envoi (à remplacer par Celery ou tâche asynchrone)
        campaign.status = 'sent'
        campaign.sent_at = timezone.now()
        campaign.save(update_fields=['status', 'sent_at'])
        return Response({'status': 'sent'})


class EmailSubscriberViewSet(viewsets.ModelViewSet):
    queryset = EmailSubscriber.objects.all()
    serializer_class = EmailSubscriberSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'destroy']:
            return [permissions.IsAuthenticated(), IsAdmin()]
        if self.action == 'subscribe':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), IsAdmin()]

    @action(detail=False, methods=['post'], url_path='subscribe', permission_classes=[permissions.AllowAny])
    def subscribe(self, request):
        email = request.data.get('email')
        name = request.data.get('name', '')
        if not email:
            return Response({'error': 'email requis'}, status=status.HTTP_400_BAD_REQUEST)
        subscriber, created = EmailSubscriber.objects.get_or_create(email=email, defaults={'name': name, 'is_active': True})
        if not created and not subscriber.is_active:
            subscriber.is_active = True
            subscriber.unsubscribed_at = None
            subscriber.save()
        return Response(self.get_serializer(subscriber).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='unsubscribe', permission_classes=[permissions.AllowAny])
    def unsubscribe(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'email requis'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            subscriber = EmailSubscriber.objects.get(email=email, is_active=True)
            subscriber.is_active = False
            subscriber.unsubscribed_at = timezone.now()
            subscriber.save()
            return Response({'status': 'unsubscribed'})
        except EmailSubscriber.DoesNotExist:
            return Response({'error': 'Abonné introuvable'}, status=status.HTTP_404_NOT_FOUND)
        