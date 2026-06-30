from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from .models import (
    MarketplaceCategory, MarketplaceProvider, ProviderDocument,
    MarketplaceService, ServiceImage, ServicePackage,
    ServiceAvailability, ServiceFavorite, ServiceReview,
    ServiceBooking, BookingPayment, MarketplaceMessage
)

# --- Category Serializers ---

class MarketplaceCategoryListSerializer(serializers.ModelSerializer):
    children_count = serializers.IntegerField(read_only=True)
    services_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = MarketplaceCategory
        fields = ('id', 'name', 'slug', 'icon', 'children_count', 'services_count', 'order')


class MarketplaceCategoryDetailSerializer(serializers.ModelSerializer):
    subcategories = MarketplaceCategoryListSerializer(many=True, read_only=True)
    
    class Meta:
        model = MarketplaceCategory
        fields = ('id', 'name', 'slug', 'description', 'icon', 'subcategories', 'meta_title', 'meta_description')


# --- Provider Serializers ---

class ProviderListSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketplaceProvider
        fields = ('id', 'business_name', 'logo', 'city', 'verified', 'average_rating', 'total_reviews', 'short_bio')


class ProviderDetailSerializer(serializers.ModelSerializer):
    total_services = serializers.IntegerField(read_only=True)
    total_bookings = serializers.IntegerField(source='total_completed_jobs', read_only=True)

    class Meta:
        model = MarketplaceProvider
        fields = '__all__'


class ProviderCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketplaceProvider
        exclude = ('user', 'verified', 'average_rating', 'total_reviews', 'total_completed_jobs', 'total_sales', 'is_deleted', 'deleted_at')


class ProviderDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderDocument
        fields = '__all__'
        read_only_fields = ('reviewed_by', 'reviewed_at', 'status')


# --- Service Serializers ---

class ServiceImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceImage
        fields = ('id', 'image', 'alt_text', 'is_primary', 'sort_order')


class ServicePackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServicePackage
        fields = ('id', 'name', 'description', 'price', 'features', 'delivery_time_days', 'revisions', 'is_popular')


class ServiceAvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceAvailability
        fields = ('id', 'date', 'start_time', 'end_time', 'is_available')


class MarketplaceServiceListSerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source='provider.business_name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    effective_price = serializers.DecimalField(source='get_effective_price', max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = MarketplaceService
        fields = (
            'id', 'title', 'slug', 'provider_name', 'category_name',
            'featured_image', 'base_price', 'discount_price', 'effective_price',
            'city', 'is_featured', 'service_type', 'reviews_count', 'average_rating'
        )


class ServiceReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source='reviewer.full_name', read_only=True)
    reviewer_avatar = serializers.ImageField(source='reviewer.avatar', read_only=True)

    class Meta:
        model = ServiceReview
        fields = ('id', 'reviewer_name', 'reviewer_avatar', 'rating', 'title', 'comment', 'is_verified_purchase', 'reply_from_provider', 'created_at')


class MarketplaceServiceDetailSerializer(serializers.ModelSerializer):
    provider = ProviderListSerializer(read_only=True)
    category = MarketplaceCategoryListSerializer(read_only=True)
    images = ServiceImageSerializer(many=True, read_only=True)
    packages = ServicePackageSerializer(many=True, read_only=True)
    availability = ServiceAvailabilitySerializer(source='availabilities', many=True, read_only=True)
    reviews = ServiceReviewSerializer(many=True, read_only=True)
    effective_price = serializers.DecimalField(source='get_effective_price', max_digits=12, decimal_places=2, read_only=True)
    is_favorited = serializers.BooleanField(read_only=True, default=False)

    class Meta:
        model = MarketplaceService
        fields = '__all__'


class MarketplaceServiceCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketplaceService
        exclude = ('provider', 'views_count', 'favorites_count', 'bookings_count', 'is_deleted', 'deleted_at')


# --- Review Serializers ---

class ServiceReviewCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceReview
        fields = ('service', 'rating', 'title', 'comment', 'event_reference')

    def validate_rating(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError(_("La note doit être comprise entre 1 et 5."))
        return value


# --- Booking Serializers ---

class ServiceBookingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceBooking
        fields = ('service', 'package', 'event', 'start_date', 'end_date', 'customer_notes')

    def validate(self, data):
        if data.get('end_date') and data['end_date'] <= data['start_date']:
            raise serializers.ValidationError(_("La date de fin doit être postérieure à la date de début."))
        return data


class ServiceBookingListSerializer(serializers.ModelSerializer):
    service_title = serializers.CharField(source='service.title', read_only=True)
    provider_name = serializers.CharField(source='service.provider.business_name', read_only=True)
    service_id = serializers.ReadOnlyField(source='service.id')
    service_image = serializers.ReadOnlyField(source='service.featured_image.url')

    class Meta:
        model = ServiceBooking
        fields = ('id', 'reference', 'service_title', 'provider_name', 'start_date', 'total_amount', 'status', 'created_at', 'service_id', 'service_image')


class ServiceBookingDetailSerializer(serializers.ModelSerializer):
    service = MarketplaceServiceListSerializer(read_only=True)
    package = ServicePackageSerializer(read_only=True)
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    
    class Meta:
        model = ServiceBooking
        fields = '__all__'


# --- Favorite Serializer ---

class ServiceFavoriteSerializer(serializers.ModelSerializer):
    service_details = MarketplaceServiceListSerializer(source='service', read_only=True)

    class Meta:
        model = ServiceFavorite
        fields = ('id', 'user', 'service', 'service_details', 'created_at')
        read_only_fields = ('user',)


# --- Message Serializer ---

class MarketplaceMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.full_name', read_only=True)
    receiver_name = serializers.CharField(source='receiver.full_name', read_only=True)

    class Meta:
        model = MarketplaceMessage
        fields = '__all__'
        read_only_fields = ('sender',)
