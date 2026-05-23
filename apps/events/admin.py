from django.contrib import admin
from .models import EventCategory, Event

@admin.register(EventCategory)
class EventCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name', 'slug')

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'organization', 'category', 'start_date', 'status', 'visibility', 'created_at')
    list_filter = ('status', 'visibility', 'category', 'start_date', 'organization')
    search_fields = ('title', 'slug', 'description', 'venue_name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('-start_date',)
    raw_id_fields = ('organization', 'category', 'created_by')
