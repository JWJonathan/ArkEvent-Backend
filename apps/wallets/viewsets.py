"""
Wallet ViewSets for Django REST Framework
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from .models import Wallet, WalletTransaction, Deposit, Withdrawal, Payout
from .serializers import (
    WalletSerializer, WalletTransactionSerializer, DepositSerializer,
    WithdrawalSerializer, PayoutSerializer
)
from .services import DepositService, WithdrawalService, WalletAnalyticsService
from apps.core.permissions import IsWalletOwner, CanApproveWithdrawal


class WalletViewSet(viewsets.ReadOnlyModelViewSet):
    """Wallet dashboard and balance information."""
    serializer_class = WalletSerializer
    permission_classes = [permissions.IsAuthenticated, IsWalletOwner]
    
    def get_queryset(self):
        return Wallet.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get'], url_path='my-wallet', permission_classes=[permissions.IsAuthenticated])
    def my_wallet(self, request):
        """Get current user's wallet."""
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(wallet)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='summary', permission_classes=[permissions.IsAuthenticated])
    def summary(self, request):
        """Get wallet summary with statistics."""
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        summary = WalletAnalyticsService.get_wallet_summary(wallet)
        stats = WalletAnalyticsService.get_transaction_statistics(wallet)
        return Response({'wallet': summary, 'stats': stats})


class WalletTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """Transaction history and ledger."""
    serializer_class = WalletTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['transaction_type', 'status']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return WalletTransaction.objects.filter(wallet__user=self.request.user)


class DepositViewSet(viewsets.ViewSet):
    """Deposit management."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DepositSerializer
    
    @action(detail=False, methods=['post'], url_path='create-deposit', permission_classes=[permissions.IsAuthenticated])
    def create_deposit(self, request):
        """Create new deposit request."""
        from apps.wallets.models import Wallet, Deposit
        
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        
        amount = request.data.get('amount')
        currency = request.data.get('currency', 'USD')
        deposit_method = request.data.get('deposit_method')
        
        try:
            deposit = DepositService.create_deposit(
                wallet=wallet,
                amount=amount,
                currency=currency,
                deposit_method=deposit_method
            )
            serializer = DepositSerializer(deposit)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], url_path='paypal-deposit')
    def paypal_deposit(self, request, pk=None):
        """Initiate PayPal payment for a deposit."""
        from apps.payments.providers.paypal import PayPalProvider
        from .models import Deposit
        
        try:
            deposit = Deposit.objects.get(id=pk, wallet__user=request.user)
            if deposit.status != 'pending':
                return Response({'error': 'Ce dépôt n\'est plus en attente.'}, status=status.HTTP_400_BAD_REQUEST)
                
            provider = PayPalProvider()
            return_url = request.data.get('return_url')
            cancel_url = request.data.get('cancel_url')
            
            session_data = provider.create_payment_session(deposit, user=request.user, return_url=return_url, cancel_url=cancel_url)
            
            if session_data:
                return Response({
                    'approval_url': session_data['approval_url'],
                    'payment_id': session_data['payment_id'],
                    'deposit_id': deposit.id
                })
            return Response({'error': 'Impossible de créer la session PayPal.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Deposit.DoesNotExist:
            return Response({'error': 'Dépôt introuvable.'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'], url_path='verify-iap')
    def verify_iap(self, request, pk=None):
        """Verify Google Play IAP for a wallet deposit."""
        from .models import Deposit
        try:
            deposit = Deposit.objects.get(id=pk, wallet__user=request.user)
            token = request.data.get('purchase_token')
            product_id = request.data.get('product_id')
            package_name = request.data.get('package_name', "com.arkevent.app")

            if not token or not product_id:
                return Response({'error': 'purchase_token et product_id sont requis.'}, status=status.HTTP_400_BAD_REQUEST)

            result = verify_google_purchase(package_name, product_id, token, is_subscription=False)
            
            if result.get('purchaseState') == 0:
                DepositService.confirm_deposit(
                    deposit=deposit,
                    transaction_id=token,
                    provider_metadata=result
                )
                return Response({'status': 'success', 'deposit_id': deposit.id})
            return Response({'error': 'L\'achat n\'est pas validé par Google Play.'}, status=status.HTTP_400_BAD_REQUEST)
        except Deposit.DoesNotExist:
            return Response({'error': 'Dépôt introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='my-deposits', permission_classes=[permissions.IsAuthenticated])
    def my_deposits(self, request):
        """Get user's deposits."""
        deposits = Deposit.objects.filter(wallet__user=request.user).order_by('-created_at')
        serializer = DepositSerializer(deposits, many=True)
        return Response(serializer.data)


class WithdrawalViewSet(viewsets.ViewSet):
    """Withdrawal management."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = WithdrawalSerializer
    
    @action(detail=False, methods=['post'], url_path='create-withdrawal', permission_classes=[permissions.IsAuthenticated])
    def create_withdrawal(self, request):
        """Request a withdrawal."""
        from apps.wallets.models import Wallet
        
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        
        amount = request.data.get('amount')
        destination_provider = request.data.get('destination_provider')
        destination_identifier = request.data.get('destination_identifier')
        withdrawal_speed = request.data.get('withdrawal_speed', 'standard')
        
        try:
            withdrawal = WithdrawalService.create_withdrawal(
                wallet=wallet,
                amount=amount,
                destination_provider=destination_provider,
                destination_identifier=destination_identifier,
                withdrawal_speed=withdrawal_speed
            )
            serializer = WithdrawalSerializer(withdrawal)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], url_path='my-withdrawals', permission_classes=[permissions.IsAuthenticated])
    def my_withdrawals(self, request):
        """Get user's withdrawal requests."""
        withdrawals = Withdrawal.objects.filter(wallet__user=request.user).order_by('-created_at')
        serializer = WithdrawalSerializer(withdrawals, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], url_path='approve-withdrawal', permission_classes=[CanApproveWithdrawal])
    def approve_withdrawal(self, request):
        """Approve a withdrawal (staff only)."""
        withdrawal_id = request.data.get('withdrawal_id')
        transaction_id = request.data.get('transaction_id')
        
        try:
            from apps.wallets.models import Withdrawal
            withdrawal = Withdrawal.objects.get(id=withdrawal_id)
            
            WithdrawalService.approve_withdrawal(withdrawal, transaction_id)
            serializer = WithdrawalSerializer(withdrawal)
            return Response(serializer.data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], url_path='reject-withdrawal', permission_classes=[CanApproveWithdrawal])
    def reject_withdrawal(self, request):
        """Reject a withdrawal (staff only)."""
        withdrawal_id = request.data.get('withdrawal_id')
        reason = request.data.get('reason', '')
        
        try:
            from apps.wallets.models import Withdrawal
            withdrawal = Withdrawal.objects.get(id=withdrawal_id)
            
            WithdrawalService.reject_withdrawal(withdrawal, reason)
            serializer = WithdrawalSerializer(withdrawal)
            return Response(serializer.data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PayoutViewSet(viewsets.ReadOnlyModelViewSet):
    """Payout history (staff view)."""
    serializer_class = PayoutSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Payout.objects.all()
        return Payout.objects.filter(wallet__user=user)
