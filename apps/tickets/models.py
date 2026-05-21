import uuid

from django.db import models
from apps.users.models import Profile
from apps.events.models import Event
from apps.organization.models import Organization
import uuid

class TicketType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    event = models.ForeignKey(Event, on_delete=models.CASCADE)

    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField()

    created_at = models.DateTimeField(auto_now_add=True)


class Ticket(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    ticket_type = models.ForeignKey(TicketType, on_delete=models.CASCADE)

    status = models.CharField(max_length=20, default="available")

    token = models.CharField(max_length=255, unique=True)

    owner_id = models.UUIDField(null=True, blank=True)  # profile.id

    created_at = models.DateTimeField(auto_now_add=True)