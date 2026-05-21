from django.db import models
import uuid
from apps.events.models import Event

class TicketType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="ticket_types")

    name = models.CharField(max_length=100) # VIP, Standard, etc.
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField()
    sold_count = models.IntegerField(default=0)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'arkevent"."ticket_types'

    def __str__(self):
        return f"{self.event.title} - {self.name}"


class Ticket(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    ticket_type = models.ForeignKey(TicketType, on_delete=models.CASCADE, related_name="tickets")

    order = models.ForeignKey("payments.Order", on_delete=models.CASCADE, related_name="tickets", null=True)

    STATUS_CHOICES = [
        ('valid', 'Valid'),
        ('used', 'Used'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="valid", db_index=True)

    token = models.CharField(max_length=255, unique=True, db_index=True) # Added index

    owner_id = models.UUIDField(db_index=True)  # profile.id

    checked_in_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arkevent"."tickets'

    def __str__(self):
        return f"Ticket {self.id} - {self.status}"
