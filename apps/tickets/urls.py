from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TicketViewSet, ReservationViewSet

router = DefaultRouter()
router.register(r'my-tickets', TicketViewSet, basename='my-tickets')
router.register(r'reserve', ReservationViewSet, basename='reserve')

urlpatterns = [
    path('', include(router.urls)),
]
