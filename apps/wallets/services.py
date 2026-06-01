"""
Wallet Service Layer
Handles wallet operations, deposits, withdrawals, and transaction management.
"""

from decimal import Decimal
from typing import Optional, Dict, List
from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta

from .models import Wallet, WalletTransaction, Deposit, Withdrawal, Payout


class DepositService:
    """Manages deposit operations into user wallets."""
    
    @staticmethod
    def create_deposit(
        wallet: Wallet,
        amount: Decimal,
        currency: str,
        deposit_method: str,
        payment_method = None
    ) -> Deposit:
        """
        Create a pending deposit.
        Deposit is marked as 'pending' until payment provider confirms.
        """
        deposit = Deposit.objects.create(
            wallet=wallet,
            amount=amount,
            currency=currency,
            deposit_method=deposit_method,
            payment_method=payment_method,
            status='pending'
        )
        return deposit
    
    @staticmethod
    @transaction.atomic
    def confirm_deposit(
        deposit: Deposit,
        transaction_id: str,
        provider_metadata: Dict = None
    ) -> WalletTransaction:
        """
        Confirm deposit and credit wallet.
        Called after payment provider confirms successful payment.
        """
        if deposit.status != 'pending':
            raise ValueError(f"Cannot confirm deposit with status {deposit.status}")
        
        # Update deposit status
        deposit.status = 'completed'
        deposit.transaction_id = transaction_id
        deposit.completed_at = timezone.now()
        deposit.save(update_fields=['status', 'transaction_id', 'completed_at', 'metadata'])
        
        # Credit wallet
        wallet = deposit.wallet
        wallet.available_balance += deposit.amount
        wallet.save(update_fields=['available_balance', 'updated_at'])
        
        # Create wallet transaction
        wallet_transaction = WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type='deposit',
            amount=deposit.amount,
            currency=deposit.currency,
            balance_after=wallet.available_balance,
            description=f"Deposit via {deposit.get_deposit_method_display()}",
            reference_id=str(deposit.id),
            status='completed',
            completed_at=timezone.now()
        )
        
        return wallet_transaction
    
    @staticmethod
    @transaction.atomic
    def cancel_deposit(deposit: Deposit, reason: str = ''):
        """Cancel a pending deposit."""
        if deposit.status not in ['pending', 'processing']:
            raise ValueError(f"Cannot cancel deposit with status {deposit.status}")
        
        deposit.status = 'cancelled'
        deposit.save(update_fields=['status', 'updated_at'])


class WithdrawalService:
    """Manages withdrawal operations from user wallets."""
    
    WITHDRAWAL_FEE_INSTANT_HTG = Decimal('100')  # 100 HTG for instant withdrawal
    
    @staticmethod
    @transaction.atomic
    def create_withdrawal(
        wallet: Wallet,
        amount: Decimal,
        destination_provider: str,
        destination_identifier: str,
        withdrawal_speed: str = 'standard'
    ) -> Withdrawal:
        """
        Create a withdrawal request.
        Deducts from available balance and creates pending withdrawal.
        """
        # Validate sufficient balance
        if wallet.available_balance < amount:
            raise ValueError(
                f"Insufficient balance. Available: {wallet.available_balance}, "
                f"Requested: {amount}"
            )
        
        # Calculate fee
        fee_amount = Decimal('0')
        if withdrawal_speed == 'instant':
            fee_amount = WithdrawalService.WITHDRAWAL_FEE_INSTANT_HTG
        
        # Check balance after fee
        total_deduct = amount + fee_amount
        if wallet.available_balance < total_deduct:
            raise ValueError(
                f"Insufficient balance including fee. Available: {wallet.available_balance}, "
                f"Total needed: {total_deduct}"
            )
        
        # Deduct from wallet (pending)
        wallet.pending_balance += total_deduct
        wallet.available_balance -= total_deduct
        wallet.save(update_fields=['pending_balance', 'available_balance', 'updated_at'])
        
        # Create withdrawal record
        withdrawal = Withdrawal.objects.create(
            wallet=wallet,
            requested_amount=amount,
            currency=wallet.currency,
            fee_amount=fee_amount,
            net_amount=amount - fee_amount,
            withdrawal_speed=withdrawal_speed,
            status='pending',
            destination_provider=destination_provider,
            destination_identifier=destination_identifier,
            requested_by=wallet.user
        )
        
        return withdrawal
    
    @staticmethod
    @transaction.atomic
    def approve_withdrawal(withdrawal: Withdrawal, transaction_id: str = None) -> WalletTransaction:
        """
        Approve and process withdrawal.
        Moves funds from pending to completion.
        """
        from apps.notifications.services import NotificationService
        if withdrawal.status != 'pending':
            raise ValueError(f"Cannot approve withdrawal with status {withdrawal.status}")
        
        wallet = withdrawal.wallet
        total_amount = withdrawal.requested_amount + withdrawal.fee_amount
        
        # Update withdrawal
        withdrawal.status = 'completed'
        withdrawal.transaction_id = transaction_id
        withdrawal.completed_at = timezone.now()
        withdrawal.save(update_fields=['status', 'transaction_id', 'completed_at'])
        
        # Update wallet (remove from pending)
        wallet.pending_balance -= total_amount
        wallet.save(update_fields=['pending_balance', 'updated_at'])
        
        # Create wallet transaction
        wallet_transaction = WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type='withdrawal',
            amount=withdrawal.net_amount,
            currency=wallet.currency,
            balance_after=wallet.available_balance,
            description=f"Withdrawal to {withdrawal.destination_provider}",
            reference_id=str(withdrawal.id),
            status='completed',
            completed_at=timezone.now()
        )
        
        # Notify user (if they are part of an organization, it might be an organizer notification)
        # For simplicity, notify the wallet owner
        NotificationService.notify_payment_user(wallet.user, 'withdrawal_approved', withdrawal.net_amount, withdrawal.currency)
        
        return wallet_transaction
    
    @staticmethod
    @transaction.atomic
    def reject_withdrawal(withdrawal: Withdrawal, rejection_reason: str = ''):
        """
        Reject withdrawal and refund to available balance.
        """
        from apps.notifications.services import NotificationService
        if withdrawal.status != 'pending':
            raise ValueError(f"Cannot reject withdrawal with status {withdrawal.status}")
        
        wallet = withdrawal.wallet
        total_amount = withdrawal.requested_amount + withdrawal.fee_amount
        
        # Return to available balance
        wallet.pending_balance -= total_amount
        wallet.available_balance += total_amount
        wallet.save(update_fields=['pending_balance', 'available_balance', 'updated_at'])
        
        # Update withdrawal
        withdrawal.status = 'rejected'
        withdrawal.rejection_reason = rejection_reason
        withdrawal.completed_at = timezone.now()
        withdrawal.save(update_fields=['status', 'rejection_reason', 'completed_at'])
        
        NotificationService.notify_payment_user(wallet.user, 'withdrawal_refused', withdrawal.requested_amount, withdrawal.currency)


class PayoutService:
    """Manages automatic payouts to organizers."""
    
    @staticmethod
    def schedule_payout(
        wallet: Wallet,
        amount: Decimal,
        payout_period_start,
        payout_period_end,
        destination_provider: str,
        destination_identifier: str,
        included_ticket_sales_count: int = 0,
        included_revenue: Decimal = Decimal('0')
    ) -> Payout:
        """
        Schedule a payout (typically auto-generated by system).
        """
        payout = Payout.objects.create(
            wallet=wallet,
            amount=amount,
            currency=wallet.currency,
            status='scheduled',
            payout_period_start=payout_period_start,
            payout_period_end=payout_period_end,
            destination_provider=destination_provider,
            destination_identifier=destination_identifier,
            included_ticket_sales_count=included_ticket_sales_count,
            included_revenue=included_revenue
        )
        return payout
    
    @staticmethod
    @transaction.atomic
    def execute_payout(payout: Payout, transaction_id: str = None) -> WalletTransaction:
        """
        Execute a scheduled payout.
        """
        if payout.status not in ['scheduled', 'pending']:
            raise ValueError(f"Cannot execute payout with status {payout.status}")
        
        wallet = payout.wallet
        
        # Deduct from wallet
        if wallet.available_balance < payout.amount:
            raise ValueError("Insufficient balance for payout")
        
        wallet.available_balance -= payout.amount
        wallet.save(update_fields=['available_balance', 'updated_at'])
        
        # Update payout
        payout.status = 'completed'
        payout.transaction_id = transaction_id
        payout.completed_at = timezone.now()
        payout.save(update_fields=['status', 'transaction_id', 'completed_at'])
        
        # Create wallet transaction
        wallet_transaction = WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type='payout',
            amount=payout.amount,
            currency=wallet.currency,
            balance_after=wallet.available_balance,
            description=f"Payout for period {payout.payout_period_start} to {payout.payout_period_end}",
            reference_id=str(payout.id),
            status='completed',
            completed_at=timezone.now()
        )
        
        return wallet_transaction


class WalletAnalyticsService:
    """Analytics for wallet operations."""
    
    @staticmethod
    def get_wallet_summary(wallet: Wallet) -> Dict:
        """Get complete wallet summary."""
        return {
            'available_balance': wallet.available_balance,
            'pending_balance': wallet.pending_balance,
            'total_balance': wallet.total_balance,
            'currency': wallet.currency,
            'is_frozen': wallet.is_frozen,
            'transaction_count': wallet.transactions.count(),
            'last_transaction': wallet.transactions.first(),
        }
    
    @staticmethod
    def get_transaction_statistics(wallet: Wallet, days: int = 30) -> Dict:
        """Get transaction statistics for period."""
        from django.utils import timezone
        from datetime import timedelta
        
        start_date = timezone.now() - timedelta(days=days)
        transactions = wallet.transactions.filter(created_at__gte=start_date)
        
        totals = {
            'deposits': Decimal('0'),
            'withdrawals': Decimal('0'),
            'ticket_sales': Decimal('0'),
            'refunds': Decimal('0'),
        }
        
        for txn in transactions:
            if txn.transaction_type in totals:
                totals[txn.transaction_type] += txn.amount
        
        return totals
