from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User
from apps.marketplace.models import MarketplaceService, MarketplaceCategory, MarketplaceProvider
from apps.marketplace.services import BookingManager
from django.core.exceptions import ValidationError

class BookingTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='customer', password='password')
        self.provider_user = User.objects.create_user(username='provider', password='password')
        self.provider = MarketplaceProvider.objects.create(
            user=self.provider_user,
            business_name="Test Provider",
            description="Test Description",
            phone="0123456789",
            email="provider@test.com",
            address="123 Test St",
            city="Test City",
            postal_code="12345"
        )
        self.category = MarketplaceCategory.objects.create(name="Test Category", slug="test-category")
        self.service = MarketplaceService.objects.create(
            provider=self.provider,
            category=self.category,
            title="Test Service",
            service_type=MarketplaceService.ServiceType.SERVICE,
            summary="Test Summary",
            description="Test Description",
            base_price=100.00,
            city="Test City",
            instant_booking=False, # This is key
            preparation_time_days=1,
            featured_image="test.jpg"
        )

    def test_booking_fails_without_availability(self):
        data = {
            'start_date': timezone.now() + timedelta(days=2),
            # 'package': None,
        }
        
        # This should raise ValidationError
        with self.assertRaises(ValidationError) as cm:
            BookingManager.create_booking(self.service, self.user, data)
        
        self.assertEqual(cm.exception.messages, ["Le service n'est pas disponible à cette date."])

    def test_booking_succeeds_with_availability(self):
        from apps.marketplace.models import ServiceAvailability
        
        start_date = timezone.now() + timedelta(days=2)
        
        ServiceAvailability.objects.create(
            service=self.service,
            date=start_date.date(),
            is_available=True
        )
        
        data = {
            'start_date': start_date,
        }
        
        # This should succeed
        try:
            BookingManager.create_booking(self.service, self.user, data)
        except ValidationError:
            self.fail("BookingManager.create_booking raised ValidationError unexpectedly!")
