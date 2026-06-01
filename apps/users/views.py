from rest_framework import generics, permissions, status, filters, viewsets, mixins
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model
from django.utils import timezone
from .serializers import (
    RegisterSerializer, VerifyEmailSerializer, ResendOtpSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer,
    UserProfileSerializer
)
from .tasks import send_verification_email, send_password_reset_email
import random
import string

User = get_user_model()

def generate_verification_code(length=6):
    """Generate a random 6-digit verification code."""
    return ''.join(random.choices(string.digits, k=length))

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate and store verification code
        code = generate_verification_code()
        user.email_verification_code = code
        user.save(update_fields=['email_verification_code'])
        
        # Send verification email asynchronously
        send_verification_email.delay(str(user.id), code)
        
        return Response({
            "success": True,
            "data": {
                "detail": "Inscription réussie. Veuillez vérifier votre email.",
                "user_id": str(user.id)
            },
            "message": ""
        }, status=status.HTTP_201_CREATED)

class VerifyEmailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data['otp']

        user = request.user
        
        # Check if code matches
        if user.email_verification_code != code:
            return Response({
                "success": False,
                "errors": {"otp": "Code de vérification invalide"}
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Mark email as verified
        user.email_verified = True
        user.is_verified = True
        user.email_verification_code = None  # Clear the code
        user.save(update_fields=['email_verified', 'is_verified', 'email_verification_code', 'updated_at'])
        
        return Response({
            "success": True,
            "data": {"detail": "Email vérifié avec succès."},
            "message": ""
        }, status=status.HTTP_200_OK)

class ResendOtpView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ResendOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        try:
            user = User.objects.get(email=email)
            
            # Check if already verified
            if user.email_verified:
                return Response({
                    "success": False,
                    "errors": {"email": "Cet email est déjà vérifié"}
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Generate new code
            code = generate_verification_code()
            user.email_verification_code = code
            user.save(update_fields=['email_verification_code'])
            
            # Send verification email
            send_verification_email.delay(str(user.id), code)
            
            return Response({
                "success": True,
                "data": {"detail": "Code de vérification renvoyé à votre email."},
                "message": ""
            }, status=status.HTTP_200_OK)
        
        except User.DoesNotExist:
            return Response({
                "success": False,
                "errors": {"email": "Utilisateur non trouvé"}
            }, status=status.HTTP_404_NOT_FOUND)

class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        try:
            user = User.objects.get(email=email)
            
            # Generate reset code
            code = generate_verification_code()
            user.email_verification_code = code
            user.save(update_fields=['email_verification_code'])
            
            # Send password reset email
            send_password_reset_email.delay(str(user.id), code)
            
            return Response({
                "success": True,
                "data": {"detail": "Code de réinitialisation envoyé à votre email."},
                "message": ""
            }, status=status.HTTP_200_OK)
        
        except User.DoesNotExist:
            # Don't reveal if user exists or not for security reasons
            return Response({
                "success": True,
                "data": {"detail": "Si l'email existe, un code de réinitialisation a été envoyé."},
                "message": ""
            }, status=status.HTTP_200_OK)

class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        code = serializer.validated_data['otp']
        new_password = serializer.validated_data['new_password']

        try:
            user = User.objects.get(email=email)
            
            # Check if code matches
            if user.email_verification_code != code:
                return Response({
                    "success": False,
                    "errors": {"otp": "Code de réinitialisation invalide"}
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update password
            user.set_password(new_password)
            user.email_verification_code = None  # Clear the code
            user.save(update_fields=['password', 'email_verification_code', 'updated_at'])
            
            from apps.notifications.services import NotificationService
            NotificationService.notify_security(user, 'password')
            
            return Response({
                "success": True,
                "data": {"detail": "Mot de passe réinitialisé avec succès."},
                "message": ""
            }, status=status.HTTP_200_OK)
        
        except User.DoesNotExist:
            return Response({
                "success": False,
                "errors": {"email": "Utilisateur non trouvé"}
            }, status=status.HTTP_404_NOT_FOUND)

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        from apps.notifications.services import NotificationService
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        old_email = instance.email
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        if 'email' in request.data and request.data['email'] != old_email:
            NotificationService.notify_security(instance, 'email')
            
        return Response(serializer.data)

from rest_framework_simplejwt.views import TokenObtainPairView

class CustomTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            email = request.data.get('email')
            user = User.objects.filter(email=email).first()
            if user:
                from apps.notifications.services import NotificationService
                NotificationService.notify_security(user, 'login')
        return response

# users/views.py (ajout)
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.conf import settings

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

        email = None
        full_name = None
        
        if provider.lower() == 'google':
            try:
                # Vérifier le token avec l'API Google
                # Note: On utilise settings.GOOGLE_CLIENT_ID
                idinfo = id_token.verify_oauth2_token(
                    social_token, 
                    google_requests.Request(), 
                    settings.GOOGLE_CLIENT_ID
                )
                
                # Vérifier l'émetteur
                if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                    return Response({"error": "Émetteur invalide"}, status=status.HTTP_400_BAD_REQUEST)
                
                email = idinfo.get('email')
                full_name = idinfo.get('name')
                
            except ValueError as e:
                # Token invalide
                if "Token used too early" in str(e) or "Token expired" in str(e):
                    # Cas particulier pour le développement ou latence réseau
                    pass
                else:
                    return Response({"error": f"Token Google invalide: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
                
                # Si on est en DEBUG, on peut éventuellement laisser passer pour tester
                if settings.DEBUG:
                    email = f"social_{provider}@example.com"
                    full_name = f"User {provider}"
                else:
                    return Response({"error": "Token Google invalide"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Pour les autres providers (Apple, FB), on simule encore
            # TODO: Implémenter la vérification réelle
            email = f"social_{provider}@example.com"
            full_name = f"User {provider}"

        if not email:
            return Response({"error": "Impossible de récupérer l'email"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Créer ou récupérer l'utilisateur
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': f"{provider.lower()}_{random.randint(1000,9999)}_{email.split('@')[0]}",
                'full_name': full_name or f"User {provider}",
                'is_verified': True,
                'email_verified': True,
                'role': 'user',
            }
        )

        # Générer les tokens JWT
        refresh = RefreshToken.for_user(user)
        
        from apps.notifications.services import NotificationService
        NotificationService.notify_security(user, 'login')
        
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
