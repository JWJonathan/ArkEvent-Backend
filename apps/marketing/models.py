from django.db import models
from django.conf import settings

class EmailCampaign(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('sending', 'Sending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]
    id = models.UUIDField(primary_key=True, editable=False)
    organization = models.ForeignKey('organization.Organization', on_delete=models.CASCADE, db_column='organization_id', related_name='email_campaigns')
    event = models.ForeignKey('events.Event', null=True, blank=True, on_delete=models.SET_NULL, db_column='event_id')
    subject = models.CharField(max_length=255)
    body_html = models.TextField(blank=True, default='')
    body_text = models.TextField(blank=True, default='')
    sender_name = models.CharField(max_length=100, blank=True, default='')
    sender_email = models.EmailField(blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    scheduled_for = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, db_column='created_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'arkevent.email_campaigns'

    def __str__(self):
        return self.subject


class EmailSubscriber(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100, blank=True, default='')
    is_active = models.BooleanField(default=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)
    source = models.CharField(max_length=100, blank=True, default='')
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'arkevent.email_subscribers'

    def __str__(self):
        return self.email