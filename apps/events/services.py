from django.utils.text import slugify
from .models import Event
from django.db import transaction
import uuid

class EventService:
    @staticmethod
    def create_event(user_id, data):
        from apps.subscriptions.services import SubscriptionService
        from apps.notifications.services import NotificationService
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        user = User.objects.get(id=user_id)
        features = SubscriptionService.get_subscription_features(user)
        active_events_count = Event.objects.filter(created_by=user, status__in=['published', 'postponed']).count()
        
        if active_events_count >= features['max_active_events']:
            NotificationService.notify_premium(user, 'limit_reached')

        with transaction.atomic():
            title = data.get('title', 'Untitled Event')
            base_slug = slugify(title)
            slug = base_slug

            # Simple collision handling for slug
            counter = 1
            while Event.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            data['slug'] = slug

            event = Event.objects.create(
                created_by_id=user_id,
                **data
            )
            
            from apps.notifications.services import NotificationService
            if Event.objects.filter(created_by_id=user_id).count() == 1:
                NotificationService.notify_gamification(event.created_by, 'first_event')
                
            return event

    @staticmethod
    def update_event(event_id, data):
        from apps.notifications.services import NotificationService
        event = Event.objects.get(id=event_id)
        
        # Track changes for notifications
        time_changed = False
        location_changed = False
        
        if 'start_date' in data and str(data['start_date']) != str(event.start_date):
            time_changed = True
        if 'venue_address' in data and data['venue_address'] != event.venue_address:
            location_changed = True
        
        for key, value in data.items():
            if key != 'slug': # Don't update slug via update_event normally
                setattr(event, key, value)
        event.save()
        
        if event.status == 'published':
            if time_changed:
                NotificationService.notify_event_update(event, 'time')
            if location_changed:
                NotificationService.notify_event_update(event, 'location')
                
        return event

    @staticmethod
    def publish_event(event_id):
        event = Event.objects.get(id=event_id)
        if not event.ticket_types.exists():
            raise Exception("Cannot publish event without ticket types")

        event.status = 'published'
        event.save()
        return event

    @staticmethod
    def cancel_event(event_id):
        from apps.notifications.services import NotificationService
        event = Event.objects.get(id=event_id)
        event.status = 'cancelled'
        event.save()
        
        NotificationService.notify_event_update(event, 'cancelled')
        return event

    @staticmethod
    def validate_capacity(event_id, requested_quantity):
        event = Event.objects.get(id=event_id)
        if event.capacity:
            sold = sum(tt.sold_count for tt in event.ticket_types.all())
            if sold + requested_quantity > event.capacity:
                return False
        return True
