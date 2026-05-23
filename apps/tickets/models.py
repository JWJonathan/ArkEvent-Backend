from django.db import models
import uuid
from django.conf import settings
from apps.events.models import Event

class TicketType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="ticket_types", db_column='event_id')
    name = models.TextField()
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField()
    is_visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'arkevent"."ticket_types'

    def __str__(self):
        return f"{self.event.title} - {self.name}"

class Ticket(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket_type = models.ForeignKey(TicketType, on_delete=models.CASCADE, related_name="tickets", db_column='ticket_type_id')
    order = models.ForeignKey("payments.Order", on_delete=models.SET_NULL, null=True, blank=True, related_name="tickets", db_column='order_id')
    status = models.CharField(max_length=20, default="available") # available, reserved, confirmed, used, cancelled
    token = models.TextField(unique=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, db_column='owner_id')
    reserved_until = models.DateTimeField(null=True, blank=True)
    checkin_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'arkevent"."tickets'

    def __str__(self):
        return f"Ticket {self.id} - {self.status}"


from django.core.validators import MinValueValidator
from django.utils import timezone


class TicketHold(models.Model):
    """Représente une réservation temporaire de billets."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ticket_holds'
    )
    ticket_type = models.ForeignKey(
        'tickets.TicketType',
        on_delete=models.CASCADE,
        related_name='holds'
    )
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'arkevent_ticket_holds'  # optionnel : nom personnalisé
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name='ticket_holds_quantity_gt_0'
            )
        ]
        indexes = [
            models.Index(fields=['expires_at']),
            models.Index(fields=['user']),
            models.Index(fields=['ticket_type']),
        ]

    def __str__(self):
        return f"{self.user} - {self.ticket_type} x{self.quantity} (expires {self.expires_at})"


class TicketTransfer(models.Model):
    """Gère les transferts de billets entre utilisateurs."""
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('accepted', 'Accepté'),
        ('declined', 'Refusé'),
        ('cancelled', 'Annulé'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(
        'tickets.Ticket',
        on_delete=models.CASCADE,
        related_name='transfers'
    )
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_transfers'
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_transfers'
    )
    to_email = models.EmailField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    message = models.TextField(blank=True, default='')
    transfer_token = models.CharField(max_length=255, unique=True, null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'arkevent_ticket_transfers'  # optionnel
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=['pending', 'accepted', 'declined', 'cancelled']),
                name='ticket_transfers_status_valid'
            )
        ]
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['transfer_token']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['from_user']),
            models.Index(fields=['to_user']),
        ]

    def __str__(self):
        return f"Transfert {self.ticket.id} de {self.from_user} vers {self.to_user or self.to_email} ({self.status})"
