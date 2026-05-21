from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TicketViewSet, CheckInView
from apps.payments.views import OrderViewSet

router = DefaultRouter()
router.register(r'tickets', TicketViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('generate/', OrderViewSet.as_view({'post': 'create'}), name='ticket-generate'), # Map to order creation
    path('checkin/validate/', CheckInView.as_view(), name='checkin-validate'),
]
