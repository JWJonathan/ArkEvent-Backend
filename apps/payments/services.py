# payments/services.py
from django.db import transaction
from django.utils import timezone
from .models import Order, Payment
from apps.tickets.models import Ticket
from apps.users.models import Wallet, WalletTransaction


class PaymentService:
    @staticmethod
    def process_successful_payment(order_id, provider_name, transaction_id, raw_data):
        """
        Exécute la même logique que le `processPayment` Flutter :
        1. Insère un paiement (status = 'succeeded')
        2. Passe la commande à 'paid'
        3. Passe les tickets de 'reserved' à 'sold' (ou 'confirmed' selon votre modèle)
        4. Crédite le portefeuille de l'organisateur
        5. Enregistre l'opération dans wallet_transactions
        Le tout dans une transaction atomique.
        """
        with transaction.atomic():
            # Idempotency check
            if Payment.objects.filter(transaction_id=transaction_id, status='succeeded').exists():
                return Order.objects.get(id=order_id)

            order = Order.objects.select_for_update().get(id=order_id)
            if order.status == 'paid':
                return order

            # 1. Création du paiement
            Payment.objects.create(
                order=order,
                user_id=order.user_id,
                amount=order.total_amount,
                currency=order.currency,
                payment_method=provider_name,   # ex: 'paypal', 'stripe'
                transaction_id=transaction_id,
                status='succeeded',
                gateway=provider_name,          # cohérent avec le modèle Dart
                metadata={
                    'provider': provider_name,
                    'raw_data': raw_data
                }
            )

            # 2. Mise à jour de la commande
            order.status = 'paid'
            order.save(update_fields=['status', 'updated_at'])

            # 3. Mise à jour des tickets liés
            tickets = Ticket.objects.filter(order=order, status='reserved')
            for ticket in tickets:
                ticket.status = 'sold'          # ou 'confirmed' selon votre modèle
                ticket.reserved_until = None
                ticket.save(update_fields=['status', 'reserved_until', 'updated_at'])

            # 4. Crédit du portefeuille de l'organisateur
            # On trouve l'organisateur via order.event.organization.created_by
            event = order.event
            organization = event.organization
            owner_id = organization.created_by_id

            wallet, _ = Wallet.objects.get_or_create(user_id=owner_id)
            wallet.balance += order.total_amount
            wallet.save(update_fields=['balance', 'updated_at'])

            # 5. Transaction wallet
            WalletTransaction.objects.create(
                user_id=owner_id,
                amount=order.total_amount,
                type='credit',
                description=f'Vente billet commande #{order.id}',
                order_id=order.id
            )

            return order