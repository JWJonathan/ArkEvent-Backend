from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    RegisterView, 
    VerifyEmailView, 
    ResendOtpView,
    PasswordResetRequestView, 
    PasswordResetConfirmView,
    UserProfileView,
    SocialLoginView,
    WalletViewSet,
    AdminUserViewSet,
)

urlpatterns = [
    # Authentification
    path('auth/register/', RegisterView.as_view(), name='auth_register'),
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Profil utilisateur
    path('auth/me/', UserProfileView.as_view(), name='user_profile'),
    
    # Vérification email
    path('auth/verify-email/', VerifyEmailView.as_view(), name='verify_email'),
    path('auth/resend-otp/', ResendOtpView.as_view(), name='resend_otp'),
    
    # Réinitialisation mot de passe
    path('auth/password-reset/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('auth/password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    
    # Connexion sociale (optionnel - à implémenter)
    path('auth/social/<str:provider>/', SocialLoginView.as_view(), name='social_login'),
]

from rest_framework.routers import DefaultRouter
from .views import EmailVerificationTokenViewSet, PasswordResetTokenViewSet

router = DefaultRouter()
router.register(r'email-verification-tokens', EmailVerificationTokenViewSet, basename='email-tokens')
router.register(r'password-reset-tokens', PasswordResetTokenViewSet, basename='pwd-reset-tokens')
router.register(r'wallet', WalletViewSet, basename='wallet')
router.register(r'admin', AdminUserViewSet, basename='admin-users')


urlpatterns += router.urls
