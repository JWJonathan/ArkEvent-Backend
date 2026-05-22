from rest_framework import viewsets
from .models import Profile
from .serializers import ProfileSerializer

class ProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer

    def get_object(self):
        if self.kwargs.get('pk') == 'me':
            return Profile.objects.get(id=self.request.user.id)
        return super().get_object()

from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from .services import WalletService
from .serializers import WalletTransactionSerializer
from payments.models import Order  # adaptez l'import

class WalletViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    # ── GET /wallet/balance/ ──
    @action(detail=False, methods=['get'], url_path='balance')
    def balance(self, request):
        balance = WalletService.get_balance(request.user)
        return Response({'balance': balance})

    # ── POST /wallet/deposit/ ──
    @action(detail=False, methods=['post'], url_path='deposit')
    def deposit(self, request):
        amount = self._parse_positive_amount(request)
        if isinstance(amount, Response):
            return amount
        description = request.data.get('description', '')
        success, _ = WalletService.deposit(request.user, amount, description)
        return Response({'status': 'success'})

    # ── POST /wallet/withdraw/ ──
    @action(detail=False, methods=['post'], url_path='withdraw')
    def withdraw(self, request):
        amount = self._parse_positive_amount(request)
        if isinstance(amount, Response):
            return amount
        description = request.data.get('description', '')
        success, wallet = WalletService.withdraw(request.user, amount, description)
        if not success:
            return Response({'error': 'Solde insuffisant'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status': 'success'})

    # ── POST /wallet/pay/ ──
    @action(detail=False, methods=['post'], url_path='pay')
    def pay_order(self, request):
        order_id = request.data.get('order_id')
        amount = self._parse_positive_amount(request)
        if isinstance(amount, Response):
            return amount
        if not order_id:
            return Response({'error': 'order_id requis'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({'error': 'Commande introuvable'}, status=status.HTTP_404_NOT_FOUND)

        if order.status != 'pending':
            return Response({'error': 'Commande déjà payée ou annulée'}, status=status.HTTP_400_BAD_REQUEST)

        success, wallet = WalletService.pay_with_wallet(request.user, order, amount)
        if not success:
            return Response({'error': 'Solde insuffisant'}, status=status.HTTP_400_BAD_REQUEST)

        # Finalisation de la commande via le PaymentService
        from payments.services import PaymentService
        PaymentService.process_successful_payment(
            order_id=order.id,
            provider_name='wallet',
            transaction_id=f"wallet_{order.id}_{timezone.now().timestamp()}",
            raw_data={}
        )
        return Response({'status': 'success', 'message': 'Paiement effectué avec le portefeuille'})

    # ── GET /wallet/transactions/ ──
    @action(detail=False, methods=['get'], url_path='transactions')
    def transaction_history(self, request):
        transactions = WalletService.get_transaction_history(request.user)
        serializer = WalletTransactionSerializer(transactions, many=True)
        return Response(serializer.data)

    @staticmethod
    def _parse_positive_amount(request):
        """Helper : extrait et valide un montant positif depuis la requête."""
        amount = request.data.get('amount')
        if not amount:
            return Response({'error': 'amount requis'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError
        except (ValueError, TypeError):
            return Response({'error': 'amount doit être un nombre positif'}, status=status.HTTP_400_BAD_REQUEST)
        return amount