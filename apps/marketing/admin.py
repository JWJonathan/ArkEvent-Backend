from django.contrib import admin
from .models import EmailCampaign, EmailSubscriber

@admin.register(EmailCampaign)
class EmailCampaignAdmin(admin.ModelAdmin):
    list_display = ('subject', 'organization', 'event', 'status', 'scheduled_for', 'sent_at')
    list_filter = ('status', 'scheduled_for', 'sent_at', 'organization')
    search_fields = ('subject', 'sender_name', 'sender_email')
    readonly_fields = ('id', 'created_at', 'updated_at')
    raw_id_fields = ('organization', 'event', 'created_by')

@admin.register(EmailSubscriber)
class EmailSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'name', 'is_active', 'subscribed_at', 'source')
    list_filter = ('is_active', 'subscribed_at', 'source')
    search_fields = ('email', 'name', 'source')
    readonly_fields = ('id', 'subscribed_at')
