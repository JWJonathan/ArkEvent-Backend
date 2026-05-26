from rest_framework import generics, permissions, status, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model
from django.utils import timezone
from .serializers import (
    RegisterSerializer, VerifyEmailSerializer, ResendOtpSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer,
    UserProfileSerializer
)
import random

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        # Ici, on pourrait envoyer un OTP par email (pour la vérification)
        return Response({
            "detail": "Inscription réussie. Veuillez vérifier votre email.",
            "user_id": str(user.id)
        }, status=status.HTTP_201_CREATED)

class VerifyEmailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        otp = serializer.validated_data['otp']

        # Simulation : OTP accepté si = '123456'
        if otp != '123456':
            return Response({"detail": "OTP invalide"}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        user.is_verified = True
        user.save(update_fields=['is_verified', 'updated_at'])
        return Response({"detail": "Email vérifié avec succès."})

class ResendOtpView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ResendOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"detail": "Aucun utilisateur trouvé avec cet email."}, status=status.HTTP_404_NOT_FOUND)
        # Envoyer OTP (simulé)
        print(f"OTP pour {email}: 123456")
        return Response({"detail": "OTP renvoyé à votre email."})

class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"detail": "Si l'email existe, un OTP a été envoyé."})
        # Envoyer OTP (simulé)
        print(f"OTP de réinitialisation pour {email}: 123456")
        return Response({"detail": "OTP envoyé à votre email."})

class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']
        new_password = serializer.validated_data['new_password']

        if otp != '123456':
            return Response({"detail": "OTP invalide"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"detail": "Utilisateur introuvable"}, status=status.HTTP_404_NOT_FOUND)

        user.set_password(new_password)
        user.save(update_fields=['password', 'updated_at'])
        return Response({"detail": "Mot de passe réinitialisé avec succès."})

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

# Login est déjà géré par SimpleJWT TokenObtainPairView (voir urls)

from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from .services.services import WalletService
from .serializers import WalletTransactionSerializer
from apps.payments.models import Order  # adaptez l'import

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

# users/views.py (ajout)
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

class SocialLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, provider):
        """
        Connexion via Google, Apple, Facebook
        POST /api/auth/social/google/
        Body: { "token": "id_token_du_provider" }
        """
        social_token = request.data.get('token')
        
        if not social_token:
            return Response({"error": "Token requis"}, status=status.HTTP_400_BAD_REQUEST)

        # TODO: Vérifier le token avec l'API du provider (Google, Apple, FB)
        # Pour le moment, on simule
        email = f"social_{provider}@example.com"
        
        # Créer ou récupérer l'utilisateur
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': f"{provider}_user_{random.randint(1000,9999)}",
                'full_name': f"User {provider}",
                'is_verified': True,  # Les connexions sociales sont vérifiées
            }
        )

        # Générer les tokens JWT
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user_id': str(user.id),
            'email': user.email,
            'is_new': created
        })
    
from rest_framework import viewsets, mixins
from .models import EmailVerificationToken, PasswordResetToken
from apps.core.permissions import IsAdmin
from .serializers import EmailVerificationTokenSerializer, PasswordResetTokenSerializer

class EmailVerificationTokenViewSet(mixins.ListModelMixin,
                                    mixins.RetrieveModelMixin,
                                    mixins.DestroyModelMixin,
                                    viewsets.GenericViewSet):
    queryset = EmailVerificationToken.objects.all().order_by('-created_at')
    serializer_class = EmailVerificationTokenSerializer
    permission_classes = [IsAdmin]  # réservé aux admins

class PasswordResetTokenViewSet(mixins.ListModelMixin,
                                 mixins.RetrieveModelMixin,
                                 mixins.DestroyModelMixin,
                                 viewsets.GenericViewSet):
    queryset = PasswordResetToken.objects.all().order_by('-created_at')
    serializer_class = PasswordResetTokenSerializer
    permission_classes = [IsAdmin]

class AdminUserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('-created_at')
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['email', 'full_name', 'phone']

    def get_queryset(self):
        qs = super().get_queryset()
        role = self.request.query_params.get('role')
        if role:
            qs = qs.filter(role=role)
        return qs

    @action(detail=True, methods=['patch'], url_path='role')
    def update_role(self, request, pk=None):
        user = self.get_object()
        new_role = request.data.get('role')
        if new_role not in [r[0] for r in User.ROLE_CHOICES]:
            return Response({'error': 'Rôle invalide'}, status=status.HTTP_400_BAD_REQUEST)
        user.role = new_role
        user.save(update_fields=['role', 'updated_at'])
        return Response({'status': 'Rôle mis à jour'})

    @action(detail=False, methods=['get'], url_path='all')
    def all_users(self, request):
        return self.list(request)

    @action(detail=True, methods=['post'], url_path='ban')
    def toggle_ban(self, request, pk=None):
        user = self.get_object()
        is_banned = request.data.get('is_banned', False)
        user.is_active = not is_banned
        user.save(update_fields=['is_active', 'updated_at'])
        return Response({'status': 'Ban mis à jour'})
