from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from .models import NotificationLog, EventNotificationSetting, PushToken
from .serializers import (
    NotificationLogSerializer, EventNotificationSettingSerializer, PushTokenSerializer
)
from apps.core.permissions import IsAdmin

# ──────────────────── NOTIFICATION LOGS ────────────────────
class NotificationLogViewSet(viewsets.ModelViewSet):
    queryset = NotificationLog.objects.all().order_by('-sent_at')
    serializer_class = NotificationLogSerializer

    def get_permissions(self):
        if self.action == 'all_logs':
            return [permissions.IsAuthenticated(), IsAdmin()]
        if self.action in ['mark_read', 'mark_unread', 'destroy']:
            return [permissions.IsAuthenticated()]
        # Pour list et retrieve, l'utilisateur ne voit que les siennes via get_queryset
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        # Pour les admins qui listent tout, on utilise l'action 'all_logs' séparée
        # Ici on restreint par défaut aux notifications de l'utilisateur connecté
        if self.action == 'list' or self.action == 'retrieve':
            return NotificationLog.objects.filter(user=user).order_by('-sent_at')
        # Pour les autres actions (mark_read, etc.) on laisse le queryset complet, mais l'objet est vérifié plus tard
        return super().get_queryset()

    # GET /notifications/all/ → admin
    @action(detail=False, methods=['get'], url_path='all')
    def all_logs(self, request):
        qs = NotificationLog.objects.all().order_by('-sent_at')
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    # POST /notifications/{id}/mark_read/
    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        if notification.user != request.user and not request.user.is_staff:
            return Response({'error': 'Non autorisé'}, status=status.HTTP_403_FORBIDDEN)
        notification.read_at = timezone.now()
        notification.save(update_fields=['read_at'])
        return Response({'status': 'read'})

    # POST /notifications/{id}/mark_unread/
    @action(detail=True, methods=['post'], url_path='mark-unread')
    def mark_unread(self, request, pk=None):
        notification = self.get_object()
        if notification.user != request.user and not request.user.is_staff:
            return Response({'error': 'Non autorisé'}, status=status.HTTP_403_FORBIDDEN)
        notification.read_at = None
        notification.save(update_fields=['read_at'])
        return Response({'status': 'unread'})

    def destroy(self, request, *args, **kwargs):
        # Vérifier que l'utilisateur peut supprimer sa propre notification (ou admin)
        instance = self.get_object()
        if instance.user != request.user and not request.user.is_staff:
            return Response({'error': 'Non autorisé'}, status=status.HTTP_403_FORBIDDEN)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ──────────────────── EVENT NOTIFICATION SETTINGS ────────────────────
class EventNotificationSettingViewSet(viewsets.ModelViewSet):
    queryset = EventNotificationSetting.objects.all()
    serializer_class = EventNotificationSettingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Les utilisateurs voient leurs propres paramètres ; admin peut tout voir
        if self.request.user.is_staff:
            return EventNotificationSetting.objects.all().order_by('user')
        return EventNotificationSetting.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Forcer l'utilisateur connecté
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        # Vérifier que l'instance appartient à l'utilisateur (déjà fait par get_object normalement)
        instance = self.get_object()
        if instance.user != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied()
        serializer.save()

    def perform_destroy(self, instance):
        if instance.user != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied()
        instance.delete()


# ──────────────────── PUSH TOKENS ────────────────────
class PushTokenViewSet(viewsets.ModelViewSet):
    queryset = PushToken.objects.all()
    serializer_class = PushTokenSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return PushToken.objects.all().order_by('-created_at')
        return PushToken.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Remplacer l'utilisateur par le demandeur
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        instance = self.get_object()
        if instance.user != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied()
        # On autorise uniquement la modification de is_active (comme dans le Flutter)
        if set(serializer.validated_data.keys()) - {'is_active'}:
            # Si d'autres champs sont envoyés, on peut les ignorer ou lever une erreur
            pass
        serializer.save()

    def perform_destroy(self, instance):
        if instance.user != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied()
        instance.delete()