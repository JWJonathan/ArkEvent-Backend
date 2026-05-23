from rest_framework import permissions
from apps.users.models import User
from apps.organization.models import OrganizationMember, Organization

class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        try:
            user = User.objects.get(id=request.user.id)
            return user.role in ['admin', 'superadmin'] and user.is_staff
        except User.DoesNotExist:
            return False

class IsOrganizer(permissions.BasePermission):
    def has_permission(self, request, view):
        # Vérifier que l'utilisateur peut créer un événement pour l'organisation fournie
        org_id = request.data.get('organization_id')
        if not org_id:
            return False
        return OrganizationMember.objects.filter(
            organization_id=org_id,
            user=request.user,
            org_role__in=['owner', 'admin', 'organizer'],
            status='active'
        ).exists()


class IsEventOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_staff:
            return True

        # If object is Event
        if hasattr(obj, 'created_by'):
            if str(obj.created_by_id) == str(request.user.id):
                return True

        # Check if user is admin of the organization that owns the event
        if hasattr(obj, 'organization'):
            return OrganizationMember.objects.filter(
                organization=obj.organization,
                user_id=request.user.id,
                org_role='admin'
            ).exists()

        return False

class IsOrganizationMember(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        # If obj is Organization
        from apps.organization.models import Organization
        if isinstance(obj, Organization):
            return OrganizationMember.objects.filter(
                organization=obj,
                user_id=request.user.id
            ).exists()

        # If obj has organization attribute
        if hasattr(obj, 'organization'):
            return OrganizationMember.objects.filter(
                organization=obj.organization,
                user_id=request.user.id
            ).exists()

        return False

from rest_framework.permissions import BasePermission

class IsOrganizationOwnerOrAdmin(BasePermission):
    """Autorise si l'utilisateur est propriétaire de l'organisation (created_by) ou staff."""
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        if isinstance(obj, Organization):
            return obj.created_by == request.user
        if isinstance(obj, OrganizationMember):
            return obj.organization.created_by == request.user
        return False

class CanManageEvent(BasePermission):
    """
    Autorise si l'utilisateur est admin, propriétaire de l'organisation,
    ou organisateur (manager/controller) de l'événement.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_staff:
            return True
        # obj est un événement
        if hasattr(obj, 'organization'):
            if obj.organization.created_by == user:
                return True
        # Vérifier si l'utilisateur est organisateur de l'événement
        from events.models import EventOrganizer
        return EventOrganizer.objects.filter(
            event_id=obj.id,
            user=user,
            role__in=['manager', 'controller']
        ).exists()
    
    
