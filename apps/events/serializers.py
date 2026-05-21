from rest_framework import serializers
from .models import Event, Category
from apps.organization.models import Organization

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']

class EventSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source='category.name')
    organization_name = serializers.ReadOnlyField(source='organization.name')

    class Meta:
        model = Event
        fields = [
            'id', 'organization_id', 'organization_name', 'category_id', 'category_name',
            'title', 'slug', 'description', 'poster_url', 'start_date', 'end_date',
            'timezone', 'venue_name', 'venue_address', 'capacity', 'status',
            'visibility', 'currency', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
