from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrganizationViewSet, OrganizationMemberViewSet

router = DefaultRouter()
router.register(r'organizations', OrganizationViewSet)
router.register(r'org-members', OrganizationMemberViewSet, basename='org-members')

urlpatterns = [
    path('', include(router.urls)),
]
