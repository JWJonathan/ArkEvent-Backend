from django.contrib import admin
from .models import TicketType, Ticket

@admin.register(TicketType)
class TicketTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'event', 'price', 'quantity', 'is_visible')
    list_filter = ('is_visible', 'event')
    search_fields = ('name', 'event__title', 'description')
    readonly_fields = ('id', 'created_at', 'updated_at')
    raw_id_fields = ('event',)

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket_type', 'status', 'token', 'owner', 'created_at')
    list_filter = ('status', 'created_at', 'ticket_type__event')
    search_fields = ('id', 'token', 'owner__id', 'ticket_type__name', 'ticket_type__event__title')
    readonly_fields = ('id', 'token', 'created_at', 'checkin_at', 'updated_at')
    raw_id_fields = ('ticket_type', 'owner')
