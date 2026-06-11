from django.db import models
from django.conf import settings
import uuid

class Organization(models.Model):
    ORG_TYPES = [
        ('company', 'Company'),
        ('association', 'Association'),
        ('government', 'Government'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    type = models.CharField(max_length=50, choices=ORG_TYPES, default='other')
    short_description = models.TextField(blank=True, default='')
    email = models.EmailField(blank=True, default='')
    phone = models.CharField(max_length=50, blank=True, default='')
    website = models.URLField(blank=True, default='')
    logo = models.ImageField(upload_to='organizations/logos/', blank=True, null=True)
    cover = models.ImageField(upload_to='organizations/covers/', blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='organizations')
    verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'arkevent.organizations'

    def __str__(self):
        return self.name


class OrganizationMember(models.Model):
    ROLES = [
        ('owner', 'Owner'),
        ('admin', 'Admin'),
        ('organizer', 'Organizer'),
        ('viewer', 'Viewer'),
    ]
    STATUSES = [
        ('active', 'Active'),
        ('invited', 'Invited'),
        ('pending', 'Pending'),
        ('suspended', 'Suspended'),
        ('refused', 'Refused'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    org_role = models.CharField(max_length=50, choices=ROLES, default='viewer')
    status = models.CharField(max_length=50, choices=STATUSES, default='active')
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='invited_members')
    joined_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'arkevent.organization_members'
        unique_together = ('organization', 'user')  # un membre par organisation

    def __str__(self):
        return f"{self.user.email} in {self.organization.name} ({self.org_role})"

