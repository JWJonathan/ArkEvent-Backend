from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils.text import slugify
from django.utils import timezone
from .models import Event

@receiver(pre_save, sender=Event)
def generate_event_slug(sender, instance, **kwargs):
    if not instance.slug:
        base = slugify(instance.title)
        date_part = (instance.start_date or timezone.now()).strftime('%Y%m%d')
        slug = f"{base}-{date_part}"
        counter = 1
        while Event.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
            slug = f"{base}-{date_part}-{counter}"
            counter += 1
        instance.slug = slug

    # Track old status
    if instance.pk:
        try:
            previous = Event.objects.get(pk=instance.pk)
            instance._old_status = previous.status
        except Event.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None

@receiver(post_save, sender=Event)
def notify_event_changes(sender, instance, created, **kwargs):
    from apps.notifications.services import NotificationService

    if created:
        NotificationService.notify_event_created(instance.created_by, instance)
    elif getattr(instance, '_old_status', None) != 'published' and instance.status == 'published':
        NotificationService.notify_event_published(instance.created_by, instance)