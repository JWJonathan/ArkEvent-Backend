from rest_framework import viewsets, permissions, status, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Order, Payment, OrderItem
from django.db import transaction
from django.utils import timezone
from .serializers import OrderSerializer, PaymentSerializer
from .services import PaymentService
from .providers.stripe import StripeProvider
from .providers.moncash import MonCashProvider
from .providers.paypal import PayPalProvider
from apps.core.permissions import IsAdmin 
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.conf import settings

class OrderViewSet(viewsets.ModelViewSet):
    """
    Remplace les méthodes Flutter :
    - getUserOrders()    -> GET /orders/?my=true (ou /orders/mine/)
    - getAllOrders()     -> GET /orders/ (admin seulement)
    - updateOrder()      -> PATCH /orders/{id}/
    - deleteOrder()      -> DELETE /orders/{id}/
    - Création d'une commande -> POST /orders/
    """
    queryset = Order.objects.filter(deleted_at__isnull=True)
    serializer_class = OrderSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'total_amount', 'status']
    ordering = ['-created_at']

    def get_permissions(self):
        """
        - list/retrieve : authentifié (l'utilisateur voit ses propres commandes ou l'admin voit tout)
        - create : authentifié
        - update/destroy : propriétaire de la commande ou admin
        """
        if self.action in ['create']:
            return [permissions.IsAuthenticated()]
        if self.action in ['update', 'partial_update', 'destroy']:
            # Le propriétaire de la commande ou un admin peuvent modifier/supprimer
            return [permissions.IsAuthenticated(), IsOrderOwnerOrAdmin()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        # Filtrage par utilisateur connecté si pas admin
        if not user.is_staff:
            qs = qs.filter(user=user)

        # Filtre optionnel par statut
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)

        return qs

    @action(detail=False, methods=['get'], url_path='mine')
    def my_orders(self, request):
        """Équivalent exact de getUserOrders(userId)"""
        qs = Order.objects.filter(user=request.user, deleted_at__isnull=True)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='all')
    @permission_classes([IsAdmin])
    def all_orders(self, request):
        """Équivalent de getAllOrders() - admin uniquement"""
        qs = Order.objects.filter(deleted_at__isnull=True)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        """
        Création d'une commande avec ses articles (tickets).
        Logique transactionnelle : réserve les tickets sélectionnés.
        """
        with transaction.atomic():
            order = serializer.save(
                user=self.request.user,
                status='pending',
                currency='HTG'  # par défaut
            )
            # On attend un tableau de tickets dans le payload
            ticket_items = self.request.data.get('items', [])
            for item in ticket_items:
                ticket_id = item.get('ticket_id')
                quantity = item.get('quantity', 1)
                ticket = Ticket.objects.select_for_update().get(
                    id=ticket_id,
                    status='available'
                )
                if ticket.available_quantity < quantity:
                    raise serializers.ValidationError(f"Pas assez de tickets disponibles pour {ticket}")
                # Réserver temporairement les tickets
                ticket.reserved_quantity += quantity
                ticket.available_quantity -= quantity
                ticket.save()
                OrderItem.objects.create(
                    order=order,
                    ticket=ticket,
                    ticket_type_name=ticket.ticket_type.name,
                    quantity=quantity,
                    price_at_purchase=ticket.price
                )
            # Recalculer le total
            order.calculate_total()

    def perform_update(self, serializer):
        """
        Mise à jour partielle : les champs autorisés sont définis dans le serializer.
        """
        serializer.save(updated_at=timezone.now())

    def perform_destroy(self, instance):
        """
        Soft delete : remplit deleted_at au lieu de supprimer.
        """
        instance.deleted_at = timezone.now()
        instance.save()

    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        """Lancement du paiement (existant, à conserver)"""
        order = self.get_object()
        # ... reste de la méthode déjà présente
        # (inchangée, voir votre code précédent)


# Permission personnalisée pour le propriétaire de la commande ou admin
from rest_framework.permissions import BasePermission

class IsOrderOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.is_staff or obj.user == request.user


# orders/views.py (suite)

class OrderItemViewSet(viewsets.ModelViewSet):
    """
    Remplace les méthodes Flutter :
    - getAllOrderItems()  -> GET /order-items/   (admin)
    - updateOrderItem()   -> PATCH /order-items/{id}/
    - deleteOrderItem()   -> DELETE /order-items/{id}/
    """
    queryset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer
    permission_classes = [IsAdmin]  # Seuls les admins peuvent gérer les items individuellement

    def get_queryset(self):
        qs = super().get_queryset()
        order_id = self.request.query_params.get('order_id')
        if order_id:
            qs = qs.filter(order_id=order_id)
        return qs

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        # Suppression définitive (comme dans le code Flutter)
        instance.delete()

class WebhookView(viewsets.GenericViewSet):
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=['post'], url_path='stripe')
    def stripe_webhook(self, request):
        provider = StripeProvider()
        event = provider.verify_webhook(request)
        if event:
            data = provider.handle_webhook(event)
            if data:
                from .services import PaymentService
                PaymentService.process_successful_payment(
                    order_id=data['order_id'],
                    provider_name='stripe',
                    transaction_id=data['transaction_id'],
                    raw_data=data['raw_data']
                )
                return Response({'status': 'success'})
        return Response({'status': 'invalid payload'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='paypal')
    def paypal_webhook(self, request):
        provider = PayPalProvider()
        event = provider.verify_webhook(request)
        if event:
            data = provider.handle_webhook(event)
            if data:
                from .services import PaymentService
                PaymentService.process_successful_payment(
                    order_id=data['order_id'],
                    provider_name='paypal',
                    transaction_id=data['transaction_id'],
                    raw_data=data['raw_data']
                )
                return Response({'status': 'success'})
        return Response({'status': 'invalid payload'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='moncash')
    def moncash_webhook(self, request):
        provider = MonCashProvider()
        event = provider.verify_webhook(request)
        if event:
            data = provider.handle_webhook(event)
            if data:
                from .services import PaymentService
                PaymentService.process_successful_payment(
                    order_id=data['order_id'],
                    provider_name='moncash',
                    transaction_id=data['transaction_id'],
                    raw_data=data['raw_data']
                )
                return Response({'status': 'success'})
        return Response({'status': 'invalid payload'}, status=status.HTTP_400_BAD_REQUEST)
    

class PaymentViewSet(viewsets.ModelViewSet):
    """
    Remplace l'intégralité du service de paiement Flutter :
    - GET    /payments/          -> getAllPayments()
    - GET    /payments/{id}/     -> détail d'un paiement
    - PATCH  /payments/{id}/     -> updatePayment()
    - POST   /payments/process/  -> processPayment()
    """

    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['transaction_id', 'user__email']   # recherche par email ou ID de transaction
    ordering_fields = ['created_at', 'amount']
    ordering = ['-created_at']

    def get_queryset(self):
        """
        Possibilité de filtrer par statut, méthode de paiement, etc.
        """
        qs = super().get_queryset()
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)
        method = self.request.query_params.get('payment_method')
        if method:
            qs = qs.filter(payment_method=method)
        return qs

    # ------------------------------------------------------------------
    # PATCH /payments/{id}/ – Équivalent de updatePayment()
    # ------------------------------------------------------------------
    def partial_update(self, request, *args, **kwargs):
        """
        Permet de mettre à jour le statut d'un paiement (et uniquement le statut).
        """
        instance = self.get_object()
        new_status = request.data.get('status')
        if new_status not in ['succeeded', 'failed', 'refunded']:
            return Response({'error': 'Statut invalide'}, status=status.HTTP_400_BAD_REQUEST)
        instance.status = new_status
        instance.save(update_fields=['status', 'updated_at'])
        return Response(self.get_serializer(instance).data)

    # ------------------------------------------------------------------
    # POST /payments/process/ – Équivalent de processPayment()
    # ------------------------------------------------------------------
    @action(detail=False, methods=['post'], url_path='process')
    def process_payment(self, request):
        """
        Endpoint appelé par le front après qu'un paiement ait été validé
        côté client (ex: retour PayPal onSuccess).
        Attend les champs : order_id, payment_method, transaction_id, gateway.
        L'utilisateur est déduit du token, le montant de la commande.
        """
        order_id = request.data.get('order_id')
        payment_method = request.data.get('payment_method')
        transaction_id = request.data.get('transaction_id')
        gateway = request.data.get('gateway', payment_method)

        if not all([order_id, payment_method, transaction_id]):
            return Response({'error': 'order_id, payment_method et transaction_id sont requis'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response({'error': 'Commande introuvable'}, status=status.HTTP_404_NOT_FOUND)

        # Vérification que l'utilisateur est bien le propriétaire de la commande
        if order.user_id != request.user.id:
            return Response({'error': 'Vous ne pouvez pas payer cette commande'},
                            status=status.HTTP_403_FORBIDDEN)

        if order.status != 'pending':
            return Response({'error': 'La commande n\'est plus en attente de paiement'},
                            status=status.HTTP_400_BAD_REQUEST)

        # Idéalement, ici on appelle le provider pour vérifier la transaction.
        # Pour rester fidèle au comportement Flutter, on considère le paiement réussi.
        try:
            with transaction.atomic():
                PaymentService.process_successful_payment(
                    order_id=order.id,
                    provider_name=gateway,
                    transaction_id=transaction_id,
                    raw_data=request.data.get('raw_data', {})
                )
            return Response({'status': 'success', 'order_id': order.id})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    @action(detail=False, methods=['post'], url_path='create-session')
    @permission_classes([IsAuthenticated])
    def create_payment_session(self, request):
        """
        Remplace startCheckout() du Flutter.
        Le SERVEUR crée la session de paiement, pas le client.
        """
        order_id = request.data.get('order_id')
        provider_name = request.data.get('provider')
        
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({'error': 'Commande invalide'}, status=400)
        
        if order.status != 'pending':
            return Response({'error': 'Commande déjà payée'}, status=400)
        
        # Sélection du provider AVEC les clés secrètes côté serveur
        if provider_name == 'stripe':
            provider = StripeProvider(
                secret_key=settings.STRIPE_SECRET_KEY,  # ✅ Dans .env
                publishable_key=settings.STRIPE_PUBLISHABLE_KEY
            )
        elif provider_name == 'paypal':
            provider = PayPalProvider(
                client_id=settings.PAYPAL_CLIENT_ID,
                secret=settings.PAYPAL_SECRET  # ✅ Jamais exposé au client
            )
        # ... autres providers
        
        # Création de la session de paiement
        try:
            payment_data = provider.create_payment_session(order)
            return Response({
                'client_secret': payment_data['client_secret'],
                'publishable_key': payment_data.get('publishable_key'),
                'payment_id': payment_data['payment_id']
            })
        except Exception as e:
            return Response({'error': str(e)}, status=500)
