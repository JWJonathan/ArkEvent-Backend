from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import Event
from .serializers import EventSerializer
from apps.core.permissions import IsAdmin, IsOrganizer, IsEventOwner

class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.filter(deleted_at__isnull=True)
    serializer_class = EventSerializer
    lookup_field = 'id'  # on utilise l'ID, mais on peut aussi chercher par slug avec une action

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description', 'venue_name', 'venue_city']
    ordering_fields = ['start_date', 'created_at', 'title', 'status']
    ordering = ['-start_date']

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated(), IsOrganizer()]
        if self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsEventOwner()]
        if self.action == 'my_events':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        qs = super().get_queryset()

        # Filtres par query params (correspondant à getAllEvents)
        category_id = self.request.query_params.get('category_id')
        if category_id:
            qs = qs.filter(category_id=category_id)

        only_active = self.request.query_params.get('only_active')
        if only_active and only_active.lower() == 'true':
            qs = qs.filter(status='published')

        org_id = self.request.query_params.get('organization_id')
        if org_id:
            qs = qs.filter(organization_id=org_id)

        slug = self.request.query_params.get('slug')
        if slug:
            qs = qs.filter(slug=slug)

        return qs

    # ─── GET /events/my/ → getMyEvents() ───
    @action(detail=False, methods=['get'], url_path='my')
    def my_events(self, request):
        qs = self.get_queryset().filter(created_by=request.user)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    # ─── GET /events/by-org/{org_id}/ → getEventsByOrganizationId() ───
    @action(detail=False, methods=['get'], url_path='by-org/(?P<org_id>[^/.]+)')
    def by_organization(self, request, org_id=None):
        qs = self.get_queryset().filter(organization_id=org_id)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    # ─── POST /events/ → createEvent() ───
    def perform_create(self, serializer):
        # created_by automatiquement assigné à l'utilisateur authentifié
        # L'organization_id doit être valide et l'utilisateur doit être organisateur
        serializer.save(created_by=self.request.user)

    # ─── PUT/PATCH /events/{id}/ → updateEvent() ───
    def perform_update(self, serializer):
        # Si le statut passe à 'published', on met à jour published_at
        if serializer.validated_data.get('status') == 'published':
            serializer.save(published_at=timezone.now())
        else:
            serializer.save()

    # ─── DELETE /events/{id}/ → deleteEvent() (soft delete) ───
    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save()

    # ─── Récupérer par slug (optionnel) ───
    @action(detail=False, methods=['get'], url_path='by-slug/(?P<slug>[^/.]+)')
    def by_slug(self, request, slug=None):
        event = self.get_queryset().filter(slug=slug).first()
        if not event:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(event)
        return Response(serializer.data)
    
from rest_framework import viewsets, permissions
from .models import EventCategory
from .serializers import EventCategorySerializer
from apps.core.permissions import IsAdmin
from django.utils import timezone

class EventCategoryViewSet(viewsets.ModelViewSet):
    queryset = EventCategory.objects.filter(deleted_at__isnull=True).order_by('sort_order', 'name')
    serializer_class = EventCategorySerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsAdmin()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        # L'ID est généré automatiquement par la base de données (uuid_generate_v4)
        serializer.save()

    def perform_update(self, serializer):
        serializer.save(updated_at=timezone.now())

    def perform_destroy(self, instance):
        # Soft delete : on met deleted_at au lieu de supprimer
        instance.deleted_at = timezone.now()
        instance.save() 


from rest_framework import viewsets, permissions
from .models import EventSession, EventSpeaker, EventOrganizer, EventMedia, EventSponsor, EventFaq, Announcement
from .serializers import (
    EventSessionSerializer, EventSpeakerSerializer,
    EventOrganizerSerializer, EventMediaSerializer, EventSponsorSerializer,
    EventFaqSerializer, AnnouncementSerializer
)
from django.utils import timezone

# ──────────────────── SESSIONS ────────────────────
class EventSessionViewSet(viewsets.ModelViewSet):
    queryset = EventSession.objects.filter(deleted_at__isnull=True).order_by('-start_time')
    serializer_class = EventSessionSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated()]  # ajoutez IsEventOwner plus tard si nécessaire
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        # Le champ event_id doit être passé dans le payload
        serializer.save()

    def perform_update(self, serializer):
        serializer.save(updated_at=timezone.now())

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save()


# ──────────────────── SPEAKERS ────────────────────
class EventSpeakerViewSet(viewsets.ModelViewSet):
    queryset = EventSpeaker.objects.all().order_by('sort_order', '-created_at')
    serializer_class = EventSpeakerSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()


# ──────────────────── ORGANIZERS ────────────────────
class EventOrganizerViewSet(viewsets.ModelViewSet):
    queryset = EventOrganizer.objects.all().order_by('-created_at')
    serializer_class = EventOrganizerSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated()]  # liste également authentifié (admin plus tard)

    def perform_create(self, serializer):
        serializer.save(added_by=self.request.user)  # l'utilisateur qui ajoute

    def perform_update(self, serializer):
        serializer.save()


# ──────────────────── MEDIA ────────────────────
class EventMediaViewSet(viewsets.ModelViewSet):
    queryset = EventMedia.objects.all().order_by('-created_at')
    serializer_class = EventMediaSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save()


# ──────────────────── SPONSORS ────────────────────
class EventSponsorViewSet(viewsets.ModelViewSet):
    queryset = EventSponsor.objects.all().order_by('sort_order', '-created_at')
    serializer_class = EventSponsorSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()

class EventFaqViewSet(viewsets.ModelViewSet):
    queryset = EventFaq.objects.all().order_by('sort_order', '-created_at')
    serializer_class = EventFaqSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated()]   # idéalement ajouter IsEventOwner
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save(updated_at=timezone.now())


class AnnouncementViewSet(viewsets.ModelViewSet):
    queryset = Announcement.objects.all().order_by('-created_at')
    serializer_class = AnnouncementSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        # Si le sender n'est pas fourni, on prend l'utilisateur connecté
        if not serializer.validated_data.get('sender'):
            serializer.save(sender=self.request.user)
        else:
            serializer.save()

    def perform_update(self, serializer):
        serializer.save()