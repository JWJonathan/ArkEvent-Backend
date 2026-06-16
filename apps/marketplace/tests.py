from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.marketplace.models import MarketplaceProvider
from apps.notifications.models import NotificationLog

User = get_user_model()

class ProviderNotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='provider@example.com', password='password')

    def test_provider_created_notification(self):
        provider = MarketplaceProvider.objects.create(
            user=self.user,
            business_name='Test Provider',
            description='Test description',
            phone='1234567890',
            email='provider@example.com',
            address='123 Street',
            city='City',
            postal_code='12345'
        )
        
        logs = NotificationLog.objects.filter(user=self.user, title="Compte prestataire créé")
        self.assertEqual(logs.count(), 2)

    def test_provider_verified_notification(self):
        provider = MarketplaceProvider.objects.create(
            user=self.user,
            business_name='Test Provider 2',
            description='Test description',
            phone='1234567890',
            email='provider@example.com',
            address='123 Street',
            city='City',
            postal_code='12345',
            verified=False
        )
        
        NotificationLog.objects.filter(user=self.user).delete()
        
        provider.verified = True
        provider.save()
        
        logs = NotificationLog.objects.filter(user=self.user, title="Compte prestataire vérifié")
        self.assertEqual(logs.count(), 2)

    def test_service_created_notification(self):
        from apps.marketplace.models import MarketplaceService, MarketplaceCategory
        provider = MarketplaceProvider.objects.create(
            user=self.user,
            business_name='Provider',
            description='desc',
            phone='1',
            email='p@e.com',
            address='a',
            city='c',
            postal_code='1'
        )
        category = MarketplaceCategory.objects.create(name='Cat', slug='cat')
        
        NotificationLog.objects.filter(user=self.user).delete()
        
        service = MarketplaceService.objects.create(
            provider=provider,
            category=category,
            title='Test Service',
            summary='sum',
            description='desc',
            base_price=10.0,
            city='c',
            status='DRAFT'
        )
        
        logs = NotificationLog.objects.filter(user=self.user, title="Nouveau service créé")
        self.assertEqual(logs.count(), 2)

    def test_service_published_notification(self):
        from apps.marketplace.models import MarketplaceService, MarketplaceCategory
        provider = MarketplaceProvider.objects.create(
            user=self.user,
            business_name='Provider',
            description='desc',
            phone='1',
            email='p@e.com',
            address='a',
            city='c',
            postal_code='1'
        )
        category = MarketplaceCategory.objects.create(name='Cat', slug='cat')
        
        service = MarketplaceService.objects.create(
            provider=provider,
            category=category,
            title='Test Service Published',
            summary='sum',
            description='desc',
            base_price=10.0,
            city='c',
            status='DRAFT'
        )
        
        NotificationLog.objects.filter(user=self.user).delete()
        
        service.status = 'PUBLISHED'
        service.save()
        
        logs = NotificationLog.objects.filter(user=self.user, title="Service publié !")
        self.assertEqual(logs.count(), 2)

    def test_booking_created_notification(self):
        from apps.marketplace.models import MarketplaceService, MarketplaceCategory, ServiceBooking
        provider = MarketplaceProvider.objects.create(
            user=self.user,
            business_name='Provider',
            description='desc',
            phone='1',
            email='p@e.com',
            address='a',
            city='c',
            postal_code='1'
        )
        category = MarketplaceCategory.objects.create(name='Cat', slug='cat')
        service = MarketplaceService.objects.create(
            provider=provider,
            category=category,
            title='Test Service',
            summary='sum',
            description='desc',
            base_price=10.0,
            city='c'
        )
        
        NotificationLog.objects.filter(user=self.user).delete()
        
        booking = ServiceBooking.objects.create(
            service=service,
            customer=self.user,
            total_amount=10.0,
            start_date=timezone.now()
        )
        
        logs = NotificationLog.objects.filter(user=self.user, title="Nouvelle réservation")
        self.assertEqual(logs.count(), 2)

    def test_booking_status_changed_notification(self):
        from apps.marketplace.models import MarketplaceService, MarketplaceCategory, ServiceBooking
        provider = MarketplaceProvider.objects.create(
            user=self.user,
            business_name='Provider',
            description='desc',
            phone='1',
            email='p@e.com',
            address='a',
            city='c',
            postal_code='1'
        )
        category = MarketplaceCategory.objects.create(name='Cat', slug='cat')
        service = MarketplaceService.objects.create(
            provider=provider,
            category=category,
            title='Test Service',
            summary='sum',
            description='desc',
            base_price=10.0,
            city='c'
        )
        
        booking = ServiceBooking.objects.create(
            service=service,
            customer=self.user,
            total_amount=10.0,
            start_date=timezone.now(),
            status='PENDING'
        )
        
        NotificationLog.objects.filter(user=self.user).delete()
        
        booking.status = 'CONFIRMED'
        booking.save()
        
        logs = NotificationLog.objects.filter(user=self.user, title__startswith="Mise à jour de réservation")
        self.assertEqual(logs.count(), 2)
