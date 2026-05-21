from django.contrib import admin
from .models import Profile

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'role', 'is_verified', 'created_at')
    list_filter = ('role', 'is_verified', 'is_public', 'gender', 'language')
    search_fields = ('username', 'first_name', 'last_name', 'phone', 'referral_code')
    readonly_fields = ('id', 'created_at', 'updated_at', 'last_login_at')
    ordering = ('-created_at',)
