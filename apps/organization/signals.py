from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils.text import slugify
from .models import Organization

@receiver(pre_save, sender=Organization)
def generate_organization_slug(sender, instance, **kwargs):
    if not instance.slug:
        base_slug = slugify(instance.name)
        # Option : garantir l'unicité
        slug = base_slug
        counter = 1
        while Organization.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        instance.slug = slug

    # Track old verification status
    if instance.pk:
        try:
            previous = Organization.objects.get(pk=instance.pk)
            instance._old_verified = previous.verified
        except Organization.DoesNotExist:
            instance._old_verified = False
    else:
        instance._old_verified = False

@receiver(post_save, sender=Organization)
def notify_organization_changes(sender, instance, created, **kwargs):
    from apps.notifications.services import NotificationService
    
    if created:
        NotificationService.notify_organization_created(instance.created_by, instance)
    elif not getattr(instance, '_old_verified', False) and instance.verified:
        NotificationService.notify_organization_verified(instance.created_by, instance)