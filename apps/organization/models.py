from django.db import models
import uuid

class Organization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)

    type = models.CharField(max_length=50, default="company")

    short_description = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=30, null=True, blank=True)

    website = models.TextField(null=True, blank=True)

    city = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=10, default="HT")

    logo_url = models.TextField(null=True, blank=True)

    verified = models.BooleanField(default=False)

    created_by = models.ForeignKey(
        "users.Profile",
        on_delete=models.CASCADE,
        related_name="created_organizations"
    )

    members = models.ManyToManyField(
        "users.Profile",
        through="OrganizationMember",
        related_name="organizations"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arkevent"."organizations'

    def __str__(self):
        return self.name

class OrganizationMember(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    profile = models.ForeignKey("users.Profile", on_delete=models.CASCADE)
    role = models.CharField(max_length=50, default="member")  # admin, member
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arkevent"."organization_members'
        unique_together = ('organization', 'profile')
