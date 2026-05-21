from django.utils.text import slugify
from .models import Event
from django.db import transaction
import uuid

class EventService:
    @staticmethod
    def create_event(user_id, data):
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
            return event

    @staticmethod
    def update_event(event_id, data):
        event = Event.objects.get(id=event_id)
        for key, value in data.items():
            if key != 'slug': # Don't update slug via update_event normally
                setattr(event, key, value)
        event.save()
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
        event = Event.objects.get(id=event_id)
        event.status = 'cancelled'
        event.save()
        return event

    @staticmethod
    def validate_capacity(event_id, requested_quantity):
        event = Event.objects.get(id=event_id)
        if event.capacity:
            sold = sum(tt.sold_count for tt in event.ticket_types.all())
            if sold + requested_quantity > event.capacity:
                return False
        return True
