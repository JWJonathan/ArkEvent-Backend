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
