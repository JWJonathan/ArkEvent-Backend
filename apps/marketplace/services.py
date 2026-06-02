from django.db import transaction, models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import (
    MarketplaceProvider, MarketplaceService, ServiceBooking, 
    ServiceReview, ServiceAvailability, ServicePackage
)

class MarketplaceServiceManager:
    @staticmethod
    def publish_service(service):
        if not service.featured_image:
            raise ValidationError(_("Une image principale est requise pour publier le service."))
        service.status = MarketplaceService.Status.PUBLISHED
        service.save()
        return service

    @staticmethod
    def pause_service(service):
        service.status = MarketplaceService.Status.PAUSED
        service.save()
        return service

    @staticmethod
    def feature_service(service):
        service.is_featured = True
        service.save()
        return service

    @staticmethod
    def increment_view(service):
        service.views_count = models.F('views_count') + 1
        service.save(update_fields=['views_count'])


class ProviderManager:
    @staticmethod
    def verify_provider(provider, reviewer=None):
        provider.verified = True
        provider.save()
        return provider

    @staticmethod
    def update_rating(provider_id):
        provider = MarketplaceProvider.objects.get(id=provider_id)
        stats = ServiceReview.objects.filter(service__provider=provider).aggregate(
            avg=models.Avg('rating'), count=models.Count('id')
        )
        provider.average_rating = stats['avg'] or 0.0
        provider.total_reviews = stats['count'] or 0
        provider.save()

    @staticmethod
    def deactivate_provider(provider):
        provider.is_active = False
        provider.save()
        return provider


class BookingManager:
    @staticmethod
    def generate_reference():
        import uuid
        return f"ARK-{uuid.uuid4().hex[:8].upper()}"

    @staticmethod
    @transaction.atomic
    def create_booking(service, customer, data):
        start_date = data.get('start_date')
        
        # 1. Validation du délai de préparation
        min_date = timezone.now() + timezone.timedelta(days=service.preparation_time_days)
        if start_date < min_date:
            raise ValidationError(_("Ce prestataire nécessite un délai de préparation de %(days)d jours.") % {'days': service.preparation_time_days})

        # 2. Vérification disponibilité (si pas instantané)
        if not service.instant_booking:
            # Vérifier si une disponibilité spécifique existe et est 'True'
            is_available = ServiceAvailability.objects.filter(
                service=service, 
                date=start_date.date(), 
                is_available=True
            ).exists()
            if not is_available:
                raise ValidationError(_("Le service n'est pas disponible à cette date."))

        # 3. Calculs financiers
        package = data.get('package')
        base_amount = package.price if package else service.get_effective_price()
        
        # Commission ArkEvent (ex: 10% par défaut, peut être configuré dynamiquement plus tard)
        commission_rate = 0.10
        commission = base_amount * commission_rate

        booking = ServiceBooking.objects.create(
            service=service,
            customer=customer,
            package=package,
            total_amount=base_amount,
            commission_amount=commission,
            reference=BookingManager.generate_reference(),
            **data
        )
        
        # Mise à jour statistiques service
        service.bookings_count = models.F('bookings_count') + 1
        service.save(update_fields=['bookings_count'])
        
        return booking

    @staticmethod
    def confirm_booking(booking):
        booking.status = ServiceBooking.BookingStatus.CONFIRMED
        booking.save()
        return booking

    @staticmethod
    def cancel_booking(booking, reason=""):
        booking.status = ServiceBooking.BookingStatus.CANCELLED
        booking.provider_notes = f"{booking.provider_notes}\nAnnulation: {reason}".strip()
        booking.save()
        return booking

    @staticmethod
    @transaction.atomic
    def complete_booking(booking):
        booking.status = ServiceBooking.BookingStatus.COMPLETED
        booking.save()
        
        # Update provider stats
        provider = booking.service.provider
        provider.total_completed_jobs = models.F('total_completed_jobs') + 1
        provider.total_sales = models.F('total_sales') + booking.total_amount
        provider.save()
        
        return booking


class ReviewManager:
    @staticmethod
    @transaction.atomic
    def create_review(service, reviewer, data):
        # Vérifier si l'utilisateur a déjà laissé un avis
        if ServiceReview.objects.filter(service=service, reviewer=reviewer).exists():
            raise ValidationError(_("Vous avez déjà laissé un avis pour ce service."))
            
        review = ServiceReview.objects.create(
            service=service,
            reviewer=reviewer,
            **data
        )
        
        # Update provider rating
        ProviderManager.update_rating(service.provider_id)
        
        return review
