from django.db import transaction
from .models import Wallet, WalletTransaction

class WalletService:

    @staticmethod
    def get_balance(user):
        """Retourne le solde, crée le wallet s'il n'existe pas (comportement Flutter)."""
        wallet, created = Wallet.objects.get_or_create(
            user=user,
            defaults={'balance': 0.00, 'currency': 'USD'}
        )
        return float(wallet.balance)

    @staticmethod
    def _update_balance(user, amount, type_, description, order=None, status='completed'):
        """
        Mise à jour atomique : modifie le solde et crée une transaction.
        Retourne (success, wallet).
        """
        with transaction.atomic():
            wallet, _ = Wallet.objects.select_for_update().get_or_create(
                user=user, defaults={'balance': 0.00, 'currency': 'USD'}
            )
            new_balance = wallet.balance + amount
            if new_balance < 0:
                return False, wallet  # solde insuffisant

            wallet.balance = new_balance
            wallet.save(update_fields=['balance', 'updated_at'])

            WalletTransaction.objects.create(
                user=user,
                amount=amount,
                type=type_,
                status=status,
                description=description,
                order=order
            )
            return True, wallet

    @staticmethod
    def deposit(user, amount, description):
        return WalletService._update_balance(user, amount, 'deposit', description)

    @staticmethod
    def withdraw(user, amount, description):
        return WalletService._update_balance(user, -amount, 'withdrawal', description)

    @staticmethod
    def pay_with_wallet(user, order, amount):
        """Payer une commande avec le wallet. Retourne (success, wallet)."""
        return WalletService._update_balance(
            user,
            -amount,
            'payment',
            f'Paiement commande #{order.id}',
            order=order
        )

    @staticmethod
    def credit_wallet(user, amount, description, order=None):
        """Créditer le wallet (ex. vente de billets)."""
        return WalletService._update_balance(user, amount, 'credit', description, order=order)

    @staticmethod
    def refund(user, amount, description, order=None):
        """Remboursement."""
        return WalletService._update_balance(user, amount, 'refund', description, order=order)

    @staticmethod
    def get_transaction_history(user):
        return WalletTransaction.objects.filter(user=user).order_by('-created_at')