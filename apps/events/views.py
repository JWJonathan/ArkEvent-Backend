from rest_framework import viewsets, permissions, filters, status, exceptions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.exceptions import PermissionDenied
from django.utils import timezone
from .models import Event, EventCategory, EventSession, EventSpeaker, EventOrganizer, EventMedia, EventSponsor, EventFaq, Announcement, EventShare
from .serializers import EventSerializer, EventCategorySerializer, EventSessionSerializer, EventSpeakerSerializer, EventOrganizerSerializer, EventMediaSerializer, EventSponsorSerializer, EventFaqSerializer, AnnouncementSerializer, EventShareSerializer
from apps.core.permissions import IsAdmin, IsOrganizer, IsEventOwner

class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.filter(deleted_at__isnull=True).order_by('-created_at')
    serializer_class = EventSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
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

        user = self.request.user

        # Si l'utilisateur n'est pas authentifié, ne montrer que les événements publics publiés
        if not user.is_authenticated:
            return qs.filter(visibility='public', status='published')
        
        if user.is_staff:
            return qs

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

        # Pour les non‑staff : événements publics publiés + événements où l'utilisateur est organisateur
        from django.db.models import Q
        return qs.filter(
            Q(visibility='public', status='published') |
            Q(organizers__user=user)
        ).distinct()

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
        from apps.subscriptions.services import SubscriptionService
        is_allowed, message = SubscriptionService.check_limit(self.request.user, 'max_active_events')
        if not is_allowed:
            custom_message = f"{message} Passez à un plan supérieur pour augmenter votre capacité."
            raise exceptions.ValidationError({'detail': custom_message})
            
        serializer.save(created_by=self.request.user)

    # ─── PUT/PATCH /events/{id}/ → updateEvent() ───
    def perform_update(self, serializer):
        # Si le statut passe à un statut actif, vérifier la limite
        new_status = serializer.validated_data.get('status')
        if new_status in ['published', 'draft', 'postponed']:
            instance = self.get_object()
            from apps.subscriptions.services import SubscriptionService
            is_allowed, message = SubscriptionService.check_limit(self.request.user, 'max_active_events', exclude_id=instance.id)
            if not is_allowed:
                custom_message = f"{message} Passez à un plan supérieur pour augmenter votre capacité."
                raise exceptions.ValidationError({'detail': custom_message})

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

    # ─── Nested Routes Support ───
    @action(detail=True, methods=['get'])
    def sessions(self, request, id=None):
        event = self.get_object()
        sessions = event.sessions.filter(deleted_at__isnull=True).order_by('start_time')
        serializer = EventSessionSerializer(sessions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def speakers(self, request, id=None):
        event = self.get_object()
        speakers = event.speakers.all().order_by('sort_order')
        serializer = EventSpeakerSerializer(speakers, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def faq(self, request, id=None):
        event = self.get_object()
        faqs = event.faqs.all().order_by('sort_order')
        serializer = EventFaqSerializer(faqs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def sponsors(self, request, id=None):
        event = self.get_object()
        sponsors = event.sponsors.all().order_by('sort_order')
        serializer = EventSponsorSerializer(sponsors, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def media(self, request, id=None):
        event = self.get_object()
        media = event.media.all().order_by('sort_order')
        serializer = EventMediaSerializer(media, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def organizers(self, request, id=None):
        event = self.get_object()
        organizers = event.organizers.all()
        serializer = EventOrganizerSerializer(organizers, many=True)
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
    
    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(is_active=True)
        return qs

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
from apps.notifications.services import NotificationService


class EventRelatedMixin:

    def filter_queryset_by_event_access(self, qs):
        user = self.request.user
        if user.is_staff:
            return qs
        
        from django.db.models import Q
        
        # Filtre de base : événements publics publiés
        public_events = Q(event__visibility='public', event__status='published')
        
        # Si utilisateur authentifié, ajouter accès via organisation
        if user.is_authenticated:
            return qs.filter(
                public_events | Q(event__organizers__user=user)
            ).distinct()
            
        # Si anonyme, ne retourner que les publics
        return qs.filter(public_events).distinct()

# ──────────────────── SESSIONS ────────────────────
class EventSessionViewSet(viewsets.ModelViewSet, EventRelatedMixin):
    queryset = EventSession.objects.filter(deleted_at__isnull=True).order_by('-start_time')
    serializer_class = EventSessionSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated()]  # ajoutez IsEventOwner plus tard si nécessaire
        return [permissions.AllowAny()]
    
    def get_queryset(self):
        qs = super().get_queryset()
        return self.filter_queryset_by_event_access(qs)

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
        # Récupérer event depuis le payload ou validated_data
        event = serializer.validated_data.get('event')
        if not event:
            event_id = self.request.data.get('event_id')
            if not event_id:
                raise PermissionDenied("L'ID de l'événement est requis.")
            from apps.events.models import Event
            event = Event.objects.get(id=event_id)
        
        serializer.save(event=event)


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
        event = serializer.validated_data.get('event')
        if not event:
            event_id = self.request.data.get('event_id')
            if event_id:
                event = Event.objects.get(id=event_id)
        
        if event:
            from apps.subscriptions.services import SubscriptionService
            is_allowed, message = SubscriptionService.check_feature(event.created_by, 'has_multi_admin')
            if not is_allowed:
                raise exceptions.ValidationError(message)
                
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
        from apps.notifications.services import NotificationService
        media = serializer.save(uploaded_by=self.request.user)
        if media.media_type == 'image':
            NotificationService.notify_during_event(media.event, 'photo')

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
        # Récupérer event depuis le payload ou validated_data
        event = serializer.validated_data.get('event')
        if not event:
            event_id = self.request.data.get('event_id')
            if not event_id:
                raise PermissionDenied("L'ID de l'événement est requis.")
            from apps.events.models import Event
            event = Event.objects.get(id=event_id)
        
        # Check subscription feature: Sponsor Placement
        from apps.subscriptions.services import SubscriptionService
        is_allowed, message = SubscriptionService.check_feature(event.created_by, 'has_sponsor_placement')
        if not is_allowed:
            raise exceptions.ValidationError(message)
            
        serializer.save(event=event)


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
        # Récupérer event depuis le payload ou validated_data
        event = serializer.validated_data.get('event')
        if not event:
            event_id = self.request.data.get('event_id')
            if not event_id:
                raise PermissionDenied("L'ID de l'événement est requis.")
            from apps.events.models import Event
            event = Event.objects.get(id=event_id)
        
        serializer.save(event=event)


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
        # Récupérer event depuis le payload ou validated_data
        event = serializer.validated_data.get('event')
        if not event:
            event_id = self.request.data.get('event_id')
            if not event_id:
                raise exceptions.PermissionDenied("L'ID de l'événement est requis.")
            from apps.events.models import Event
            event = Event.objects.get(id=event_id)
        
        # Check subscription feature: Marketing Tools
        from apps.subscriptions.services import SubscriptionService
        is_allowed, message = SubscriptionService.check_feature(event.created_by, 'has_marketing_tools')
        if not is_allowed:
            raise exceptions.ValidationError(message)
            
        # Si le sender n'est pas fourni, on prend l'utilisateur connecté
        sender = serializer.validated_data.get('sender')
        if not sender:
            announcement = serializer.save(event=event, sender=self.request.user)
        else:
            announcement = serializer.save(event=event)

        # Notify participants of the event
        NotificationService.notify_all_participants(
            event=event,
            title=f"Nouvelle annonce pour {event.title}",
            body=announcement.content,
            metadata={'announcement_id': str(announcement.id)}
        )

    def perform_update(self, serializer):
        serializer.save()

class EventShareViewSet(viewsets.ModelViewSet):
    queryset = EventShare.objects.all().order_by('-created_at')
    serializer_class = EventShareSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated()]  # seuls les admins peuvent lister (à ajuster)

    def perform_create(self, serializer):
        from apps.notifications.services import NotificationService
        share = serializer.save(user=self.request.user)
        # Notify organizer
        event = share.event
        organizer = event.created_by
        NotificationService.notify_social_interaction(organizer, 'share', self.request.user, event)
