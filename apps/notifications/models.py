from django.db import models
from django.conf import settings
import uuid

class NotificationLog(models.Model):
    TYPES = [('push','Push'), ('email','Email'), ('sms','SMS')]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_column='user_id', related_name='notification_logs')
    type = models.CharField(max_length=10, choices=TYPES, default='push')
    title = models.CharField(max_length=255, blank=True, default='')
    body = models.TextField(blank=True, default='')
    event = models.ForeignKey('events.Event', null=True, blank=True, on_delete=models.SET_NULL, db_column='event_id')
    order = models.ForeignKey('payments.Order', null=True, blank=True, on_delete=models.SET_NULL, db_column='order_id')
    metadata = models.JSONField(default=dict, blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'arkevent.notification_logs'

    def __str__(self):
        return f"{self.type} - {self.title}"


class EventNotificationSetting(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_column='user_id', related_name='notification_settings')
    event = models.ForeignKey('events.Event', on_delete=models.CASCADE, db_column='event_id', related_name='notification_settings')
    push_enabled = models.BooleanField(default=True)
    email_enabled = models.BooleanField(default=False)

    class Meta:
        db_table = 'arkevent.event_notification_settings'
        unique_together = ('user', 'event')

    def __str__(self):
        return f"Settings for {self.user.email} on {self.event.title}"


class PushToken(models.Model):
    PLATFORMS = [('ios','iOS'), ('android','Android'), ('web','Web')]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_column='user_id', related_name='push_tokens')
    token = models.TextField()
    platform = models.CharField(max_length=10, choices=PLATFORMS)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'arkevent.push_tokens'
        unique_together = ('user', 'token')

class UserDevice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_column='user_id', related_name='devices')
    device_id = models.CharField(max_length=255, blank=True, default='')
    device_name = models.CharField(max_length=255, blank=True, default='')
    os = models.CharField(max_length=50, blank=True, default='')
    app_version = models.CharField(max_length=50, blank=True, default='')
    last_seen = models.DateTimeField(default=models.functions.Now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arkevent.user_devices'
        