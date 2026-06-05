from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import MarketplaceService, ServiceAvailability
from django.utils import timezone
from datetime import timedelta

@receiver(post_save, sender=MarketplaceService)
def create_default_availability(sender, instance, created, **kwargs):
    if created:
        # Create availability for the next, say, 365 days
        today = timezone.now().date()
        days_to_create = 365
        
        availabilities = [
            ServiceAvailability(
                service=instance,
                date=today + timedelta(days=i),
                is_available=True
            )
            for i in range(days_to_create)
        ]
        ServiceAvailability.objects.bulk_create(availabilities)
