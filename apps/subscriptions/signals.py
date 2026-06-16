from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import UserSubscription
from apps.notifications.services import NotificationService

@receiver(post_save, sender=UserSubscription)
def notify_plan_activation(sender, instance, created, **kwargs):
    if created and instance.status == 'active':
        NotificationService.notify_plan_activated(instance.user, instance)

