from django.db import models
import uuid
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
    owner = models.ForeignKey("users.Profile", on_delete=models.SET_NULL, null=True, blank=True, db_column='owner_id')
    reserved_until = models.DateTimeField(null=True, blank=True)
    checkin_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'arkevent"."tickets'

    def __str__(self):
        return f"Ticket {self.id} - {self.status}"
