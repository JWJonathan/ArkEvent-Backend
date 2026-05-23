from rest_framework import serializers
from .models import RegistrationForm, RegistrationField, RegistrationAnswer, Attendance, Badge

class RegistrationFormSerializer(serializers.ModelSerializer):
    event_title = serializers.ReadOnlyField(source='event.title')

    class Meta:
        model = RegistrationForm
        fields = ['id', 'event_id', 'event_title', 'title', 'is_required', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class RegistrationFieldSerializer(serializers.ModelSerializer):
    form_title = serializers.ReadOnlyField(source='form.title')

    class Meta:
        model = RegistrationField
        fields = ['id', 'form_id', 'form_title', 'label', 'field_type', 'options', 'is_required', 'sort_order', 'created_at']
        read_only_fields = ['id', 'created_at']

class RegistrationAnswerSerializer(serializers.ModelSerializer):
    field_label = serializers.ReadOnlyField(source='field.label')
    form_title = serializers.ReadOnlyField(source='field.form.title')

    class Meta:
        model = RegistrationAnswer
        fields = ['id', 'field_id', 'field_label', 'form_title', 'order_id', 'ticket_id', 'answer', 'created_at']
        read_only_fields = ['id', 'created_at']

class AttendanceSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source='user.profile.full_name')
    ticket_token = serializers.ReadOnlyField(source='ticket.token')

    class Meta:
        model = Attendance
        fields = ['id', 'ticket_id', 'ticket_token', 'user_id', 'user_name', 'checkin_at', 'checkout_at', 'method', 'validation_code', 'created_at']
        read_only_fields = ['id', 'created_at']

class BadgeSerializer(serializers.ModelSerializer):
    event_title = serializers.ReadOnlyField(source='event.title')
    user_name = serializers.ReadOnlyField(source='user.profile.full_name')

    class Meta:
        model = Badge
        fields = ['id', 'event_id', 'event_title', 'user_id', 'user_name', 'type', 'badge_code', 'printed', 'created_at']
        read_only_fields = ['id', 'created_at']