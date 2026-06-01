from celery import shared_task
from .services import NotificationService
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

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

@shared_task
def schedule_event_reminders():
    """
    Periodic task to send reminders 7 days, 24 hours and 1 hour before an event.
    """
    from apps.events.models import Event
    now = timezone.now()
    
    # 7 days reminder
    target_7d = now + timedelta(days=7)
    events_7d = Event.objects.filter(
        start_date__gte=target_7d, 
        start_date__lt=target_7d + timedelta(hours=1),
        status='published'
    )
    for event in events_7d:
        NotificationService.notify_event_reminder(event, "7d")

    # 24 hours reminder
    target_24h = now + timedelta(hours=24)
    events_24h = Event.objects.filter(
        start_date__gte=target_24h, 
        start_date__lt=target_24h + timedelta(hours=1),
        status='published'
    )
    for event in events_24h:
        NotificationService.notify_event_reminder(event, "24h")

    # 1 hour reminder
    target_1h = now + timedelta(hours=1)
    events_1h = Event.objects.filter(
        start_date__gte=target_1h, 
        start_date__lt=target_1h + timedelta(minutes=15),
        status='published'
    )
    for event in events_1h:
        NotificationService.notify_event_reminder(event, "1h")
    
    # Event started now
    events_started = Event.objects.filter(
        start_date__gte=now - timedelta(minutes=5),
        start_date__lt=now,
        status='published'
    )
    for event in events_started:
        NotificationService.notify_event_update(event, "started")

    # Check-in available (based on doors_open)
    events_checkin = Event.objects.filter(
        doors_open__gte=now - timedelta(minutes=15),
        doors_open__lt=now,
        status='published'
    )
    for event in events_checkin:
        NotificationService.notify_during_event(event, "checkin")

@shared_task
def schedule_post_event_notifications():
    """
    Periodic task to send thank you and review notifications after event ends.
    """
    from apps.events.models import Event
    now = timezone.now()
    
    # 1 day after event ends
    target_1d_after = now - timedelta(days=1)
    events_ended = Event.objects.filter(
        end_date__gte=target_1d_after - timedelta(hours=1),
        end_date__lt=target_1d_after,
        status='published'
    )
    for event in events_ended:
        NotificationService.notify_post_event(event, 'thanks')
        NotificationService.notify_post_event(event, 'review')
        # Mark as completed
        event.status = 'completed'
        event.save(update_fields=['status'])
        # Notify organizer
        NotificationService.notify_gamification(event.created_by, 'event_completed')
