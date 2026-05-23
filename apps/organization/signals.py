from django.db.models.signals import pre_save
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