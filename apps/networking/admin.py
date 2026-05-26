from django.contrib import admin
from .models import NetworkingMatch, SocialPost

@admin.register(NetworkingMatch)
class NetworkingMatchAdmin(admin.ModelAdmin):
    list_display = ('user1', 'user2', 'event', 'status', 'matched_at')
    list_filter = ('status', 'matched_at', 'event')
    search_fields = ('user1__email', 'user2__email', 'event__title')
    readonly_fields = ('id', 'matched_at')
    raw_id_fields = ('event', 'user1', 'user2')

@admin.register(SocialPost)
class SocialPostAdmin(admin.ModelAdmin):
    list_display = ('platform', 'event', 'status', 'scheduled_at', 'posted_at')
    list_filter = ('platform', 'status', 'scheduled_at', 'event')
    search_fields = ('content', 'event__title')
    readonly_fields = ('id', 'created_at', 'updated_at')
    raw_id_fields = ('event', 'created_by')
