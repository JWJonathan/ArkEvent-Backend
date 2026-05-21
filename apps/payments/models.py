import uuid

from django.db import models
from apps.users.models import Profile
from apps.events.models import Event
from apps.organization.models import Organization

class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    user_id = models.UUIDField()

    event = models.ForeignKey(Event, on_delete=models.CASCADE)

    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(max_length=20, default="pending")

    created_at = models.DateTimeField(auto_now_add=True)


class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    order = models.ForeignKey(Order, on_delete=models.CASCADE)

    user_id = models.UUIDField()

    amount = models.DecimalField(max_digits=10, decimal_places=2)

    gateway = models.CharField(max_length=50)

    status = models.CharField(max_length=20, default="initiated")

    created_at = models.DateTimeField(auto_now_add=True)
