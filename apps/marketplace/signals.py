from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import MarketplaceService, ServiceAvailability, MarketplaceProvider, ServiceBooking
from django.utils import timezone
from datetime import timedelta
from apps.notifications.services import NotificationService

# --- MarketplaceProvider Signals ---

@receiver(pre_save, sender=MarketplaceProvider)
def track_provider_verification(sender, instance, **kwargs):
    if instance.pk:
        try:
            previous = MarketplaceProvider.objects.get(pk=instance.pk)
            instance._old_verified = previous.verified
        except MarketplaceProvider.DoesNotExist:
            instance._old_verified = False
    else:
        instance._old_verified = False

@receiver(post_save, sender=MarketplaceProvider)
def notify_provider_changes(sender, instance, created, **kwargs):
    if created:
        NotificationService.notify_provider_created(instance.user, instance)
    elif not getattr(instance, '_old_verified', False) and instance.verified:
        NotificationService.notify_provider_verified(instance.user, instance)

# --- MarketplaceService Signals ---

@receiver(pre_save, sender=MarketplaceService)
def track_service_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            previous = MarketplaceService.objects.get(pk=instance.pk)
            instance._old_status = previous.status
        except MarketplaceService.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None

@receiver(post_save, sender=MarketplaceService)
def handle_marketplace_service_post_save(sender, instance, created, **kwargs):
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
        
        # Notify user on creation
        NotificationService.notify_service_created(instance.provider.user, instance)
    
    # Check for status change to PUBLISHED
    old_status = getattr(instance, '_old_status', None)
    if old_status != 'PUBLISHED' and instance.status == 'PUBLISHED':
        # Notify user on publication
        NotificationService.notify_service_published(instance.provider.user, instance)

# --- ServiceBooking Signals ---

@receiver(pre_save, sender=ServiceBooking)
def track_booking_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            previous = ServiceBooking.objects.get(pk=instance.pk)
            instance._old_status = previous.status
        except ServiceBooking.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None

@receiver(post_save, sender=ServiceBooking)
def handle_service_booking_post_save(sender, instance, created, **kwargs):
    if created:
        NotificationService.notify_booking_created(instance.customer, instance)
    elif getattr(instance, '_old_status', None) != instance.status:
        # Notify user on status change
        NotificationService.notify_booking_status_changed(instance.customer, instance)
