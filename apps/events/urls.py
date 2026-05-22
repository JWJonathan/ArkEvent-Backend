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
router.register(r'', EventViewSet)
router.register(r'categories', EventCategoryViewSet) 
router.register(r'sessions', EventSessionViewSet)
router.register(r'speakers', EventSpeakerViewSet)
router.register(r'organizers', EventOrganizerViewSet)
router.register(r'media', EventMediaViewSet)
router.register(r'sponsors', EventSponsorViewSet)
router.register(r'faqs', EventFaqViewSet)
router.register(r'announcements', AnnouncementViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
