from django.db import models
import uuid
from apps.events.models import Event

class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey("users.Profile", on_delete=models.CASCADE, related_name="orders", db_column='user_id')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="orders", db_column='event_id')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.TextField(default="HTG")
    status = models.CharField(max_length=20, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'arkevent"."orders'

class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items", db_column='order_id')
    ticket_type = models.ForeignKey("tickets.TicketType", on_delete=models.CASCADE, db_column='ticket_type_id')
    quantity = models.IntegerField(default=1)
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arkevent"."order_items'

class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="payments", db_column='order_id')
    user = models.ForeignKey("users.Profile", on_delete=models.CASCADE, related_name="payments", db_column='user_id')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.TextField(default="HTG")
    transaction_id = models.TextField(unique=True, null=True, blank=True)
    status = models.CharField(max_length=20, default="initiated")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arkevent"."payments'
