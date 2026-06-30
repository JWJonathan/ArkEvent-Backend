from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    full_name = serializers.CharField(required=True)
    phone = serializers.CharField(required=True)
    role = serializers.CharField(default='user')

    class Meta:
        model = User
        fields = ['email', 'password', 'full_name', 'phone', 'role', 'first_name', 'last_name']

    def create(self, validated_data):
        full_name = validated_data.pop('full_name')
        role = validated_data.pop('role', 'user')
        # Séparer le full_name en first/last si non fournis
        first_name = validated_data.pop('first_name', full_name.split(' ')[0])
        last_name = validated_data.pop('last_name', ' '.join(full_name.split(' ')[1:]))

        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            full_name=full_name,
            first_name=first_name,
            last_name=last_name,
            phone=validated_data['phone'],
            role=role,
            username=validated_data['email'].split('@')[0],  # peut être null
            is_verified=False,
        )
        return user

class VerifyEmailSerializer(serializers.Serializer):
    otp = serializers.CharField(max_length=6)

class ResendOtpSerializer(serializers.Serializer):
    email = serializers.EmailField()

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name', 'full_name',
            'phone', 'phone_verified', 'date_of_birth', 'gender', 'location',
            'user_timezone', 'language', 'avatar', 'cover', 'bio', 'website',
            'social_links', 'role', 'is_verified', 'is_public', 'notification_preferences',
            'settings', 'referral_code', 'referred_by', 'affiliate_id',
            'last_login_at', 'accepted_terms_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'email', 'created_at', 'updated_at', 'is_verified', 'role']

    def update(self, instance, validated_data):
        # Empêche la modification du rôle par l'utilisateur normal
        if not self.context['request'].user.is_staff:
            validated_data.pop('role', None)
        return super().update(instance, validated_data)

from apps.wallets.models import Wallet, WalletTransaction

class WalletSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Wallet
        fields = ['id', 'user', 'user_email', 'available_balance', 'pending_balance', 'currency', 'created_at', 'updated_at']


class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTransaction
        fields = ['id', 'wallet', 'transaction_type', 'status', 'amount', 'currency', 'balance_after', 'reference_id', 'description', 'created_at']

from .models import EmailVerificationToken, PasswordResetToken

class EmailVerificationTokenSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source='user.full_name')

    class Meta:
        model = EmailVerificationToken
        fields = ['id', 'user_id', 'user_name', 'token', 'expires_at', 'created_at']

class PasswordResetTokenSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source='user.full_name')

    class Meta:
        model = PasswordResetToken
        fields = ['id', 'user_id', 'user_name', 'token', 'expires_at', 'created_at']

from .models import EmailVerificationToken, PasswordResetToken
from .models import EmailVerificationToken, PasswordResetToken

class EmailVerificationTokenSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source='user.full_name')

    class Meta:
        model = EmailVerificationToken
        fields = ['id', 'user_id', 'user_name', 'token', 'expires_at', 'created_at']

class PasswordResetTokenSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source='user.full_name')

    class Meta:
        model = PasswordResetToken
        fields = ['id', 'user_id', 'user_name', 'token', 'expires_at', 'created_at']
