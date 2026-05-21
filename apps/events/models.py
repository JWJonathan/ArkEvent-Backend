from django.db import models
import uuid
from apps.organization.models import Organization

class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    class Meta:
        db_table = 'arkevent"."categories'
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="events")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)

    created_by = models.ForeignKey("users.Profile", on_delete=models.CASCADE, related_name="created_events")

    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)

    description = models.TextField(null=True, blank=True)

    poster_url = models.TextField(null=True, blank=True)

    start_date = models.DateTimeField(db_index=True) # Added index
    end_date = models.DateTimeField(null=True, blank=True)

    timezone = models.CharField(max_length=50, default="America/Port-au-Prince")

    venue_name = models.CharField(max_length=255, null=True, blank=True)
    venue_address = models.TextField(null=True, blank=True)

    capacity = models.IntegerField(null=True, blank=True)

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="draft", db_index=True)

    VISIBILITY_CHOICES = [
        ('public', 'Public'),
        ('private', 'Private'),
        ('unlisted', 'Unlisted'),
    ]
    visibility = models.CharField(max_length=30, choices=VISIBILITY_CHOICES, default="public")

    currency = models.CharField(max_length=10, default="HTG")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'arkevent"."events'
        indexes = [
            models.Index(fields=['start_date', 'status']),
        ]

    def __str__(self):
        return self.title
