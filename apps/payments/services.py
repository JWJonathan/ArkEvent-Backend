"""
Payment and Commission Services
Handles payment processing, commission calculations, and financial transactions.
"""

from decimal import Decimal
from typing import Dict, Optional
from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta

from .models import (
    Order, Payment, TicketSale, CommissionRule, Invoice, RefundRequest
)
from apps.wallets.models import Wallet, WalletTransaction, Deposit, Withdrawal, Payout
from apps.subscriptions.models import UserSubscription, SubscriptionPlan
from apps.tickets.models import Ticket
from apps.notifications.services import NotificationService


# ============================================================================
# COMMISSION SERVICE
# ============================================================================

class CommissionService:
    """
    Calculates commissions based on flexible rules.
    
    Commission Types:
    - percentage: % of ticket price
    - fixed: fixed amount per ticket
    - hybrid: percentage + fixed amount
    
    Deduction Models:
    - organizer: deducted from organizer revenue
    - customer: added to customer checkout
    """
    
    @staticmethod
    def get_commission_rule(subscription_tier: str = None) -> CommissionRule:
        """
        Retrieve active commission rule for subscription tier.
        Falls back to default rule if tier-specific not found.
        """
        # Try tier-specific rule
        if subscription_tier:
            rule = CommissionRule.objects.filter(
                subscription_tier=subscription_tier,
                is_active=True
            ).first()
            if rule:
                return rule
        
        # Fall back to default (subscription_tier=None)
        return CommissionRule.objects.filter(
            subscription_tier=None,
            is_active=True
        ).first()
    
    @staticmethod
    def calculate_commission(
        ticket_price: Decimal,
        quantity: int,
        subscription_tier: str = None,
        currency: str = 'HTG'
    ) -> Dict[str, any]:
        """
        Calculate commission for ticket purchase.
        
        Returns:
        {
            'subtotal': ticket_price * quantity,
            'commission_amount': commission to platform,
            'organizer_net_revenue': organizer receives,
            'platform_fee': added to customer (if applicable),
            'total_customer_pays': final amount customer pays
        }
        """
        rule = CommissionService.get_commission_rule(subscription_tier)
        
        subtotal = ticket_price * Decimal(quantity)
        commission_amount = Decimal('0')
        platform_fee = Decimal('0')
        
        # Calculate based on commission type
        if rule.commission_type == 'percentage':
            commission_amount = subtotal * (rule.percentage / Decimal('100'))
        
        elif rule.commission_type == 'fixed':
            commission_amount = rule.fixed_amount * Decimal(quantity)
        
        elif rule.commission_type == 'hybrid':
            percentage_part = subtotal * (rule.percentage / Decimal('100'))
            fixed_part = rule.fixed_amount * Decimal(quantity)
            commission_amount = percentage_part + fixed_part
        
        # Apply deduction model
        if rule.deduction_model == 'organizer':
            # Commission deducted from organizer revenue
            organizer_net_revenue = subtotal - commission_amount
            total_customer_pays = subtotal
        else:  # customer
            # Commission added to customer checkout
            platform_fee = commission_amount
            organizer_net_revenue = subtotal
            total_customer_pays = subtotal + platform_fee
        
        return {
            'subtotal': subtotal,
            'commission_amount': commission_amount,
            'organizer_net_revenue': organizer_net_revenue,
            'platform_fee': platform_fee,
            'total_customer_pays': total_customer_pays,
            'commission_rule_id': rule.id,
            'deduction_model': rule.deduction_model,
        }


# ============================================================================
# WALLET SERVICE
# ============================================================================

class WalletService:
    """
    Manages wallet operations: deposits, withdrawals, transactions.
    Maintains immutable transaction ledger for audit trail.
    """
    
    @staticmethod
    def get_or_create_wallet(user) -> Wallet:
        """Get or create wallet for user."""
        wallet, _ = Wallet.objects.get_or_create(user=user)
        return wallet
    
    @staticmethod
    def credit_wallet(
        wallet: Wallet,
        amount: Decimal,
        transaction_type: str,
        description: str = '',
        reference_id: str = '',
        related_ticket_sale = None
    ) -> WalletTransaction:
        """
        Credit wallet (add funds).
        Updates available balance and creates immutable transaction record.
        """
        if wallet.is_frozen:
            raise ValueError(f"Wallet is frozen. Reason: {wallet.freeze_reason}")
        
        wallet.available_balance += amount
        wallet.save(update_fields=['available_balance', 'updated_at'])
        
        # Create immutable transaction record
        transaction = WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type=transaction_type,
            amount=amount,
            currency=wallet.currency,
            balance_after=wallet.available_balance,
            description=description,
            reference_id=reference_id,
            related_ticket_sale=related_ticket_sale,
            status='completed',
            completed_at=timezone.now()
        )
        
        return transaction
    
    @staticmethod
    def debit_wallet(
        wallet: Wallet,
        amount: Decimal,
        transaction_type: str,
        description: str = '',
        reference_id: str = ''
    ) -> Optional[WalletTransaction]:
        """
        Debit wallet (remove funds).
        Validates sufficient balance before debit.
        """
        if wallet.is_frozen:
            raise ValueError(f"Wallet is frozen. Reason: {wallet.freeze_reason}")
        
        if wallet.available_balance < amount:
            raise ValueError(
                f"Insufficient balance. Available: {wallet.available_balance}, "
                f"Requested: {amount}"
            )
        
        wallet.available_balance -= amount
        wallet.save(update_fields=['available_balance', 'updated_at'])
        
        # Create immutable transaction record
        transaction = WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type=transaction_type,
            amount=amount,
            currency=wallet.currency,
            balance_after=wallet.available_balance,
            description=description,
            reference_id=reference_id,
            status='completed',
            completed_at=timezone.now()
        )
        
        return transaction
    
    @staticmethod
    def freeze_wallet(wallet: Wallet, reason: str):
        """Freeze wallet during disputes or investigations."""
        wallet.is_frozen = True
        wallet.freeze_reason = reason
        wallet.save(update_fields=['is_frozen', 'freeze_reason'])
    
    @staticmethod
    def unfreeze_wallet(wallet: Wallet):
        """Unfreeze wallet after resolution."""
        wallet.is_frozen = False
        wallet.freeze_reason = ''
        wallet.save(update_fields=['is_frozen', 'freeze_reason'])
    
    @staticmethod
    def get_transaction_history(wallet: Wallet, limit: int = 50):
        """Get paginated transaction history."""
        return wallet.transactions.all()[:limit]


# ============================================================================
# PAYMENT SERVICE
# ============================================================================

class PaymentService:
    """
    Orchestrates complete payment flows.
    Coordinates commission calculations, wallet credits, and transaction recording.
    """
    
    @staticmethod
    @transaction.atomic
    def process_ticket_purchase(
        event,
        buyer,
        ticket_quantity: int,
        ticket_price_per_unit: Decimal,
        currency: str = 'HTG',
        payment_method = None,
        transaction_id: str = None
    ) -> TicketSale:
        """
        Complete ticket purchase flow:
        1. Calculate commissions
        2. Split revenue between platform and organizer
        3. Credit organizer wallet
        4. Credit platform wallet
        5. Create transaction records
        6. Generate invoice
        
        ATOMIC transaction ensures all-or-nothing consistency.
        """
        
        # Get organizer subscription tier
        org_subscription = UserSubscription.objects.filter(
            user=event.organization.created_by,
            status='active'
        ).first()
        subscription_tier = org_subscription.plan.tier if org_subscription else 'free'
        
        # Calculate commission
        commission_data = CommissionService.calculate_commission(
            ticket_price_per_unit,
            ticket_quantity,
            subscription_tier,
            currency
        )
        
        # Create TicketSale record
        ticket_sale = TicketSale.objects.create(
            event=event,
            buyer=buyer,
            ticket_quantity=ticket_quantity,
            ticket_price_per_unit=ticket_price_per_unit,
            currency=currency,
            subtotal=commission_data['subtotal'],
            platform_fee=commission_data['platform_fee'],
            commission_amount=commission_data['commission_amount'],
            organizer_net_revenue=commission_data['organizer_net_revenue'],
            total_amount_paid=commission_data['total_customer_pays'],
            commission_rule_id=commission_data['commission_rule_id'],
            payment_status='completed',
            transaction_id=transaction_id,
        )
        
        # Credit organizer wallet
        organizer = event.organization.created_by
        organizer_wallet = WalletService.get_or_create_wallet(organizer)
        
        WalletService.credit_wallet(
            organizer_wallet,
            commission_data['organizer_net_revenue'],
            'ticket_sale',
            f"Ticket sale for {event.title}",
            str(ticket_sale.id),
            ticket_sale
        )
        
        # Credit platform wallet (system account)
        # TODO: Implement platform wallet concept
        
        # Generate invoice for buyer
        invoice_number = PaymentService.generate_invoice_number()
        Invoice.objects.create(
            invoice_number=invoice_number,
            invoice_type='sale',
            ticket_sale=ticket_sale,
            buyer=buyer,
            seller=event.organization,
            subtotal=ticket_sale.subtotal,
            total_amount=ticket_sale.total_amount_paid,
            currency=currency,
        )

        # Notify buyer
        NotificationService.notify_ticket_purchase(buyer, ticket_sale)
        
        return ticket_sale
    
    @staticmethod
    @transaction.atomic
    def process_refund(
        ticket_sale: TicketSale,
        refund_amount: Decimal,
        reason: str
    ) -> RefundRequest:
        """
        Process refund:
        1. Create refund request
        2. Reverse organizer wallet credit
        3. Reverse commission calculation
        4. Refund customer payment
        5. Create refund invoice
        
        ATOMIC transaction ensures consistency.
        """
        
        # Create refund request
        refund_request = RefundRequest.objects.create(
            ticket_sale=ticket_sale,
            requester=ticket_sale.buyer,
            refund_amount=refund_amount,
            refund_reason=reason,
            reason_description=reason,
            status='approved'  # Auto-approve (can be changed to 'pending')
        )
        
        # Reverse organizer credit
        organizer = ticket_sale.event.organization.created_by
        organizer_wallet = WalletService.get_or_create_wallet(organizer)
        
        WalletService.debit_wallet(
            organizer_wallet,
            refund_amount,
            'refund',
            f"Refund for ticket sale {ticket_sale.id}",
            str(refund_request.id)
        )
        
        # Update ticket sale status
        ticket_sale.payment_status = 'refunded'
        ticket_sale.save(update_fields=['payment_status', 'updated_at'])
        
        # Create refund invoice
        invoice_number = PaymentService.generate_invoice_number()
        Invoice.objects.create(
            invoice_number=invoice_number,
            invoice_type='refund',
            ticket_sale=ticket_sale,
            buyer=ticket_sale.buyer,
            seller=ticket_sale.event.organization,
            subtotal=-refund_amount,
            total_amount=-refund_amount,
            currency=ticket_sale.currency,
        )
        
        return refund_request
    
    @staticmethod
    def generate_invoice_number() -> str:
        """Generate unique invoice number."""
        from django.utils import timezone
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        latest = Invoice.objects.latest('created_at')
        sequence = int(latest.invoice_number.split('-')[-1]) + 1 if latest else 1
        return f"INV-{timestamp}-{sequence:06d}"
    
    @staticmethod
    def process_successful_payment(order_id, provider_name, transaction_id, raw_data):
        """
        Legacy payment processing (for backward compatibility).
        """
        with transaction.atomic():
            # Idempotency check
            if Payment.objects.filter(transaction_id=transaction_id, status='succeeded').exists():
                return Order.objects.get(id=order_id)

            order = Order.objects.select_for_update().get(id=order_id)
            if order.status == 'paid':
                return order

            # 1. Create payment record
            Payment.objects.create(
                order=order,
                user_id=order.user_id,
                amount=order.total_amount,
                currency=order.currency,
                transaction_id=transaction_id,
                status='succeeded',
                metadata={'provider': provider_name, 'raw_data': raw_data}
            )

            # 2. Update order status
            order.status = 'paid'
            order.save(update_fields=['status', 'updated_at'])

            # 3. Update related tickets
            tickets = Ticket.objects.filter(order=order, status='reserved')
            for ticket in tickets:
                ticket.status = 'sold'
                ticket.reserved_until = None
                ticket.save(update_fields=['status', 'reserved_until', 'updated_at'])

            # 4. Credit organizer wallet
            event = order.event
            organization = event.organization
            owner = organization.created_by

            organizer_wallet = WalletService.get_or_create_wallet(owner)
            WalletService.credit_wallet(
                organizer_wallet,
                order.total_amount,
                'ticket_sale',
                f'Ticket sale for event {event.id}',
                str(order.id)
            )

            # Notify buyer
            NotificationService.notify_ticket_purchase(order.user, order)

            return order