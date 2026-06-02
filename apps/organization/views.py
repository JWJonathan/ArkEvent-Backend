from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.users.views import User
from .models import Organization, OrganizationMember
from .serializers import OrganizationSerializer, OrganizationMemberSerializer
from .services import OrganizationService, MemberService
from apps.core.permissions import IsAdmin, IsOrganizationOwnerOrAdmin

class OrganizationViewSet(viewsets.ModelViewSet):
    queryset = Organization.objects.filter(deleted_at__isnull=True)
    serializer_class = OrganizationSerializer

    def get_permissions(self):
        if self.action in ['create', 'my_organizations', 'user_organizations']:
            return [permissions.IsAuthenticated()]
        if self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsOrganizationOwnerOrAdmin()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        # RLS : tout le monde peut voir les organisations non supprimées
        qs = Organization.objects.filter(deleted_at__isnull=True)
        
        # Si admin ou liste simple, on peut potentiellement tout voir
        if self.action == 'list':
            return qs.order_by('-created_at')
            
        user = self.request.user
        
        # Si l'utilisateur est admin, il peut voir tout
        if user.is_authenticated and user.is_staff:
            return qs.order_by('-created_at')
            
        # Sinon, pour les actions de détail, on restreint selon la visibilité
        # (À ajuster selon la logique métier précise si nécessaire)
        return qs

    def perform_create(self, serializer):
        data = serializer.validated_data
        org = OrganizationService.create_organization(self.request.user, data)
        # On retourne l'organisation créée via le serializer
        serializer.instance = org

    def perform_update(self, serializer):
        # On conserve la logique de updateOrganization du Flutter
        instance = self.get_object()
        data = serializer.validated_data
        OrganizationService.update_organization(instance, data)
        # On rafraîchit l'instance
        instance.refresh_from_db()

    def perform_destroy(self, instance):
        OrganizationService.soft_delete_organization(instance)

    # ── Action : GET /organizations/my/ → getMyOrganizations() ──
    @action(detail=False, methods=['get'], url_path='my')
    def my_organizations(self, request):
        orgs = OrganizationService.get_my_organizations(request.user)
        serializer = self.get_serializer(orgs, many=True)
        return Response(serializer.data)

    # ── Action : GET /organizations/user/ → getUserOrganizations() (déjà fait par la list normale si on veut la séparer) ──
    @action(detail=False, methods=['get'], url_path='user')
    def user_organizations(self, request):
        orgs = OrganizationService.get_user_organizations(request.user)
        serializer = self.get_serializer(orgs, many=True)
        return Response(serializer.data)

    # ── Action : GET /organizations/all/ (admin) → getAllOrganizations() ──
    @action(detail=False, methods=['get'], url_path='all', permission_classes=[IsAdmin])
    def all_organizations(self, request):
        orgs = OrganizationService.get_all_organizations()
        page = self.paginate_queryset(orgs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(orgs, many=True)
        return Response(serializer.data)

    # ── Action : GET /organizations/{id}/members/ → getMembers() ──
    @action(detail=True, methods=['get'], url_path='members')
    def members(self, request, pk=None):
        org = self.get_object()
        members = MemberService.get_members(org)
        serializer = OrganizationMemberSerializer(members, many=True)
        return Response(serializer.data)


class OrganizationMemberViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ['add_member', 'update_member', 'remove_member']:
            return [permissions.IsAuthenticated(), IsOrganizationOwnerOrAdmin()]
        if self.action == 'list_all':
            return [permissions.IsAuthenticated(), IsAdmin()]
        return super().get_permissions()
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return OrganizationMember.objects.all()
        org_id = self.request.query_params.get('organization_id')
        if org_id:
            # Vérifier si l'utilisateur est admin de l'organisation
            if OrganizationMember.objects.filter(organization_id=org_id, user=user, org_role='owner').exists():
                return OrganizationMember.objects.filter(organization_id=org_id)
        # Sinon, ne montrer que les appartenances de l'utilisateur
        return OrganizationMember.objects.filter(user=user)

    # ── POST /org-members/add/ → addMember(orgId, userId, role, status) ──
    @action(detail=False, methods=['post'], url_path='add')
    def add_member(self, request):
        org_id = request.data.get('organization_id')
        user_id = request.data.get('user_id')
        role = request.data.get('role', 'viewer')
        status = request.data.get('status', 'active')

        if not org_id or not user_id:
            return Response({'error': 'organization_id et user_id requis'}, status=status.HTTP_400_BAD_REQUEST)

        org = OrganizationService.get_organization_by_id(org_id)
        if not org:
            return Response({'error': 'Organisation introuvable'}, status=status.HTTP_404_NOT_FOUND)

        try:
            user = User.objects.get(id=user_id)
        except:
            return Response({'error': 'Utilisateur introuvable'}, status=status.HTTP_404_NOT_FOUND)

        try:
            member = MemberService.add_member(org, user, role=role, status=status, invited_by=request.user)
            serializer = OrganizationMemberSerializer(member)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # ── PATCH /org-members/{id}/update/ → updateMember(memberId, role, status) ──
    @action(detail=True, methods=['patch'], url_path='update')
    def update_member(self, request, pk=None):
        try:
            member = OrganizationMember.objects.get(id=pk)
        except OrganizationMember.DoesNotExist:
            return Response({'error': 'Membre introuvable'}, status=status.HTTP_404_NOT_FOUND)

        role = request.data.get('role')
        status = request.data.get('status')
        MemberService.update_member(member, role=role, status=status)
        serializer = OrganizationMemberSerializer(member)
        return Response(serializer.data)

    # ── DELETE /org-members/{id}/remove/ → removeMember(memberId) ──
    @action(detail=True, methods=['delete'], url_path='remove')
    def remove_member(self, request, pk=None):
        try:
            member = OrganizationMember.objects.get(id=pk)
        except OrganizationMember.DoesNotExist:
            return Response({'error': 'Membre introuvable'}, status=status.HTTP_404_NOT_FOUND)

        MemberService.remove_member(member)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ── GET /org-members/all/ (admin) → getAllMembers() ──
    @action(detail=False, methods=['get'], url_path='all')
    def list_all(self, request):
        members = MemberService.get_all_members()
        serializer = OrganizationMemberSerializer(members, many=True)
        return Response(serializer.data)

    # ── GET /org-members/?organization_id=... → getMembers(orgId) (alternative) ──
    def list(self, request):
        org_id = request.query_params.get('organization_id')
        if org_id:
            org = OrganizationService.get_organization_by_id(org_id)
            if not org:
                return Response({'error': 'Organisation introuvable'}, status=status.HTTP_404_NOT_FOUND)
            members = MemberService.get_members(org)
        else:
            # Par défaut on ne liste pas tous les membres, sauf admin (déjà protégé par get_permissions)
            if not request.user.is_staff:
                return Response({'error': 'Précisez organization_id'}, status=status.HTTP_400_BAD_REQUEST)
            members = MemberService.get_all_members()
        serializer = OrganizationMemberSerializer(members, many=True)
        return Response(serializer.data)