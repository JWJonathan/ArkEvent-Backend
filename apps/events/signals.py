from django.db.models.signals import pre_save
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