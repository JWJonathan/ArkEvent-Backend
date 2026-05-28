from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
import uuid

class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('The Email must be set')
        email = self.normalize_email(email)
        user = self.model(id=uuid.uuid4(), email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'superadmin')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        if not extra_fields.get('username'):
            extra_fields['username'] = email

        return self._create_user(email, password, **extra_fields)

class User(AbstractUser):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('controller', 'Controller'),
        ('admin', 'Admin'),
        ('superadmin', 'Super Admin'),
    ]
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('prefer_not_to_say', 'Prefer not to say')
    ]

    id = models.UUIDField(primary_key=True, editable=False, unique=True)
    email = models.EmailField(unique=True, blank=False)
    username = models.CharField(max_length=150, blank=True, null=True, unique=True)

    # Champs supplémentaires de arkevent.profiles
    first_name = models.CharField(max_length=150, blank=True, default='')
    last_name = models.CharField(max_length=150, blank=True, default='')
    full_name = models.CharField(max_length=300, blank=True, default='')
    phone = models.CharField(max_length=50, blank=True, default='')
    phone_verified = models.BooleanField(default=False)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True, default='')
    location = models.CharField(max_length=255, blank=True, default='')
    user_timezone = models.CharField(max_length=50, blank=True, default='UTC')
    language = models.CharField(max_length=10, blank=True, default='fr')
    avatar = models.ImageField(upload_to='users/avatars/', blank=True, null=True)
    cover = models.ImageField(upload_to='users/covers/', blank=True, null=True)
    bio = models.TextField(blank=True, default='')
    website = models.URLField(blank=True, default='')
    social_links = models.JSONField(default=dict, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    is_verified = models.BooleanField(default=False)
    is_public = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    email_verification_code = models.CharField(max_length=10, blank=True, null=True, db_column='email_verification_code')
    notification_preferences = models.JSONField(default=dict, blank=True)
    settings = models.JSONField(default=dict, blank=True)
    referral_code = models.CharField(max_length=50, blank=True, default='')
    referred_by = models.UUIDField(null=True, blank=True)
    affiliate_id = models.UUIDField(null=True, blank=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    accepted_terms_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    # Remplace les champs de AbstractUser qui ne sont pas nécessaires
    # On garde password, last_login, is_active, is_staff, is_superuser, date_joined

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name', 'phone', 'role']

    class Meta:
        db_table = 'arkevent.users'
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'

    def __str__(self):
        return self.email

    def get_full_name(self):
        return self.full_name or f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name or self.email.split('@')[0]

from django.db import models
from django.core.validators import MinValueValidator
from django.conf import settings


class EmailVerificationToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id')
    token = models.CharField(max_length=255, unique=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arkevent.email_verification_tokens'

class PasswordResetToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id')
    token = models.CharField(max_length=255, unique=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arkevent.password_reset_tokens'

