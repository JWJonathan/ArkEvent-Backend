from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import RegistrationForm, RegistrationField, RegistrationAnswer, Attendance, Badge
from .serializers import (
    RegistrationFormSerializer, RegistrationFieldSerializer,
    RegistrationAnswerSerializer, AttendanceSerializer, BadgeSerializer
)
from apps.core.permissions import IsAdmin

# ──────────── Registration Forms ────────────
class RegistrationFormViewSet(viewsets.ModelViewSet):
    queryset = RegistrationForm.objects.all().order_by('-created_at')
    serializer_class = RegistrationFormSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsAdmin()]  # ou IsOrganizer
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save(updated_at=timezone.now())

    def perform_destroy(self, instance):
        instance.delete()


# ──────────── Registration Fields ────────────
class RegistrationFieldViewSet(viewsets.ModelViewSet):
    queryset = RegistrationField.objects.all().order_by('form__title', 'sort_order')
    serializer_class = RegistrationFieldSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsAdmin()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        instance.delete()


# ──────────── Registration Answers ────────────
class RegistrationAnswerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RegistrationAnswer.objects.all().order_by('-created_at')
    serializer_class = RegistrationAnswerSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]  # admin only

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ──────────── Attendances ────────────
class AttendanceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Attendance.objects.all().order_by('-checkin_at')
    serializer_class = AttendanceSerializer
    permission_classes = [permissions.IsAuthenticated]  # lister pour les organisateurs/admin

    def get_queryset(self):
        if self.request.user.is_staff:
            return Attendance.objects.all().order_by('-checkin_at')
        # L'organisateur ne voit que les présences de ses événements
        return Attendance.objects.filter(ticket__ticket_type__event__organizers__user=self.request.user).distinct()


# ──────────── Badges ────────────
class BadgeViewSet(viewsets.ModelViewSet):
    queryset = Badge.objects.all().order_by('-created_at')
    serializer_class = BadgeSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsAdmin()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        instance.delete()