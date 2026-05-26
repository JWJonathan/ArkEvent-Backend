# admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, Wallet, WalletTransaction, EmailVerificationToken, PasswordResetToken


class CustomUserAdmin(BaseUserAdmin):
    # Champs affichés dans la liste des utilisateurs
    list_display = (
        'email',
        'full_name',
        'role',
        'is_verified',
        'is_active',
        'is_staff',
        'created_at',
    )
    list_filter = (
        'role',
        'is_verified',
        'is_active',
        'is_staff',
        'is_superuser',
        'gender',
        'language',
    )
    search_fields = ('email', 'username', 'full_name', 'first_name', 'last_name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'last_login_at', 'accepted_terms_at')

    # Champs dans le formulaire d’édition
    fieldsets = (
        (_('Login credentials'), {
            'fields': ('email', 'username', 'password')
        }),
        (_('Personal information'), {
            'fields': (
                'first_name', 'last_name', 'full_name',
                'date_of_birth', 'gender', 'bio', 'avatar', 'cover',
            )
        }),
        (_('Contact & localisation'), {
            'fields': (
                'phone', 'phone_verified', 'location',
                'user_timezone', 'language', 'website', 'social_links',
            )
        }),
        (_('Roles & permissions'), {
            'fields': (
                'role', 'is_verified', 'is_public',
                'is_active', 'is_staff', 'is_superuser',
                'groups', 'user_permissions',
            )
        }),
        (_('Referral & affiliation'), {
            'fields': ('referral_code', 'referred_by', 'affiliate_id'),
        }),
        (_('Preferences & settings'), {
            'fields': ('notification_preferences', 'settings'),
        }),
        (_('Important dates'), {
            'fields': ('last_login', 'last_login_at', 'accepted_terms_at',
                       'created_at', 'updated_at', 'deleted_at'),
        }),
    )

    # Champs pour la création d’un utilisateur (formulaire simplifié)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'username', 'password1', 'password2',
                'full_name', 'phone', 'role',
            ),
        }),
    )

    # Gestion du champ email comme identifiant principal
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['email'].required = True
        return form


class WalletAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'balance', 'currency', 'created_at', 'updated_at')
    search_fields = ('user__email', 'user__username', 'user__full_name')
    list_filter = ('currency',)
    readonly_fields = ('created_at', 'updated_at')

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User email'
    user_email.admin_order_field = 'user__email'


class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'amount', 'type', 'status', 'created_at')
    list_filter = ('type', 'status')
    search_fields = ('user__email', 'description')
    readonly_fields = ('created_at',)
    # autocomplete_fields = ['user', 'order'] # OrderAdmin needs search_fields for this to work

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User email'
    user_email.admin_order_field = 'user__email'

@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'expires_at', 'created_at')
    search_fields = ('user__email', 'token')
    readonly_fields = ('created_at',)

@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'expires_at', 'created_at')
    search_fields = ('user__email', 'token')
    readonly_fields = ('created_at',)


# Enregistrement des modèles
admin.site.register(User, CustomUserAdmin)
admin.site.register(Wallet, WalletAdmin)
admin.site.register(WalletTransaction, WalletTransactionAdmin)
