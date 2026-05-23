from django.db import models
from django.conf import settings

class EventView(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    event = models.ForeignKey('events.Event', on_delete=models.CASCADE, db_column='event_id', related_name='views')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, db_column='user_id')
    source = models.CharField(max_length=255, blank=True, default='')
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arkevent.event_views'

    def __str__(self):
        return f"View {self.event.title} at {self.viewed_at}"


class EventAnalyticsDaily(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    event = models.ForeignKey('events.Event', on_delete=models.CASCADE, db_column='event_id', related_name='daily_analytics')
    date = models.DateField()
    views = models.PositiveIntegerField(default=0)
    unique_views = models.PositiveIntegerField(default=0)
    shares = models.PositiveIntegerField(default=0)
    orders = models.PositiveIntegerField(default=0)
    tickets_sold = models.PositiveIntegerField(default=0)
    revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arkevent.event_analytics_daily'
        unique_together = ('event', 'date')

    def __str__(self):
        return f"{self.event.title} - {self.date}"


class ActivityLog(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, db_column='user_id')
    action = models.CharField(max_length=255)
    entity_type = models.CharField(max_length=100, blank=True, default='')
    entity_id = models.UUIDField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arkevent.activity_logs'

    def __str__(self):
        return f"{self.action} by {self.user}"