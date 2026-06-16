from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.payments.models import Order
from apps.events.models import Event
from apps.organization.models import Organization
from apps.tickets.models import TicketType
from apps.notifications.models import NotificationLog
from decimal import Decimal

User = get_user_model()

class OrderNotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='buyer@example.com', password='password')
        self.org_user = User.objects.create_user(email='org@example.com', password='password')
        self.org = Organization.objects.create(name='Test Org', created_by=self.org_user)
        self.event = Event.objects.create(title='Test Event', organization=self.org, created_by=self.org_user, start_date='2026-07-01 10:00:00')
        self.ticket_type = TicketType.objects.create(event=self.event, name='VIP', price=100.00)
        
    def test_order_notification_contains_details(self):
        # Create order with items
        order = Order.objects.create(
            user=self.user,
            event=self.event,
            total_amount=200.00,
            currency='USD',
            status='completed'
        )
        # Create item
        from apps.payments.models import OrderItem
        OrderItem.objects.create(
            order=order,
            ticket_type=self.ticket_type,
            quantity=2,
            price_at_purchase=100.00
        )
        
        # Trigger notification
        from apps.notifications.services import NotificationService
        NotificationService.notify_ticket_order_placed(self.user, order)
        
        # Verify
        logs = NotificationLog.objects.filter(user=self.user, title="Commande confirmée")
        self.assertEqual(logs.count(), 2)
        log = logs.first()
        self.assertIn('VIP', log.body)
        self.assertIn('2x', log.body)
        self.assertIn('200.0', log.body)
