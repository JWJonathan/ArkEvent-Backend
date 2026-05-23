from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegistrationFormViewSet, RegistrationFieldViewSet,
    RegistrationAnswerViewSet, AttendanceViewSet, BadgeViewSet
)

router = DefaultRouter()
router.register(r'registration-forms', RegistrationFormViewSet)
router.register(r'registration-fields', RegistrationFieldViewSet)
router.register(r'registration-answers', RegistrationAnswerViewSet)
router.register(r'attendances', AttendanceViewSet)
router.register(r'badges', BadgeViewSet)

urlpatterns = [
    path('', include(router.urls)),
]