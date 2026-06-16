from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.subscriptions.models import SubscriptionPlan, UserSubscription
from apps.notifications.models import NotificationLog
from datetime import date

User = get_user_model()

class SubscriptionNotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='test@example.com', password='password')
        self.plan = SubscriptionPlan.objects.create(
            tier='pro',
            price_usd=10.00,
            commission_percentage=5.0
        )

    def test_subscription_created_notification(self):
        # Create a subscription
        subscription = UserSubscription.objects.create(
            user=self.user,
            plan=self.plan,
            start_date=date.today(),
            renewal_date=date.today(),
            amount_paid=10.00
        )
        
        # Should have created 2 notifications (push and email)
        logs = NotificationLog.objects.filter(user=self.user)
        self.assertEqual(logs.count(), 2)
        self.assertTrue(logs.filter(title="Plan activé avec succès").exists())
        
        # Verify details
        log = logs.filter(title="Plan activé avec succès").first()
        self.assertIn("Pro", log.body)
        self.assertIn("10.0", log.body)
