from django.contrib import admin
from .models import TicketType, Ticket, TicketHold, TicketTransfer

@admin.register(TicketType)
class TicketTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'event', 'price', 'quantity', 'is_visible')
    list_filter = ('is_visible', 'event')
    search_fields = ('name', 'event__title', 'description')
    readonly_fields = ('id', 'created_at', 'updated_at')
    raw_id_fields = ('event',)

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket_type', 'price', 'status', 'is_verified', 'token', 'owner', 'created_at')
    list_filter = ('status', 'is_verified', 'checkin_method', 'created_at', 'ticket_type__event')
    search_fields = ('id', 'token', 'owner__email', 'ticket_type__name', 'ticket_type__event__title')
    readonly_fields = ('id', 'token', 'created_at', 'checkin_at', 'updated_at', 'qr_code')
    raw_id_fields = ('ticket_type', 'owner', 'order')

@admin.register(TicketHold)
class TicketHoldAdmin(admin.ModelAdmin):
    list_display = ('user', 'ticket_type', 'quantity', 'expires_at', 'created_at')
    list_filter = ('expires_at', 'created_at', 'ticket_type__event')
    search_fields = ('user__email', 'ticket_type__name', 'ticket_type__event__title')
    readonly_fields = ('id', 'created_at')
    raw_id_fields = ('user', 'ticket_type')

@admin.register(TicketTransfer)
class TicketTransferAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'from_user', 'to_user', 'to_email', 'status', 'created_at')
    list_filter = ('status', 'created_at', 'expires_at')
    search_fields = ('ticket__token', 'from_user__email', 'to_user__email', 'to_email', 'transfer_token')
    readonly_fields = ('id', 'created_at', 'completed_at')
    raw_id_fields = ('ticket', 'from_user', 'to_user')
