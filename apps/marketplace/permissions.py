from rest_framework import permissions

class IsProviderOwner(permissions.BasePermission):
    """
    Permission to allow only the owner of the provider profile to edit it.
    """
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return obj.user == request.user


class IsServiceOwner(permissions.BasePermission):
    """
    Permission to allow only the provider who owns the service to edit it.
    """
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return obj.provider.user == request.user


class IsBookingParticipant(permissions.BasePermission):
    """
    Permission to allow only the customer or the provider involved in a booking to view/manage it.
    """
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return obj.customer == request.user or obj.service.provider.user == request.user


class IsVerifiedProvider(permissions.BasePermission):
    """
    Permission to allow only verified providers to perform certain actions.
    """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            hasattr(request.user, 'marketplace_profile') and 
            request.user.marketplace_profile.verified and
            request.user.marketplace_profile.is_active
        )
