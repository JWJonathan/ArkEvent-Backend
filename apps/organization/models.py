from django.db import models
import uuid

class Organization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.TextField()
    slug = models.TextField(unique=True, null=True, blank=True)
    type = models.TextField(default="company")
    short_description = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    email = models.TextField(null=True, blank=True)
    phone = models.TextField(null=True, blank=True)
    website = models.TextField(null=True, blank=True)
    city = models.TextField(null=True, blank=True)
    country = models.TextField(default="HT")
    logo_url = models.TextField(null=True, blank=True)
    verified = models.BooleanField(default=False)
    created_by = models.ForeignKey("users.Profile", on_delete=models.CASCADE, related_name="created_organizations", db_column='created_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'arkevent"."organizations'

    def __str__(self):
        return self.name

class OrganizationMember(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, db_column='organization_id')
    user = models.ForeignKey("users.Profile", on_delete=models.CASCADE, db_column='user_id')
    org_role = models.CharField(max_length=50, default="staff")
    joined_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'arkevent"."organization_members'
        unique_together = ('organization', 'user')
