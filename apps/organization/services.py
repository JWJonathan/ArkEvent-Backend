from django.db import transaction
from django.utils import timezone
from .models import Organization, OrganizationMember

class OrganizationService:

    @staticmethod
    def create_organization(user, data: dict):
        """
        Crée l'organisation et ajoute le créateur comme propriétaire.
        data contient les champs : name, type, short_description, email, phone, website, logo, cover
        Retourne l'organisation créée.
        """
        from apps.notifications.services import NotificationService
        with transaction.atomic():
            org = Organization.objects.create(
                name=data['name'],
                type=data.get('type', 'other'),
                short_description=data.get('short_description', ''),
                email=data.get('email', ''),
                phone=data.get('phone', ''),
                website=data.get('website', ''),
                logo=data.get('logo', None),
                cover=data.get('cover', None),
                created_by=user,
            )
            OrganizationMember.objects.create(
                organization=org,
                user=user,
                org_role='owner',
                status='active',
            )
            NotificationService.notify_organization_created(user, org)
            return org

    @staticmethod
    def update_organization(org, data: dict, verified=None):
        """
        data peut contenir les champs modifiables.
        verified peut être forcé (admin).
        """
        for field in ['name', 'type', 'short_description', 'email', 'phone', 'website', 'logo', 'cover']:
            if field in data:
                setattr(org, field, data[field])
        if verified is not None:
            org.verified = verified
        org.save(update_fields=[*data.keys(), 'updated_at'] if not verified else [*data.keys(), 'verified', 'updated_at'])

    @staticmethod
    def soft_delete_organization(org):
        org.deleted_at = timezone.now()
        org.save(update_fields=['deleted_at'])

    @staticmethod
    def get_user_organizations(user):
        """Organisations créées par l'utilisateur."""
        return Organization.objects.filter(created_by=user, deleted_at__isnull=True).order_by('-created_at')

    @staticmethod
    def get_my_organizations(user):
        """Organisations où l'utilisateur est membre (active ou invité)."""
        return Organization.objects.filter(
            members__user=user,
            members__status__in=['active', 'invited'],
            # created_by=user,
            deleted_at__isnull=True
        ).distinct().order_by('-created_at')

    @staticmethod
    def get_all_organizations():
        return Organization.objects.filter(deleted_at__isnull=True).order_by('-created_at')

    @staticmethod
    def get_organization_by_id(org_id):
        try:
            return Organization.objects.get(id=org_id, deleted_at__isnull=True)
        except Organization.DoesNotExist:
            return None


class MemberService:

    @staticmethod
    def get_members(org):
        """Retourne tous les membres d'une organisation avec le nom du profil."""
        return org.members.select_related('user__marketplace_profile').all().order_by('-joined_at')

    @staticmethod
    def get_all_members():
        return OrganizationMember.objects.select_related('user__marketplace_profile', 'organization').all().order_by('-joined_at')

    @staticmethod
    def add_member(org, user, role='viewer', status='active', invited_by=None):
        from apps.notifications.services import NotificationService
        # Vérifier si déjà membre
        if OrganizationMember.objects.filter(organization=org, user=user).exists():
            raise ValueError('Cet utilisateur est déjà membre de l’organisation.')

        member = OrganizationMember.objects.create(
            organization=org,
            user=user,
            org_role=role,
            status=status,
            invited_by=invited_by
        )

        if status == 'invited':
            NotificationService.notify_member_invite(org, user, invited_by)
        elif status == 'pending':
            NotificationService.notify_org_admins(org, 'new_request', user)
        elif status == 'active':
            NotificationService.notify_org_admins(org, 'new_member', user)

        return member

    @staticmethod
    def update_member(member, role=None, status=None):
        from apps.notifications.services import NotificationService
        old_status = member.status
        old_role = member.org_role

        if role:
            member.org_role = role
        if status:
            member.status = status
        member.save(update_fields=['org_role', 'status', 'updated_at'])

        if status and status != old_status:
            if status == 'active':
                NotificationService.notify_membership_status(member.organization, member.user, 'accepted')
                NotificationService.notify_org_admins(member.organization, 'new_member', member.user)
            elif status == 'refused':
                NotificationService.notify_membership_status(member.organization, member.user, 'refused')

        if role and role != old_role:
            NotificationService.notify_membership_status(member.organization, member.user, 'role_assigned')
            NotificationService.notify_org_admins(member.organization, 'role_modified', member.user)

    @staticmethod
    def remove_member(member):
        from apps.notifications.services import NotificationService
        org = member.organization
        user = member.user
        member.delete()
        NotificationService.notify_org_admins(org, 'member_left', user)