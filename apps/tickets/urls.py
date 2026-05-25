from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TicketTypeViewSet, TicketViewSet, TicketHoldViewSet, TicketTransferViewSet

router = DefaultRouter()
router.register(r'ticket-types', TicketTypeViewSet)
router.register(r'ticket-holds', TicketHoldViewSet)
router.register(r'ticket-transfers', TicketTransferViewSet)
router.register(r'', TicketViewSet)

urlpatterns = [
    path('mine/count/', TicketViewSet.as_view({'get': 'my_tickets_count'}), name='my-tickets-count'),
    path('', include(router.urls)),
]
