from rest_framework import serializers
from .models import Organization, OrganizationMember

class OrganizationSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)

    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'type', 'short_description', 'email', 'phone',
            'website', 'logo_url', 'cover_url', 'created_by', 'created_by_email',
            'verified', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_by_email', 'created_at', 'updated_at']


class OrganizationMemberSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.profile.full_name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = OrganizationMember
        fields = [
            'id', 'organization', 'user', 'user_name', 'user_email',
            'org_role', 'status', 'invited_by', 'joined_at', 'updated_at'
        ]
        read_only_fields = ['id', 'joined_at', 'updated_at']