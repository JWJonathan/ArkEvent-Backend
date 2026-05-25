from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrganizationViewSet, OrganizationMemberViewSet

router = DefaultRouter()
router.register(r'org-members', OrganizationMemberViewSet, basename='org-members')
router.register(r'', OrganizationViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
