from django.db import models
import uuid
from apps.organization.models import Organization

class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.TextField()
    slug = models.TextField(unique=True)

    class Meta:
        db_table = 'arkevent"."event_categories'
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="events", db_column='organization_id')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, db_column='category_id')
    created_by = models.ForeignKey("users.Profile", on_delete=models.CASCADE, related_name="created_events", db_column='created_by')
    title = models.TextField()
    slug = models.TextField(unique=True)
    description = models.TextField(null=True, blank=True)
    poster_url = models.TextField(null=True, blank=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    timezone = models.TextField(default="America/Port-au-Prince")
    venue_name = models.TextField(null=True, blank=True)
    venue_address = models.TextField(null=True, blank=True)
    capacity = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=30, default="draft")
    visibility = models.CharField(max_length=30, default="public")
    currency = models.TextField(default="HTG")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'arkevent"."events'

    def __str__(self):
        return self.title
