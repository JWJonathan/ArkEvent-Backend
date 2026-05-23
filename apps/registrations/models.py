from django.db import models
from django.conf import settings

class RegistrationForm(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    event = models.ForeignKey('events.Event', on_delete=models.CASCADE, db_column='event_id', related_name='registration_forms')
    title = models.CharField(max_length=255, default="Formulaire d'inscription")
    is_required = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'arkevent.registration_forms'
        unique_together = ('event',)

    def __str__(self):
        return f"{self.title} - {self.event.title}"


class RegistrationField(models.Model):
    FIELD_TYPES = [
        ('text', 'Text'),
        ('textarea', 'Textarea'),
        ('select', 'Select'),
        ('checkbox', 'Checkbox'),
        ('date', 'Date'),
        ('file', 'File'),
        ('number', 'Number'),
    ]
    id = models.UUIDField(primary_key=True, editable=False)
    form = models.ForeignKey(RegistrationForm, on_delete=models.CASCADE, db_column='form_id', related_name='fields')
    label = models.CharField(max_length=255)
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES)
    options = models.JSONField(default=list, blank=True)  # pour select, checkbox
    is_required = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arkevent.registration_fields'

    def __str__(self):
        return self.label


class RegistrationAnswer(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    field = models.ForeignKey(RegistrationField, on_delete=models.CASCADE, db_column='field_id', related_name='answers')
    order = models.ForeignKey('payments.Order', on_delete=models.CASCADE, db_column='order_id', related_name='registration_answers')
    ticket = models.ForeignKey('tickets.Ticket', null=True, blank=True, on_delete=models.SET_NULL, db_column='ticket_id')
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arkevent.registration_answers'

    def __str__(self):
        return self.answer[:50]


class Attendance(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    ticket = models.OneToOneField('tickets.Ticket', on_delete=models.CASCADE, db_column='ticket_id', related_name='attendance')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_column='user_id')
    checkin_at = models.DateTimeField(auto_now_add=True)
    checkout_at = models.DateTimeField(null=True, blank=True)
    method = models.CharField(max_length=50, blank=True, default='')
    validation_code = models.CharField(max_length=100, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arkevent.attendances'

    def __str__(self):
        return f"Checkin {self.ticket.token}"


class Badge(models.Model):
    BADGE_TYPES = [
        ('attendee', 'Attendee'),
        ('speaker', 'Speaker'),
        ('staff', 'Staff'),
        ('vip', 'VIP'),
        ('press', 'Press'),
        ('exhibitor', 'Exhibitor'),
    ]
    id = models.UUIDField(primary_key=True, editable=False)
    event = models.ForeignKey('events.Event', on_delete=models.CASCADE, db_column='event_id', related_name='badges')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_column='user_id')
    type = models.CharField(max_length=20, choices=BADGE_TYPES, default='attendee')
    badge_code = models.CharField(max_length=100, unique=True, null=True, blank=True)
    printed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arkevent.badges'
        unique_together = ('event', 'user', 'type')

    def __str__(self):
        return f"{self.type} - {self.user.email}"
    