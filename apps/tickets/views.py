from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from .models import TicketType, Ticket, TicketHold, TicketTransfer
from .serializers import (
    TicketTypeSerializer, TicketSerializer,
    TicketHoldSerializer, TicketTransferSerializer
)
from apps.core.permissions import IsAdmin, IsOrganizer
from .services import TicketService
from apps.notifications.services import NotificationService


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
    queryset = TicketType.objects.filter(deleted_at__isnull=True).order_by('-created_at')
    serializer_class = TicketTypeSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        
        # Filtres basés sur la visibilité publique pour les non-auth ou non-staff
        if not user.is_authenticated or not user.is_staff:
            qs = qs.filter(event__visibility='public', event__status='published')
        
        event_id = self.request.query_params.get('event_id')
        if event_id:
            qs = qs.filter(event_id=event_id)
        return qs.distinct()

    def perform_create(self, serializer):
        # Récupérer event depuis le payload ou validated_data
        event = serializer.validated_data.get('event')
        if not event:
            event_id = self.request.data.get('event_id')
            if not event_id:
                raise PermissionDenied("L'ID de l'événement est requis.")
            from apps.events.models import Event
            event = Event.objects.get(id=event_id)
            
        # Convert UUID to string for comparison
        if str(event.organization.created_by.id) != str(self.request.user.id) and not self.request.user.is_staff:
            raise PermissionDenied("Vous ne pouvez pas créer de type de billet pour cet événement.")
        
        # Check subscription limit
        from apps.subscriptions.services import SubscriptionService
        from django.db.models import Sum
        from rest_framework.exceptions import ValidationError
        
        current_total = TicketType.objects.filter(event=event).aggregate(total=Sum('quantity'))['total'] or 0
        new_quantity = serializer.validated_data.get('quantity', 0)
        
        is_allowed, message = SubscriptionService.check_limit(event.created_by, 'max_tickets_per_event', current_total + new_quantity)
        if not is_allowed:
            # Upgrade message enhancement
            custom_message = f"{message} Passez à un plan supérieur pour augmenter votre capacité."
            raise ValidationError({'detail': custom_message})

        serializer.save(event=event)


    def perform_update(self, serializer):
        instance = self.get_object()
        # Convert UUID to string for comparison
        if str(instance.event.organization.created_by.id) != str(self.request.user.id) and not self.request.user.is_staff:
            raise PermissionDenied()
            
        # Check subscription limit if quantity is changing
        if 'quantity' in serializer.validated_data:
            from apps.subscriptions.services import SubscriptionService
            from django.db.models import Sum
            from rest_framework.exceptions import ValidationError
            
            other_total = TicketType.objects.filter(event=instance.event).exclude(id=instance.id).aggregate(total=Sum('quantity'))['total'] or 0
            new_total = other_total + serializer.validated_data['quantity']
            
            is_allowed, message = SubscriptionService.check_limit(instance.event.created_by, 'max_tickets_per_event', new_total)
            if not is_allowed:
                # Upgrade message enhancement
                custom_message = f"{message} Passez à un plan supérieur pour augmenter votre capacité."
                raise ValidationError({'detail': custom_message})
                
        serializer.save(updated_at=timezone.now())

    def perform_destroy(self, instance):
        # Convert UUID to string for comparison
        if str(instance.event.organization.created_by.id) != str(self.request.user.id) and not self.request.user.is_staff:
            raise PermissionDenied()
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
    queryset = Ticket.objects.all().order_by('-created_at')
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        if user.is_staff:
            return qs
        
        return qs.filter(
            Q(owner=user) |
            Q(ticket_type__event__organizers__user=user)
        ).distinct()

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

    @action(detail=False, methods=['get'], url_path='count')
    def my_tickets_count(self, request):
        """Équivalent de getMyTicketsCount()"""
        count = self.get_queryset().filter(owner=request.user).count()
        return Response({'count': count})

    def perform_create(self, serializer):
        # Réservé aux organisateurs / admins (création manuelle de tickets)
        if not self.request.user.is_staff:
            raise PermissionDenied()
        serializer.save()

    def perform_update(self, serializer):
        instance = self.get_object()
        user = self.request.user
        event = instance.ticket_type.event
        
        # Autoriser le proprio, le staff, ou l'organisateur de l'event
        is_owner = instance.owner == user
        is_organizer = event.organization.created_by == user or \
                       event.organizers.filter(user=user).exists()
        
        if not is_owner and not is_organizer and not user.is_staff:
            raise PermissionDenied("Vous n'avez pas la permission de modifier ce billet.")
            
        serializer.save(updated_at=timezone.now())

    def perform_destroy(self, instance):
        # Soft delete : annule le billet (même logique que deleteTicket Flutter)
        if instance.owner != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied()
        instance.status = 'cancelled'
        instance.updated_at = timezone.now()
        instance.save()

    @action(detail=False, methods=['post'], url_path='claim-free')
    def claim_free(self, request):
        """
        Permet à un utilisateur de réclamer un billet gratuit sans passer par le paiement.
        Attend : ticket_type_id
        """
        ticket_type_id = request.data.get('ticket_type_id')
        if not ticket_type_id:
            return Response({'error': 'ID du type de billet requis'}, status=status.HTTP_400_BAD_REQUEST)

        from .services import ReservationService
        try:
            ticket = ReservationService.claim_free_ticket(request.user.id, ticket_type_id)
            serializer = self.get_serializer(ticket)
            return Response({
                'success': True,
                'message': 'Billet gratuit obtenu avec succès !',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='validate')
    def validate_ticket(self, request):
        """
        Équivalent de validateTicket(token, event_id)
        L'utilisateur connecté est le contrôleur (doit être organisateur de l'event).
        """
        token = request.data.get('token')
        event_id = request.data.get('event_id')
        if not token:
            return Response({'error': 'Le token est requis'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ticket = Ticket.objects.select_related('ticket_type__event', 'owner').get(token=token)
        except Ticket.DoesNotExist:
            return Response({'success': False, 'message': 'Billet invalide ou introuvable'}, status=status.HTTP_404_NOT_FOUND)

        # Vérifier que l'utilisateur est bien organisateur de l'événement
        # On peut aussi vérifier via EventOrganizer model si nécessaire
        event = ticket.ticket_type.event
        is_organizer = event.organization.created_by == request.user or \
                       event.organizers.filter(user=request.user).exists()
        
        if not is_organizer and not request.user.is_staff:
            return Response({'success': False, 'message': 'Non autorisé à valider des billets pour cet événement'}, status=status.HTTP_403_FORBIDDEN)

        # Check subscription feature: QR Check-in
        from apps.subscriptions.services import SubscriptionService
        is_allowed, message = SubscriptionService.check_feature(event.created_by, 'has_qr_checkin')
        if not is_allowed:
            return Response({'success': False, 'message': message})

        # Vérifier le statut
        if ticket.is_verified:
            return Response({
                'success': False, 
                'message': 'Ce billet a déjà été validé',
                'data': {
                    'checkin_at': ticket.checkin_at,
                    'owner': ticket.owner.full_name if ticket.owner else 'Anonyme'
                }
            }, status=status.HTTP_400_BAD_REQUEST)
            
        if ticket.status in ['cancelled', 'refunded']:
            return Response({'success': False, 'message': 'Ce billet a été annulé ou remboursé'}, status=status.HTTP_400_BAD_REQUEST)
        
        if ticket.status != 'confirmed' and not request.user.is_staff:
            return Response({'success': False, 'message': f'Le billet n\'est pas dans un état valide pour être utilisé (Statut: {ticket.status})'}, status=status.HTTP_400_BAD_REQUEST)

        # Marquer comme validé
        ticket.is_verified = True
        ticket.status = 'used'
        ticket.checkin_at = timezone.now()
        ticket.checkin_method = request.data.get('method', 'scan')
        ticket.save(update_fields=['is_verified', 'status', 'checkin_at', 'checkin_method', 'updated_at'])

        return Response({
            'success': True,
            'message': 'Billet validé avec succès ! Accès autorisé.',
            'data': {
                'owner': ticket.owner.full_name if ticket.owner else 'Anonyme',
                'ticket_type': ticket.ticket_type.name,
                'event': event.title,
                'checkin_at': ticket.checkin_at
            }
        })

    @action(detail=True, methods=['get'], url_path='download-pdf')
    def download_pdf(self, request, pk=None):
        """
        Sert le fichier PDF du billet avec les bons headers.
        Query param ?download=true pour forcer le téléchargement.
        """
        ticket = self.get_object()
        
        if not ticket.pdf_ticket:
            # Essayer de le générer s'il n'existe pas
            if ticket.status in ['sold', 'confirmed']:
                ticket.generate_pdf_ticket()
                ticket.save(update_fields=['pdf_ticket'])
            else:
                return Response(
                    {'error': 'Le PDF n\'est pas encore disponible. Le billet doit être confirmé.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

        if not ticket.pdf_ticket:
            return Response({'error': 'Échec de la génération du PDF.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Déterminer si on doit forcer le téléchargement
        force_download = request.query_params.get('download', 'false').lower() == 'true'
        
        from django.http import HttpResponse
        import os
        
        try:
            # Lecture du fichier (supporte le stockage local et S3 via django-storages)
            pdf_data = ticket.pdf_ticket.read()
            response = HttpResponse(pdf_data, content_type='application/pdf')
            
            filename = f"billet-{ticket.id}.pdf"
            disposition = 'attachment' if force_download else 'inline'
            response['Content-Disposition'] = f'{disposition}; filename="{filename}"'
            
            return response
        except Exception as e:
            return Response({'error': f'Erreur lors de la lecture du fichier: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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

    def perform_create(self, serializer):
        transfer = serializer.save(from_user=self.request.user)
        if transfer.to_user:
            # Notify the recipient that they have a pending transfer
            NotificationService.send_notification(
                transfer.to_user,
                "Transfert de billet en attente",
                f"{self.request.user.full_name if self.request.user else self.request.user.email} vous a envoyé un billet. Veuillez l'accepter.",
                notification_type='push',
                event=transfer.ticket.ticket_type.event
            )

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

        if new_status == 'accepted':
            NotificationService.notify_ticket_transfer(instance.from_user, instance.to_user, instance.ticket)
        elif new_status == 'declined':
            # Optionnel: notifier le sender que c'est refusé
            pass

        return Response(self.get_serializer(instance).data)