from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.organization.models import Organization
from apps.notifications.models import NotificationLog

User = get_user_model()

class OrganizationNotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='test@example.com', password='password')

    def test_organization_created_notification(self):
        # We need to ensure that creation of organization triggers the notification
        org = Organization.objects.create(name='Test Org', created_by=self.user)
        
        # Should have created 2 notifications (push and email)
        logs = NotificationLog.objects.filter(user=self.user)
        self.assertEqual(logs.count(), 2)
        self.assertTrue(logs.filter(title="Félicitations ! Organisation créée").exists())

    def test_organization_verified_notification(self):
        # Create unverified org
        org = Organization.objects.create(name='Test Org 2', created_by=self.user, verified=False)
        
        # Clear previous logs from creation
        NotificationLog.objects.filter(user=self.user).delete()
        
        # Verify it
        org.verified = True
        org.save()
        
        # Should have created 2 notifications (push and email)
        logs = NotificationLog.objects.filter(user=self.user)
        self.assertEqual(logs.count(), 2)
        self.assertTrue(logs.filter(title="Organisation vérifiée").exists())
