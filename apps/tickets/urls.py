from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TicketTypeViewSet, TicketViewSet, TicketHoldViewSet, TicketTransferViewSet

router = DefaultRouter()
router.register(r'ticket-types', TicketTypeViewSet)
router.register(r'tickets', TicketViewSet)
router.register(r'ticket-holds', TicketHoldViewSet)
router.register(r'ticket-transfers', TicketTransferViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
