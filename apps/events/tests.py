from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.organization.models import Organization
from apps.events.models import Event
from apps.notifications.models import NotificationLog
from django.utils import timezone

User = get_user_model()

class EventNotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='test@example.com', password='password')
        self.org = Organization.objects.create(name='Test Org', created_by=self.user)

    def test_event_created_notification(self):
        # We need to ensure that creation of event triggers the notification
        event = Event.objects.create(
            title='Test Event', 
            organization=self.org, 
            created_by=self.user,
            start_date=timezone.now()
        )
        
        # Should have created 2 notifications (push and email)
        logs = NotificationLog.objects.filter(user=self.user, event=event)
        self.assertEqual(logs.count(), 2)
        self.assertTrue(logs.filter(title="Nouvel événement créé").exists())

    def test_event_published_notification(self):
        # Create draft event
        event = Event.objects.create(
            title='Test Event 2', 
            organization=self.org, 
            created_by=self.user,
            start_date=timezone.now(),
            status='draft'
        )
        
        # Clear previous logs from creation
        NotificationLog.objects.filter(user=self.user, event=event).delete()
        
        # Publish it
        event.status = 'published'
        event.save()
        
        # Should have created 2 notifications (push and email)
        logs = NotificationLog.objects.filter(user=self.user, event=event)
        self.assertEqual(logs.count(), 2)
        self.assertTrue(logs.filter(title="Événement publié !").exists())
