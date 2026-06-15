from botocore import model
from django.db import models
import uuid
from apps.organization.models import Organization

from django.db import models
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone

class Event(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('cancelled', 'Cancelled'),
        ('postponed', 'Postponed'),
        ('completed', 'Completed'),
    ]
    VISIBILITY_CHOICES = [
        ('public', 'Public'),
        ('private', 'Private'),
        ('unlisted', 'Unlisted'),
    ]
    AGE_CHOICES = [
        ('all', 'All'),
        ('parental_guidance', 'Parental Guidance'),
        ('min_12', '12+'),
        ('min_16', '16+'),
        ('min_18', '18+'),
        ('min_21', '21+'),
    ]
    CHECKIN_CHOICES = [
        ('manual', 'Manual'),
        ('scan', 'Scan'),
        ('face', 'Face'),
        ('code', 'Code'),
    ]
    TARGET_AUDIENCIENCE_CHOICES = [
        ('general', 'Grand public'),
        ('students', 'Etudiants'),
        ('professionals', 'Professionels'), 
        ('families', 'Familles'),
        ('seniors', 'Personnes âgées'),
        ('children', 'Enfants'),
        ('youth', 'Jeunes'),
        ('developers', 'Développeurs'),
        ('designers', 'Designers'),
        ('marketing', 'Marketing'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey('organization.Organization', on_delete=models.CASCADE, db_column='organization_id')
    category = models.ForeignKey('events.EventCategory', on_delete=models.SET_NULL, null=True, blank=True, db_column='category_id')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_column='created_by')
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    short_description = models.TextField(blank=True, default='')
    description = models.TextField(blank=True, default='')
    highlights = models.TextField(blank=True, default='')
    tags = ArrayField(models.TextField(), blank=True, default=list)
    poster = models.ImageField(upload_to='events/posters/', blank=True, null=True)
    banner = models.ImageField(upload_to='events/banners/', blank=True, null=True)
    thumbnail = models.ImageField(upload_to='events/thumbnails/', blank=True, null=True)
    video = models.FileField(upload_to='events/videos/', blank=True, null=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    doors_open = models.DateTimeField(null=True, blank=True)
    timezone = models.CharField(max_length=50, default='America/Port-au-Prince')
    venue_name = models.CharField(max_length=255, blank=True, default='')
    venue_address = models.TextField(blank=True, default='')
    venue_city = models.CharField(max_length=100, blank=True, default='')
    venue_state = models.CharField(max_length=100, blank=True, default='')
    venue_country = models.CharField(max_length=2, default='HT')
    venue_postal_code = models.CharField(max_length=20, blank=True, default='')
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    location_display = models.CharField(max_length=255, blank=True, default='')
    is_online = models.BooleanField(default=False)
    online_url = models.URLField(blank=True, default='')
    capacity = models.PositiveIntegerField(null=True, blank=True)
    age_limit = models.CharField(max_length=20, choices=AGE_CHOICES, default='all')
    is_free = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='public')
    ticket_opens_at = models.DateTimeField(null=True, blank=True)
    ticket_closes_at = models.DateTimeField(null=True, blank=True)
    currency = models.CharField(max_length=3, default='USD')

    min_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    marketing_budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    expected_attendance = models.PositiveIntegerField(null=True, blank=True)
    target_audience = ArrayField(models.CharField(max_length=20, choices=TARGET_AUDIENCIENCE_CHOICES), default=list, blank=True)
    custom_registration_url = models.URLField(blank=True, default='')
    meta_title = models.CharField(max_length=255, blank=True, default='')
    meta_description = models.TextField(blank=True, default='')
    meta_keywords = ArrayField(models.TextField(), blank=True, default=list)
    structured_data = models.JSONField(default=dict, blank=True, null=True)
    has_waitlist = models.BooleanField(default=False)
    waitlist_capacity = models.PositiveIntegerField(null=True, blank=True)
    allow_transfers = models.BooleanField(default=True)
    require_approval = models.BooleanField(default=False)
    checkin_method = models.CharField(max_length=20, choices=CHECKIN_CHOICES, default='scan')
    event_language = models.CharField(max_length=10, default='fr')
    accessibility_info = models.TextField(blank=True, default='')
    sustainability_info = models.TextField(blank=True, default='')
    metadata = models.JSONField(default=dict, blank=True, null=True)
    settings = models.JSONField(default=dict, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'arkevent.events'

    def __str__(self):
        return self.title
    
    def delete(self, using=None, keep_parents=False):
        if self.status in ['published', 'completed']:
            self.deleted_at = timezone.now()
            self.save(update_fields=['deleted_at'])
        else:
            super().delete(using=using, keep_parents=keep_parents)

class EventCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True, default='')
    icon = models.CharField(max_length=255, blank=True, default='')
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
        db_column='parent_id'
    )
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'arkevent.event_categories'
        verbose_name_plural = 'Event categories'

    def __str__(self):
        return self.name


class EventSession(models.Model):
    SESSION_TYPE_CHOICES = [
        ('talk', 'Discussion'),
        ('demo', 'Démonstration'),
        ('workshop', 'Atelier de travail'),
        ('performance', 'Performance'),
        ('panel', 'Panel'),
        ('break', 'Pause'),
        ('networking', 'Réseautage'),
        ('other', 'Autre'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey('Event', on_delete=models.CASCADE, db_column='event_id', related_name='sessions')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    session_type = models.CharField(max_length=20, choices=SESSION_TYPE_CHOICES, null=True, blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=255, blank=True, default='')
    capacity = models.PositiveIntegerField(null=True, blank=True)
    speakers = models.ForeignKey('EventSpeaker', null=True, blank=True, on_delete=models.SET_NULL, db_column='speaker_id')
    image = models.ImageField(upload_to='sessions/images/', blank=True, null=True)
    recording = models.FileField(upload_to='sessions/recordings/', blank=True, null=True)
    requires_ticket = models.BooleanField(default=False)
    ticket_type = models.ForeignKey('tickets.TicketType', null=True, blank=True, on_delete=models.SET_NULL, db_column='ticket_type_id')
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'arkevent.event_sessions'

    def __str__(self):
        return f"{self.title} ({self.event.title})"


class EventSpeaker(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey('Event', on_delete=models.CASCADE, db_column='event_id', related_name='speakers')
    profile = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, db_column='profile_id')
    full_name = models.CharField(max_length=255)
    role = models.CharField(max_length=255, blank=True, default='')
    bio = models.TextField(blank=True, default='')
    photo = models.ImageField(upload_to='speakers/photos/', blank=True, null=True)
    social_links = models.JSONField(default=dict, blank=True, null=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arkevent.event_speakers'

    def __str__(self):
        return self.full_name


class EventOrganizer(models.Model):
    ROLE_CHOICES = [
        ('manager', 'Manager'),
        ('viewer', 'Spectateur'),
        ('controller', 'Contrôleur'),
        ('organizer', 'Organisateur'),
        ('presenter', 'Présentateur'),
        ('speaker', 'Intervenant'),
        ('other', 'Other'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey('Event', on_delete=models.CASCADE, db_column='event_id', related_name='organizers')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_column='user_id')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='manager')
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, db_column='added_by', related_name='added_organizers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arkevent.event_organizers'
        unique_together = ('event', 'user')

    def __str__(self):
        return f"{self.user.email} - {self.role} ({self.event.title})"


class EventMedia(models.Model):
    MEDIA_TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
        ('document', 'Document'),
        ('audio', 'Audio'),
        ('other', 'Other'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey('Event', on_delete=models.CASCADE, db_column='event_id', related_name='media')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, db_column='uploaded_by')
    media_type = models.CharField(max_length=20, choices=MEDIA_TYPE_CHOICES)
    file = models.FileField(upload_to='events/media/')
    alt_text = models.CharField(max_length=255, blank=True, default='')
    title = models.CharField(max_length=255, blank=True, default='')
    description = models.TextField(blank=True, default='')
    sort_order = models.IntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arkevent.event_media'

    def __str__(self):
        return f"{self.media_type}: {self.title or self.file.name}"


class EventSponsor(models.Model):
    ROLE_CHOICES = [
        ('platinum', 'Platinum'),
        ('gold', 'Gold'),
        ('silver', 'Silver'),
        ('bronze', 'Bronze'),
    ]
    LEVEL_CHOICES = [
        ('global', 'Global'),
        ('regional', 'Regional'),
        ('local', 'Local'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey('Event', on_delete=models.CASCADE, db_column='event_id', related_name='sponsors')
    name = models.CharField(max_length=255)
    logo = models.ImageField(upload_to='sponsors/logos/', blank=True, null=True)
    website = models.URLField(blank=True, default='')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='bronze')
    level = models.CharField(max_length=100, choices=LEVEL_CHOICES, default='')
    description = models.TextField(blank=True, default='')
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arkevent.event_sponsors'

    def __str__(self):
        return self.name

class EventFaq(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey('Event', on_delete=models.CASCADE, db_column='event_id', related_name='faqs')
    question = models.TextField()
    answer = models.TextField()
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'arkevent.event_faq'

    def __str__(self):
        return self.question


class Announcement(models.Model):
    URGENCY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey('Event', on_delete=models.CASCADE, db_column='event_id', related_name='announcements')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, db_column='sender_id')
    title = models.CharField(max_length=255, blank=True, default='')
    message = models.TextField()
    urgency = models.CharField(max_length=20, choices=URGENCY_CHOICES, default='normal')
    is_push = models.BooleanField(default=True)
    sent_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arkevent.announcements'

    def __str__(self):
        return self.title or self.message[:50]

class EventShare(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey('Event', on_delete=models.CASCADE, db_column='event_id', related_name='shares')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, db_column='user_id')
    platform = models.CharField(max_length=50)  # ex: 'facebook', 'twitter', 'whatsapp'
    recipient = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arkevent.event_shares'

    def __str__(self):
        return f"{self.platform} - {self.event.title}"
