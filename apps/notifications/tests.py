from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.notifications.models import NotificationLog, EventNotificationSetting
from apps.notifications.services import NotificationService
from apps.events.models import Event
from apps.organization.models import Organization
import uuid

User = get_user_model()

class NotificationServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='password123'
        )
        self.org = Organization.objects.create(
            name='Test Org',
            created_by=self.user
        )
        self.event = Event.objects.create(
            title='Test Event',
            organization=self.org,
            created_by=self.user,
            start_date='2026-01-01T00:00:00Z',
            end_date='2026-01-01T23:59:59Z'
        )

    def test_send_notification_logs_and_respects_settings(self):
        # 1. Test basic notification logging
        NotificationService.send_notification(
            user=self.user,
            title='Test Title',
            body='Test Body',
            notification_type='push'
        )
        self.assertEqual(NotificationLog.objects.count(), 1)
        log = NotificationLog.objects.first()
        self.assertEqual(log.title, 'Test Title')
        self.assertEqual(log.type, 'push')

        # 2. Test settings: Disable push for this event
        EventNotificationSetting.objects.create(
            user=self.user,
            event=self.event,
            push_enabled=False
        )
        
        # Should NOT send/log if disabled
        NotificationService.send_notification(
            user=self.user,
            title='Push Disabled',
            body='Body',
            notification_type='push',
            event=self.event
        )
        # Count remains 1 from the previous test
        self.assertEqual(NotificationLog.objects.filter(title='Push Disabled').count(), 0)

    def test_send_email_notification(self):
        # Should log as email
        NotificationService.send_notification(
            user=self.user,
            title='Email Test',
            body='Body',
            notification_type='email'
        )
        log = NotificationLog.objects.get(title='Email Test')
        self.assertEqual(log.type, 'email')
