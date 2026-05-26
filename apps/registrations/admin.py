from django.contrib import admin
from .models import (
    RegistrationForm, RegistrationField, RegistrationAnswer, 
    Attendance, Badge
)

class RegistrationFieldInline(admin.TabularInline):
    model = RegistrationField
    extra = 1

@admin.register(RegistrationForm)
class RegistrationFormAdmin(admin.ModelAdmin):
    list_display = ('title', 'event', 'is_required', 'created_at')
    list_filter = ('is_required', 'event')
    search_fields = ('title', 'event__title')
    readonly_fields = ('id', 'created_at', 'updated_at')
    raw_id_fields = ('event',)
    inlines = [RegistrationFieldInline]

@admin.register(RegistrationField)
class RegistrationFieldAdmin(admin.ModelAdmin):
    list_display = ('label', 'form', 'field_type', 'is_required', 'sort_order')
    list_filter = ('field_type', 'is_required', 'form')
    search_fields = ('label', 'form__title', 'form__event__title')
    raw_id_fields = ('form',)

@admin.register(RegistrationAnswer)
class RegistrationAnswerAdmin(admin.ModelAdmin):
    list_display = ('field', 'order', 'ticket', 'answer', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('answer', 'field__label', 'order__id', 'ticket__token')
    raw_id_fields = ('field', 'order', 'ticket')

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'user', 'checkin_at', 'method')
    list_filter = ('method', 'checkin_at', 'ticket__ticket_type__event')
    search_fields = ('ticket__token', 'user__email', 'validation_code')
    readonly_fields = ('id', 'created_at')
    raw_id_fields = ('ticket', 'user')

@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ('user', 'event', 'type', 'badge_code', 'printed')
    list_filter = ('type', 'printed', 'event')
    search_fields = ('user__email', 'badge_code', 'event__title')
    readonly_fields = ('id', 'created_at')
    raw_id_fields = ('event', 'user')
