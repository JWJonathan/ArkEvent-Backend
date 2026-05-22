from rest_framework import serializers
from .models import Profile

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = [
            'id', 'username', 'first_name', 'last_name', 'phone',
            'phone_verified', 'avatar_url', 'role', 'created_at'
        ]
        read_only_fields = ['id', 'role', 'created_at']


from .models import Wallet, WalletTransaction

class WalletSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Wallet
        fields = ['id', 'user', 'user_email', 'balance', 'currency', 'created_at', 'updated_at']


class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTransaction
        fields = ['id', 'user', 'amount', 'type', 'status', 'description', 'order', 'metadata', 'created_at']

