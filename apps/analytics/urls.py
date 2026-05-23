from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EventViewViewSet, EventAnalyticsDailyViewSet, ActivityLogViewSet

router = DefaultRouter()
router.register(r'event-views', EventViewViewSet)
router.register(r'daily-analytics', EventAnalyticsDailyViewSet)
router.register(r'activity-logs', ActivityLogViewSet)

urlpatterns = [
    path('', include(router.urls)),
]