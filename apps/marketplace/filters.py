import django_filters
from .models import MarketplaceService, MarketplaceProvider

class MarketplaceServiceFilter(django_filters.FilterSet):
    price_min = django_filters.NumberFilter(field_name="base_price", lookup_expr='gte')
    price_max = django_filters.NumberFilter(field_name="base_price", lookup_expr='lte')
    min_rating = django_filters.NumberFilter(field_name="average_rating", lookup_expr='gte')
    available_date = django_filters.DateFilter(field_name="availabilities__date", method='filter_availability')

    class Meta:
        model = MarketplaceService
        fields = {
            'category': ['exact'],
            'city': ['exact', 'icontains'],
            'country': ['exact'],
            'provider': ['exact'],
            'service_type': ['exact'],
            'is_featured': ['exact'],
            'status': ['exact'],
        }

    def filter_availability(self, queryset, name, value):
        return queryset.filter(availabilities__date=value, availabilities__is_available=True)


class ProviderFilter(django_filters.FilterSet):
    min_rating = django_filters.NumberFilter(field_name="average_rating", lookup_expr='gte')

    class Meta:
        model = MarketplaceProvider
        fields = {
            'verified': ['exact'],
            'city': ['exact', 'icontains'],
            'country': ['exact'],
            'provider_type': ['exact'],
        }
