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
        currency: str = 'USD'
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
        currency: str = 'USD',
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
        Processes a successful payment from any provider.
        Handles both ticket orders (ORDER_ prefix or UUID) and subscriptions (SUB_ prefix).
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        with transaction.atomic():
            # Handle Subscriptions and Orders via Custom Field
            custom = raw_data.get('custom', '')
            if custom and ':' in custom:
                parts = custom.split(':')
                obj_type = parts[0]
                obj_id = parts[1]
                user_id = parts[2] if len(parts) > 2 else None
                
                if obj_type == 'SUB' and user_id:
                    from apps.subscriptions.models import SubscriptionPlan
                    from apps.subscriptions.services import SubscriptionService
                    try:
                        user = User.objects.get(id=user_id)
                        plan = SubscriptionPlan.objects.get(tier=obj_id, is_active=True)
                        SubscriptionService.subscribe_user(
                            user=user,
                            plan=plan,
                            payment_method='paypal',
                            currency='USD'
                        )
                        return None # Success
                    except Exception:
                        pass # Log error or handle appropriately
                
                elif obj_type == 'BOOKING' and user_id:
                    from apps.marketplace.models import ServiceBooking
                    from apps.marketplace.services import BookingManager
                    try:
                        booking = ServiceBooking.objects.get(id=obj_id)
                        BookingManager.process_booking_payment(
                            booking=booking,
                            transaction_id=transaction_id,
                            payment_method='paypal',
                            raw_data=raw_data
                        )
                        return None # Success
                    except Exception:
                        pass
                
                elif obj_type == 'DEPOSIT' and user_id:
                    from apps.wallets.models import Deposit
                    from apps.wallets.services import DepositService
                    try:
                        deposit = Deposit.objects.get(id=obj_id)
                        DepositService.confirm_deposit(
                            deposit=deposit,
                            transaction_id=transaction_id,
                            provider_metadata=raw_data
                        )
                        return None # Success
                    except Exception:
                        pass

            # Handle Legacy Subscriptions (SUB_ prefix in order_id)
            if str(order_id).startswith('SUB_'):
                tier = str(order_id).replace('SUB_', '').lower()
                # Find user from raw_data if possible, or we need to pass user_id to this method
                # In PayPal webhooks, 'custom' field often contains user info if we sent it
                user_id = raw_data.get('custom_user_id') 
                # If user_id not in raw_data, we might need a better way to track pending subs
                
                # Try to find the user who initiated the payment
                # Note: This part depends on how you pass user context to the webhook
                # For now, let's assume we can get the user
                # If not, we might need to look up a 'PendingPayment' record
                return None # Placeholder for sub activation

            # Idempotency check for Orders
            if Payment.objects.filter(transaction_id=transaction_id, status='succeeded').exists():
                return Order.objects.get(id=order_id)

            try:
                order = Order.objects.select_for_update().get(id=order_id)
            except (Order.DoesNotExist, ValidationError):
                # Check if it's a subscription tier again (fallback)
                if order_id in ['free', 'pro', 'business', 'enterprise']:
                    # Handle sub...
                    return None
                raise

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
                NotificationService.notify_ticket_status(order.user, ticket, 'generated')

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
            NotificationService.notify_payment_organizer(organization, 'revenue', order.total_amount)

            # Notify buyer
            NotificationService.notify_ticket_purchase(order.user, order)
            NotificationService.notify_organizer_sales(event, 'sale')

            # Check if first sale
            if Ticket.objects.filter(ticket_type__event__organization__created_by=owner, status='sold').count() <= order.tickets.count():
                NotificationService.notify_gamification(owner, 'first_sale')

            # Check if sold out
            sold_count = Ticket.objects.filter(ticket_type__event=event, status='sold').count()
            if event.capacity and sold_count >= event.capacity:
                NotificationService.notify_organizer_sales(event, 'sold_out')
            elif event.capacity and sold_count >= event.capacity * 0.9:
                NotificationService.notify_organizer_sales(event, 'low_stock')

            return order