# tickets/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import TicketType, Ticket
import secrets

@receiver(post_save, sender=TicketType)
def generate_tickets_for_type(sender, instance, created, **kwargs):
    if created:
        tickets = []
        for _ in range(instance.quantity):
            tickets.append(Ticket(
                ticket_type=instance,
                token=secrets.token_hex(24)
            ))
        Ticket.objects.bulk_create(tickets)