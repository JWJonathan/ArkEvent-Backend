from django.db import models

class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    category_id = models.UUIDField(null=True)

    created_by = models.ForeignKey("users.Profile", on_delete=models.CASCADE)

    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)

    description = models.TextField(null=True, blank=True)

    poster_url = models.TextField(null=True, blank=True)

    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)

    timezone = models.CharField(max_length=50, default="America/Port-au-Prince")

    venue_name = models.CharField(max_length=255, null=True, blank=True)
    venue_address = models.TextField(null=True, blank=True)

    capacity = models.IntegerField(null=True, blank=True)

    status = models.CharField(max_length=30, default="draft")
    visibility = models.CharField(max_length=30, default="public")

    currency = models.CharField(max_length=10, default="HTG")

    created_at = models.DateTimeField(auto_now_add=True)