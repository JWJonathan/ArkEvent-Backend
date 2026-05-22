from django.db import transaction
from django.utils import timezone
from .models import Organization, OrganizationMember

class OrganizationService:

    @staticmethod
    def create_organization(user, data: dict):
        """
        Crée l'organisation et ajoute le créateur comme propriétaire.
        data contient les champs : name, type, short_description, email, phone, website, logo_url, cover_url
        Retourne l'organisation créée.
        """
        with transaction.atomic():
            org = Organization.objects.create(
                name=data['name'],
                type=data.get('type', 'other'),
                short_description=data.get('short_description', ''),
                email=data.get('email', ''),
                phone=data.get('phone', ''),
                website=data.get('website', ''),
                logo_url=data.get('logo_url', ''),
                cover_url=data.get('cover_url', ''),
                created_by=user,
            )
            OrganizationMember.objects.create(
                organization=org,
                user=user,
                org_role='owner',
                status='active',
            )
            return org

    @staticmethod
    def update_organization(org, data: dict, verified=None):
        """
        data peut contenir les champs modifiables.
        verified peut être forcé (admin).
        """
        for field in ['name', 'type', 'short_description', 'email', 'phone', 'website', 'logo_url', 'cover_url']:
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
        return org.members.select_related('user__profile').all().order_by('-joined_at')

    @staticmethod
    def get_all_members():
        return OrganizationMember.objects.select_related('user__profile', 'organization').all().order_by('-joined_at')

    @staticmethod
    def add_member(org, user, role='viewer', status='active', invited_by=None):
        # Vérifier si déjà membre
        if OrganizationMember.objects.filter(organization=org, user=user).exists():
            raise ValueError('Cet utilisateur est déjà membre de l’organisation.')
        return OrganizationMember.objects.create(
            organization=org,
            user=user,
            org_role=role,
            status=status,
            invited_by=invited_by
        )

    @staticmethod
    def update_member(member, role=None, status=None):
        if role:
            member.org_role = role
        if status:
            member.status = status
        member.save(update_fields=['org_role', 'status', 'updated_at'])

    @staticmethod
    def remove_member(member):
        member.delete()