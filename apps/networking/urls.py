from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NetworkingMatchViewSet, SocialPostViewSet

router = DefaultRouter()
router.register(r'networking-matches', NetworkingMatchViewSet)
router.register(r'social-posts', SocialPostViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
