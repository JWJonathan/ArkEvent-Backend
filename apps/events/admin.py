from django.contrib import admin
from .models import (
    EventCategory, Event, EventSession, EventSpeaker, 
    EventOrganizer, EventMedia, EventSponsor, EventFaq, 
    Announcement, EventShare
)

class EventSessionInline(admin.TabularInline):
    model = EventSession
    extra = 0

class EventSpeakerInline(admin.TabularInline):
    model = EventSpeaker
    extra = 0

class EventOrganizerInline(admin.TabularInline):
    model = EventOrganizer
    extra = 0

class EventMediaInline(admin.TabularInline):
    model = EventMedia
    extra = 0

class EventSponsorInline(admin.TabularInline):
    model = EventSponsor
    extra = 0

class EventFaqInline(admin.TabularInline):
    model = EventFaq
    extra = 0

@admin.register(EventCategory)
class EventCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'parent', 'is_active')
    list_filter = ('is_active', 'parent')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'organization', 'category', 'start_date', 'status', 'visibility', 'created_at')
    list_filter = ('status', 'visibility', 'category', 'start_date', 'organization')
    search_fields = ('title', 'slug', 'description', 'venue_name')
    readonly_fields = ('id', 'created_at', 'updated_at', 'published_at')
    ordering = ('-start_date',)
    raw_id_fields = ('organization', 'category', 'created_by')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [
        EventSessionInline, 
        EventSpeakerInline, 
        EventOrganizerInline, 
        EventMediaInline, 
        EventSponsorInline, 
        EventFaqInline
    ]

@admin.register(EventSession)
class EventSessionAdmin(admin.ModelAdmin):
    list_display = ('title', 'event', 'session_type', 'start_time', 'end_time')
    list_filter = ('session_type', 'start_time', 'event')
    search_fields = ('title', 'description', 'event__title')
    raw_id_fields = ('event', 'ticket_type')

@admin.register(EventSpeaker)
class EventSpeakerAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'event', 'role')
    list_filter = ('event',)
    search_fields = ('full_name', 'role', 'bio', 'event__title')
    raw_id_fields = ('event', 'profile')

@admin.register(EventOrganizer)
class EventOrganizerAdmin(admin.ModelAdmin):
    list_display = ('user', 'event', 'role')
    list_filter = ('role', 'event')
    search_fields = ('user__email', 'event__title')
    raw_id_fields = ('event', 'user', 'added_by')

@admin.register(EventMedia)
class EventMediaAdmin(admin.ModelAdmin):
    list_display = ('title', 'event', 'media_type', 'is_featured')
    list_filter = ('media_type', 'is_featured', 'event')
    search_fields = ('title', 'alt_text', 'event__title')
    raw_id_fields = ('event', 'uploaded_by')

@admin.register(EventSponsor)
class EventSponsorAdmin(admin.ModelAdmin):
    list_display = ('name', 'event', 'level')
    list_filter = ('level', 'event')
    search_fields = ('name', 'description', 'event__title')
    raw_id_fields = ('event',)

@admin.register(EventFaq)
class EventFaqAdmin(admin.ModelAdmin):
    list_display = ('question', 'event', 'sort_order')
    list_filter = ('event',)
    search_fields = ('question', 'answer', 'event__title')
    raw_id_fields = ('event',)

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'event', 'urgency', 'is_push', 'sent_at')
    list_filter = ('urgency', 'is_push', 'sent_at', 'event')
    search_fields = ('title', 'message', 'event__title')
    raw_id_fields = ('event', 'sender')

@admin.register(EventShare)
class EventShareAdmin(admin.ModelAdmin):
    list_display = ('event', 'platform', 'user', 'created_at')
    list_filter = ('platform', 'created_at', 'event')
    search_fields = ('event__title', 'user__email', 'recipient')
    raw_id_fields = ('event', 'user')
