from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EventViewSet,
    EventCategoryViewSet,
    EventSessionViewSet,
    EventSpeakerViewSet,
    EventOrganizerViewSet,
    EventMediaViewSet,
    EventSponsorViewSet,
    EventFaqViewSet,
    AnnouncementViewSet,
)

router = DefaultRouter()

# 1. Register specific sub-routes first
router.register(r'event-categories', EventCategoryViewSet, basename='event-category')
router.register(r'categories', EventCategoryViewSet) 

router.register(r'event-sessions', EventSessionViewSet, basename='event-session')
router.register(r'sessions', EventSessionViewSet)

router.register(r'event-speakers', EventSpeakerViewSet, basename='event-speaker')
router.register(r'speakers', EventSpeakerViewSet)

router.register(r'event-organizers', EventOrganizerViewSet, basename='event-organizer')
router.register(r'organizers', EventOrganizerViewSet)

router.register(r'event-media', EventMediaViewSet, basename='event-media')
router.register(r'media', EventMediaViewSet)

router.register(r'event-sponsors', EventSponsorViewSet, basename='event-sponsor')
router.register(r'sponsors', EventSponsorViewSet)

router.register(r'event-faqs', EventFaqViewSet, basename='event-faq')
router.register(r'event-faq', EventFaqViewSet, basename='event-faq-singular')
router.register(r'faqs', EventFaqViewSet)

router.register(r'announcements', AnnouncementViewSet)

# 2. Register the empty prefix LAST
router.register(r'', EventViewSet, basename='event')

urlpatterns = [
    path('', include(router.urls)),
]