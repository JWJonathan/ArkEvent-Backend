from celery import shared_task
from .services import NotificationService
from django.contrib.auth import get_user_model

User = get_user_model()

@shared_task
def send_notification_task(user_id, title, body, notification_type='push', event_id=None, order_id=None, metadata=None):
    try:
        user = User.objects.get(id=user_id)
        from apps.events.models import Event
        from apps.payments.models import Order
        
        event = Event.objects.get(id=event_id) if event_id else None
        order = Order.objects.get(id=order_id) if order_id else None
        
        NotificationService.send_notification(
            user=user,
            title=title,
            body=body,
            notification_type=notification_type,
            event=event,
            order=order,
            metadata=metadata
        )
        return True
    except Exception as e:
        # Log error
        return False

@shared_task
def notify_all_participants_task(event_id, title, body, metadata=None):
    from apps.events.models import Event
    try:
        event = Event.objects.get(id=event_id)
        NotificationService.notify_all_participants(event, title, body, metadata)
        return True
    except Exception:
        return False
