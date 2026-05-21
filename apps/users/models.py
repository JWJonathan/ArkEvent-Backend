from django.db import models
import uuid

class Profile(models.Model):
    id = models.UUIDField(primary_key=True, editable=False) # References auth.users(id)
    username = models.CharField(max_length=150, unique=True, null=True, blank=True)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    phone = models.TextField(null=True, blank=True)
    phone_verified = models.BooleanField(default=False)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, null=True, blank=True)
    location = models.TextField(null=True, blank=True)
    timezone = models.TextField(default="UTC")
    language = models.TextField(default="fr")
    avatar_url = models.TextField(null=True, blank=True)
    cover_url = models.TextField(null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    website = models.TextField(null=True, blank=True)
    social_links = models.JSONField(default=dict)
    role = models.CharField(max_length=20, default="user")
    is_verified = models.BooleanField(default=False)
    is_public = models.BooleanField(default=False)
    notification_preferences = models.JSONField(default=dict)
    settings = models.JSONField(default=dict)
    referral_code = models.TextField(unique=True, null=True, blank=True)
    referred_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, db_column='referred_by')
    last_login_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'arkevent"."profiles'

    def __str__(self):
        return self.username or str(self.id)
