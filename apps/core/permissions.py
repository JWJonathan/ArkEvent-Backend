from rest_framework import permissions
from apps.users.models import Profile
from apps.organization.models import OrganizationMember

class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        try:
            profile = Profile.objects.get(id=request.user.id)
            return profile.role in ['admin', 'superadmin']
        except Profile.DoesNotExist:
            return False

class IsOrganizer(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        try:
            profile = Profile.objects.get(id=request.user.id)
            return profile.role in ['organizer', 'admin', 'superadmin']
        except Profile.DoesNotExist:
            return False

class IsEventOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        # If object is Event
        if hasattr(obj, 'created_by'):
            if str(obj.created_by.id) == str(request.user.id):
                return True

        # Check if user is admin of the organization that owns the event
        if hasattr(obj, 'organization'):
            return OrganizationMember.objects.filter(
                organization=obj.organization,
                profile_id=request.user.id,
                role='admin'
            ).exists()

        return False

class IsOrganizationMember(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        # If obj is Organization
        if hasattr(obj, 'members'):
            return obj.members.filter(id=request.user.id).exists()

        # If obj has organization attribute
        if hasattr(obj, 'organization'):
            return obj.organization.members.filter(id=request.user.id).exists()

        return False
