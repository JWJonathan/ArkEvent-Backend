from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewsets import (
    WalletViewSet, WalletTransactionViewSet, DepositViewSet,
    WithdrawalViewSet, PayoutViewSet
)

router = DefaultRouter()

router.register(r'transactions', WalletTransactionViewSet, basename='transactions')
router.register(r'deposits', DepositViewSet, basename='deposits')
router.register(r'withdrawals', WithdrawalViewSet, basename='withdrawals')
router.register(r'payouts', PayoutViewSet, basename='payouts')
router.register(r'', WalletViewSet, basename='wallets')

urlpatterns = [
    path('', include(router.urls)),
]
