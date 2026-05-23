from django.shortcuts import render
from rest_framework import viewsets, permissions, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Coupon, CouponUsage
from .serializers import CouponSerializer, CouponUsageSerializer
from apps.core.permissions import IsAdmin, IsOrganizer
from django.utils import timezone


class CouponViewSet(viewsets.ModelViewSet):
    queryset = Coupon.objects.filter(deleted_at__isnull=True).order_by('-created_at')
    serializer_class = CouponSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated()]  # Ajouter IsOrganizer si nécessaire
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_at=timezone.now())

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save()

    # Optionnel : endpoint pour valider un coupon
    @action(detail=False, methods=['post'], url_path='validate')
    def validate_coupon(self, request):
        code = request.data.get('code')
        order_amount = request.data.get('order_amount')
        ticket_type_ids = request.data.get('ticket_type_ids', [])
        try:
            coupon = Coupon.objects.get(code=code, deleted_at__isnull=True, is_active=True)
        except Coupon.DoesNotExist:
            return Response({'valid': False, 'message': 'Coupon invalide'}, status=status.HTTP_404_NOT_FOUND)

        # Vérifications de validité
        if not coupon.is_active:
            return Response({'valid': False, 'message': 'Coupon désactivé'})
        if coupon.valid_from and timezone.now() < coupon.valid_from:
            return Response({'valid': False, 'message': 'Coupon pas encore valide'})
        if coupon.valid_to and timezone.now() > coupon.valid_to:
            return Response({'valid': False, 'message': 'Coupon expiré'})
        if coupon.max_uses and coupon.usages.count() >= coupon.max_uses:
            return Response({'valid': False, 'message': 'Limite d\'utilisation atteinte'})
        if float(order_amount) < float(coupon.min_order_amount):
            return Response({'valid': False, 'message': f'Montant minimum de commande : {coupon.min_order_amount}'})

        # Vérifier les types de tickets applicables
        if coupon.applicable_ticket_types:
            # coupon.applicable_ticket_types est une liste d'UUID (str)
            if not set(ticket_type_ids) & set(coupon.applicable_ticket_types):
                return Response({'valid': False, 'message': 'Ce coupon ne s\'applique pas à ces types de billets'})

        # Calculer la réduction
        discount = 0.0
        if coupon.discount_type == 'percentage':
            discount = (float(order_amount) * float(coupon.discount_value)) / 100.0
        else:
            discount = float(coupon.discount_value)

        return Response({
            'valid': True,
            'discount': discount,
            'coupon_id': str(coupon.id)
        })


class CouponUsageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CouponUsage.objects.all().order_by('-used_at')
    serializer_class = CouponUsageSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]



from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import GiftCard, GiftCardTransaction, LoyaltyPoint, LoyaltyTransaction, Affiliate, AffiliateTransaction
from .serializers import (
    GiftCardSerializer, GiftCardTransactionSerializer,
    LoyaltyPointSerializer, LoyaltyTransactionSerializer,
    AffiliateSerializer, AffiliateTransactionSerializer
)
from apps.core.permissions import IsAdmin

# ───────── Gift Cards ─────────
class GiftCardViewSet(viewsets.ModelViewSet):
    queryset = GiftCard.objects.all().order_by('-created_at')
    serializer_class = GiftCardSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsAdmin()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        # On peut ajouter le purchaser automatiquement
        serializer.save(purchaser=self.request.user if not serializer.validated_data.get('purchaser') else None)

    def perform_update(self, serializer):
        serializer.save(updated_at=timezone.now())

    def perform_destroy(self, instance):
        # Hard delete (comme le Flutter)
        instance.delete()


class GiftCardTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GiftCardTransaction.objects.all().order_by('-created_at')
    serializer_class = GiftCardTransactionSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]


# ───────── Loyalty ─────────
class LoyaltyPointViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LoyaltyPoint.objects.all().order_by('-balance')
    serializer_class = LoyaltyPointSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @action(detail=True, methods=['post'], url_path='update-balance')
    def update_balance(self, request, pk=None):
        """Met à jour le solde (remplace updateLoyaltyBalance)."""
        point = self.get_object()
        new_balance = request.data.get('balance')
        if new_balance is None or int(new_balance) < 0:
            return Response({'error': 'balance doit être un entier positif'}, status=status.HTTP_400_BAD_REQUEST)
        point.balance = new_balance
        point.save(update_fields=['balance', 'updated_at'])
        return Response(self.get_serializer(point).data)


class LoyaltyTransactionViewSet(viewsets.ModelViewSet):
    queryset = LoyaltyTransaction.objects.all().order_by('-created_at')
    serializer_class = LoyaltyTransactionSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated(), IsAdmin()]  # admin seulement pour ajouter
        return [permissions.IsAuthenticated(), IsAdmin()]

    def perform_create(self, serializer):
        serializer.save()

    # Pas de update/destroy pour les transactions (lecture seule + création)


# ───────── Affiliates ─────────
class AffiliateViewSet(viewsets.ModelViewSet):
    queryset = Affiliate.objects.all().order_by('-created_at')
    serializer_class = AffiliateSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsAdmin()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save(updated_at=timezone.now())

    def perform_destroy(self, instance):
        instance.delete()


class AffiliateTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AffiliateTransaction.objects.all().order_by('-created_at')
    serializer_class = AffiliateTransactionSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]


from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
from .models import Wishlist, Review, ReviewLike, UserTag
from .serializers import WishlistSerializer, ReviewSerializer, ReviewLikeSerializer, UserTagSerializer
from apps.events.models import Event

# ───────── Wishlist ─────────
class WishlistViewSet(viewsets.ModelViewSet):
    serializer_class = WishlistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # L'utilisateur ne voit que sa propre wishlist
        return Wishlist.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    # POST /wishlist/add/ (alternative pour addToWishlist)
    @action(detail=False, methods=['post'], url_path='add')
    def add_to_wishlist(self, request):
        event_id = request.data.get('event_id')
        if not event_id:
            return Response({'error': 'event_id requis'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            event = Event.objects.get(id=event_id, deleted_at__isnull=True)
        except Event.DoesNotExist:
            return Response({'error': 'Événement introuvable'}, status=status.HTTP_404_NOT_FOUND)

        wishlist, created = Wishlist.objects.get_or_create(user=request.user, event=event)
        if not created:
            return Response({'detail': 'Déjà dans la wishlist'}, status=status.HTTP_200_OK)
        return Response(self.get_serializer(wishlist).data, status=status.HTTP_201_CREATED)

    # DELETE /wishlist/remove/ (alternative pour removeFromWishlist)
    @action(detail=False, methods=['delete'], url_path='remove')
    def remove_from_wishlist(self, request):
        event_id = request.data.get('event_id')
        if not event_id:
            return Response({'error': 'event_id requis'}, status=status.HTTP_400_BAD_REQUEST)
        deleted, _ = Wishlist.objects.filter(user=request.user, event_id=event_id).delete()
        if not deleted:
            return Response({'detail': 'Événement non trouvé dans la wishlist'}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # GET /wishlist/check/?event_id=... (remplace isInWishlist)
    @action(detail=False, methods=['get'], url_path='check')
    def check_wishlist(self, request):
        event_id = request.query_params.get('event_id')
        if not event_id:
            return Response({'error': 'event_id requis'}, status=status.HTTP_400_BAD_REQUEST)
        exists = Wishlist.objects.filter(user=request.user, event_id=event_id).exists()
        return Response({'in_wishlist': exists})

    # GET /wishlist/events/ (remplace getWishlistEvents)
    @action(detail=False, methods=['get'], url_path='events')
    def wishlist_events(self, request):
        wishlist_entries = Wishlist.objects.filter(user=request.user).select_related('event')
        events = [entry.event for entry in wishlist_entries if entry.event.deleted_at is None]
        from events.serializers import EventSerializer
        serializer = EventSerializer(events, many=True)
        return Response(serializer.data)


# ───────── Reviews ─────────
class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.filter(deleted_at__isnull=True).order_by('-created_at')
    serializer_class = ReviewSerializer

    def get_permissions(self):
        if self.action == 'list' or self.action == 'retrieve':
            return [permissions.AllowAny()]
        if self.action == 'like' or self.action == 'unlike':
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated()]
    
    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(is_visible=True)
        return qs

    def perform_create(self, serializer):
        # On vérifie que l'utilisateur n'a pas déjà laissé un avis
        event = serializer.validated_data['event']
        if Review.objects.filter(user=self.request.user, event=event, deleted_at__isnull=True).exists():
            raise serializers.ValidationError("Vous avez déjà donné votre avis pour cet événement.")
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        # Vérifie que l'utilisateur est l'auteur de l'avis
        instance = self.get_object()
        if instance.user != self.request.user and not self.request.user.is_staff:
            raise permissions.PermissionDenied("Vous ne pouvez modifier que vos propres avis.")
        serializer.save(updated_at=timezone.now())

    def perform_destroy(self, instance):
        # Soft delete
        if instance.user != self.request.user and not self.request.user.is_staff:
            raise permissions.PermissionDenied()
        instance.deleted_at = timezone.now()
        instance.save()

    @action(detail=True, methods=['post'], url_path='like')
    def like(self, request, pk=None):
        review = self.get_object()
        like, created = ReviewLike.objects.get_or_create(review=review, user=request.user)
        if created:
            review.likes_count += 1
            review.save(update_fields=['likes_count'])
            return Response({'status': 'liked'})
        return Response({'status': 'already_liked'})

    @action(detail=True, methods=['post'], url_path='unlike')
    def unlike(self, request, pk=None):
        review = self.get_object()
        deleted, _ = ReviewLike.objects.filter(review=review, user=request.user).delete()
        if deleted:
            review.likes_count = max(0, review.likes_count - 1)
            review.save(update_fields=['likes_count'])
            return Response({'status': 'unliked'})
        return Response({'status': 'not_liked'})


# ───────── User Tags ─────────
class UserTagViewSet(viewsets.ModelViewSet):
    queryset = UserTag.objects.all()
    serializer_class = UserTagSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return UserTag.objects.all()
        return UserTag.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)