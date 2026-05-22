from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction
from django.utils import timezone
from .models import TicketType, Ticket, TicketHold, TicketTransfer
from .serializers import (
    TicketTypeSerializer, TicketSerializer,
    TicketHoldSerializer, TicketTransferSerializer
)
from apps.core.permissions import IsAdmin, IsOrganizer, IsTicketOwner
from .services import TicketService


# ──────────────── TICKET TYPES ────────────────
class TicketTypeViewSet(viewsets.ModelViewSet):
    """
    Remplace :
    - getAllTicketTypes()
    - getTicketTypesByEvent()
    - createTicketType()
    - updateTicketType()
    - deleteTicketType()
    """
    queryset = TicketType.objects.filter(deleted_at__isnull=True)
    serializer_class = TicketTypeSerializer
    permission_classes = [permissions.IsAuthenticated]  # la vue ajuste selon l'action

    def get_queryset(self):
        qs = super().get_queryset()
        event_id = self.request.query_params.get('event_id')
        if event_id:
            qs = qs.filter(event_id=event_id)
        return qs

    def perform_create(self, serializer):
        # Vérifier que l'utilisateur est organisateur de l'événement
        event = serializer.validated_data['event']
        if event.organization.created_by != self.request.user and not self.request.user.is_staff:
            raise permissions.PermissionDenied("Vous ne pouvez pas créer de type de billet pour cet événement.")
        serializer.save()

    def perform_update(self, serializer):
        instance = self.get_object()
        if instance.event.organization.created_by != self.request.user and not self.request.user.is_staff:
            raise permissions.PermissionDenied()
        serializer.save(updated_at=timezone.now())

    def perform_destroy(self, instance):
        if instance.event.organization.created_by != self.request.user and not self.request.user.is_staff:
            raise permissions.PermissionDenied()
        instance.deleted_at = timezone.now()
        instance.save()


# ──────────────── TICKETS ────────────────
class TicketViewSet(viewsets.ModelViewSet):
    """
    Remplace :
    - getAllTickets()
    - getMyTickets()
    - createTicket()
    - updateTicket()
    - deleteTicket()
    - validateTicket()
    """
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        # Filtres optionnels
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)

        event_id = self.request.query_params.get('event_id')
        if event_id:
            qs = qs.filter(ticket_type__event_id=event_id)

        # Les utilisateurs non admin ne voient que leurs propres tickets
        if not user.is_staff:
            qs = qs.filter(owner=user)
        return qs

    @action(detail=False, methods=['get'], url_path='mine')
    def my_tickets(self, request):
        """Équivalent de getMyTickets(userId)"""
        qs = self.get_queryset().filter(owner=request.user)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        # Réservé aux organisateurs / admins (création manuelle de tickets)
        if not self.request.user.is_staff:
            raise permissions.PermissionDenied()
        serializer.save()

    def perform_update(self, serializer):
        instance = self.get_object()
        # Vérifier que l'utilisateur est propriétaire ou organisateur de l'événement
        if instance.owner != self.request.user and not self.request.user.is_staff:
            raise permissions.PermissionDenied()
        serializer.save(updated_at=timezone.now())

    def perform_destroy(self, instance):
        # Soft delete : annule le billet (même logique que deleteTicket Flutter)
        if instance.owner != self.request.user and not self.request.user.is_staff:
            raise permissions.PermissionDenied()
        instance.status = 'cancelled'
        instance.updated_at = timezone.now()
        instance.save()

    @action(detail=False, methods=['post'], url_path='validate')
    def validate_ticket(self, request):
        """
        Équivalent de validateTicket(token, eventId, controllerId)
        Attend : token, event_id
        L'utilisateur connecté est le contrôleur (doit être organisateur de l'event).
        """
        token = request.data.get('token')
        event_id = request.data.get('event_id')
        if not token or not event_id:
            return Response({'error': 'token et event_id requis'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ticket = Ticket.objects.get(token=token)
        except Ticket.DoesNotExist:
            return Response({'success': False, 'message': 'Billet introuvable'})

        # Vérifier que l'utilisateur est bien organisateur de l'événement
        if ticket.ticket_type.event.organization.created_by != request.user and not request.user.is_staff:
            return Response({'success': False, 'message': 'Non autorisé à valider'})

        # Vérifier le statut
        if ticket.status == 'used':
            return Response({'success': False, 'message': 'Billet déjà utilisé'})
        if ticket.status in ['cancelled', 'refunded']:
            return Response({'success': False, 'message': 'Billet annulé ou remboursé'})
        if ticket.status == 'pending':
            return Response({'success': False, 'message': 'Billet non payé'})

        # Marquer comme utilisé
        ticket.status = 'used'
        ticket.checkin_at = timezone.now()
        ticket.checkin_method = 'scan'
        ticket.save(update_fields=['status', 'checkin_at', 'checkin_method', 'updated_at'])

        return Response({
            'success': True,
            'message': 'Billet validé avec succès',
            'data': {
                'owner': ticket.owner.profile.full_name if ticket.owner and ticket.owner.profile else 'Anonyme',
                'type': ticket.ticket_type.name
            }
        })


# ──────────────── TICKET HOLDS ────────────────
class TicketHoldViewSet(viewsets.ModelViewSet):
    """
    Remplace :
    - getAllTicketHolds()
    - deleteTicketHold()
    """
    queryset = TicketHold.objects.all()
    serializer_class = TicketHoldSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def destroy(self, request, *args, **kwargs):
        # Suppression définitive (comme dans le code Flutter)
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ──────────────── TICKET TRANSFERS ────────────────
class TicketTransferViewSet(viewsets.ModelViewSet):
    """
    Remplace :
    - getAllTicketTransfers()
    - updateTransferStatus()
    """
    queryset = TicketTransfer.objects.all()
    serializer_class = TicketTransferSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def partial_update(self, request, *args, **kwargs):
        """Mise à jour partielle : principalement pour changer le statut."""
        instance = self.get_object()
        new_status = request.data.get('status')
        if new_status not in ['pending', 'accepted', 'declined', 'cancelled']:
            return Response({'error': 'Statut invalide'}, status=status.HTTP_400_BAD_REQUEST)

        instance.status = new_status
        if new_status in ['accepted', 'declined', 'cancelled']:
            instance.completed_at = timezone.now()
        instance.save(update_fields=['status', 'completed_at'])
        return Response(self.get_serializer(instance).data)