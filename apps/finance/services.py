"""
Finance Service Layer
Handles analytics, reporting, and financial metrics.
"""

from decimal import Decimal
from datetime import datetime, timedelta, date
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone

from .models import PlatformRevenue, RevenueReport, AnalyticsDailyMetric
from apps.payments.models import TicketSale, CommissionRule
from apps.subscriptions.models import UserSubscription
from apps.wallets.models import WalletTransaction


class PlatformRevenueService:
    """Tracks and reports platform-wide revenue."""
    
    @staticmethod
    def get_daily_revenue(date_obj: date, currency: str = 'USD') -> PlatformRevenue or None:
        """Get daily revenue for specific date."""
        return PlatformRevenue.objects.filter(
            revenue_date=date_obj,
            currency=currency
        ).first()
    
    @staticmethod
    def calculate_daily_revenue(date_obj: date, currency: str = 'USD') -> PlatformRevenue:
        """
        Calculate and save daily revenue metrics.
        Aggregates from all transactions for the day.
        """
        start = timezone.make_aware(timezone.datetime.combine(date_obj, timezone.time.min))
        end = timezone.make_aware(timezone.datetime.combine(date_obj, timezone.time.max))
        
        # Ticket commission revenue
        ticket_sales = TicketSale.objects.filter(
            created_at__range=[start, end],
            currency=currency,
            payment_status='completed'
        )
        
        ticket_commission = ticket_sales.aggregate(
            total=Sum('commission_amount')
        )['total'] or Decimal('0')
        
        ticket_count = ticket_sales.count()
        
        # Subscription revenue
        subscriptions = UserSubscription.objects.filter(
            start_date=date_obj,
            currency=currency
        )
        
        subscription_revenue = subscriptions.aggregate(
            total=Sum('amount_paid')
        )['total'] or Decimal('0')
        
        new_subscriptions = subscriptions.count()
        
        # Premium feature revenue
        premium_features = UserSubscription.objects.filter(
            created_at__range=[start, end],
            currency=currency
        )
        
        premium_revenue = premium_features.aggregate(
            total=Sum('amount_paid')
        )['total'] or Decimal('0')
        
        premium_count = premium_features.count()
        
        # Total revenue
        total_revenue = ticket_commission + subscription_revenue + premium_revenue
        
        # Get or create daily revenue
        month_start = date_obj.replace(day=1)
        revenue, _ = PlatformRevenue.objects.get_or_create(
            revenue_date=date_obj,
            revenue_month=month_start,
            currency=currency,
            defaults={
                'ticket_commission_revenue': ticket_commission,
                'subscription_revenue': subscription_revenue,
                'premium_feature_revenue': premium_revenue,
                'total_revenue': total_revenue,
                'ticket_sales_count': ticket_count,
                'new_subscriptions_count': new_subscriptions,
                'premium_features_purchased_count': premium_count,
            }
        )
        
        return revenue
    
    @staticmethod
    def get_monthly_revenue(year: int, month: int, currency: str = 'USD') -> Dict:
        """Get aggregated monthly revenue."""
        from calendar import monthrange
        
        days_in_month = monthrange(year, month)[1]
        month_start = date(year, month, 1)
        month_end = date(year, month, days_in_month)
        
        revenues = PlatformRevenue.objects.filter(
            revenue_date__range=[month_start, month_end],
            currency=currency
        )
        
        totals = revenues.aggregate(
            total_commission=Sum('ticket_commission_revenue'),
            total_subscriptions=Sum('subscription_revenue'),
            total_premium=Sum('premium_feature_revenue'),
            total_revenue=Sum('total_revenue'),
            total_sales=Sum('ticket_sales_count'),
            total_subscriptions_new=Sum('new_subscriptions_count'),
        )
        
        return {
            'period': f"{year}-{month:02d}",
            'ticket_commission': totals['total_commission'] or Decimal('0'),
            'subscription': totals['total_subscriptions'] or Decimal('0'),
            'premium_features': totals['total_premium'] or Decimal('0'),
            'total': totals['total_revenue'] or Decimal('0'),
            'ticket_sales_count': totals['total_sales'] or 0,
            'new_subscriptions': totals['total_subscriptions_new'] or 0,
            'currency': currency,
        }


class OrganizerRevenueService:
    """Tracks organizer-specific revenue."""
    
    @staticmethod
    def calculate_organizer_revenue(organization, start_date: date, end_date: date) -> RevenueReport:
        """
        Calculate revenue report for organizer.
        Aggregates ticket sales for their events.
        """
        from django.utils import timezone
        
        # Convert dates to datetimes
        start_dt = timezone.make_aware(timezone.datetime.combine(start_date, timezone.time.min))
        end_dt = timezone.make_aware(timezone.datetime.combine(end_date, timezone.time.max))
        
        # Get all events for organization
        events = organization.events.all()
        
        # Get ticket sales for period
        ticket_sales = TicketSale.objects.filter(
            event__in=events,
            created_at__range=[start_dt, end_dt],
            payment_status__in=['completed', 'partial_refund']
        )
        
        # Calculate metrics
        gross_revenue = ticket_sales.aggregate(
            total=Sum('subtotal')
        )['total'] or Decimal('0')
        
        commissions = ticket_sales.aggregate(
            total=Sum('commission_amount')
        )['total'] or Decimal('0')
        
        refunds = TicketSale.objects.filter(
            event__in=events,
            created_at__range=[start_dt, end_dt],
            payment_status='refunded'
        )
        
        refund_amount = refunds.aggregate(
            total=Sum('total_amount_paid')
        )['total'] or Decimal('0')
        
        # Calculate period type
        days_diff = (end_date - start_date).days
        if days_diff == 0:
            period_type = 'daily'
        elif days_diff <= 7:
            period_type = 'weekly'
        else:
            period_type = 'monthly'
        
        # Get top event
        top_event = ticket_sales.values('event').annotate(
            count=Count('id')
        ).order_by('-count').first()
        top_event_id = top_event['event'] if top_event else None
        
        # Create report
        report = RevenueReport.objects.create(
            organizer=organization,
            period_type=period_type,
            start_date=start_date,
            end_date=end_date,
            gross_revenue=gross_revenue,
            total_commissions=commissions,
            net_revenue=gross_revenue - commissions - refund_amount,
            currency='USD',
            total_ticket_sales=ticket_sales.count(),
            total_tickets_sold=ticket_sales.aggregate(
                total=Sum('ticket_quantity')
            )['total'] or 0,
            average_ticket_price=gross_revenue / ticket_sales.aggregate(
                total=Sum('ticket_quantity')
            )['total'] if ticket_sales.aggregate(total=Sum('ticket_quantity'))['total'] else 0,
            events_count=events.count(),
            top_event_id=top_event_id,
            refunds_count=refunds.count(),
            refunds_amount=refund_amount,
        )
        
        return report
    
    @staticmethod
    def get_organizer_commission_percentage(organization) -> Decimal:
        """Get applicable commission percentage for organizer."""
        subscription = organization.created_by.subscription
        
        if subscription and subscription.status == 'active':
            return Decimal(subscription.plan.commission_percentage)
        else:
            # Free tier default
            free_plan = SubscriptionPlan.objects.get(tier='free')
            return Decimal(free_plan.commission_percentage)


class AnalyticsService:
    """Event and ticket analytics."""
    
    @staticmethod
    def record_daily_analytics(event, date_obj: date = None):
        """
        Record daily analytics for event.
        Aggregates views, sales, and revenue.
        """
        if not date_obj:
            date_obj = timezone.now().date()
        
        start = timezone.make_aware(timezone.datetime.combine(date_obj, timezone.time.min))
        end = timezone.make_aware(timezone.datetime.combine(date_obj, timezone.time.max))
        
        # Get ticket sales for event on date
        sales = TicketSale.objects.filter(
            event=event,
            created_at__range=[start, end],
            payment_status='completed'
        )
        
        revenue = sales.aggregate(
            total=Sum('organizer_net_revenue')
        )['total'] or Decimal('0')
        
        # Get refunds
        refunds = TicketSale.objects.filter(
            event=event,
            created_at__range=[start, end],
            payment_status='refunded'
        )
        
        refund_amount = refunds.aggregate(
            total=Sum('total_amount_paid')
        )['total'] or Decimal('0')
        
        # Create or update daily metric
        metric, _ = AnalyticsDailyMetric.objects.get_or_create(
            event=event,
            metric_date=date_obj,
            defaults={
                'tickets_sold': sales.aggregate(total=Sum('ticket_quantity'))['total'] or 0,
                'revenue': revenue,
                'refunds': refunds.count(),
                'refund_amount': refund_amount,
            }
        )
        
        return metric
    
    @staticmethod
    def get_event_analytics(event, days: int = 30) -> Dict:
        """Get analytics summary for event."""
        from datetime import timedelta
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        metrics = AnalyticsDailyMetric.objects.filter(
            event=event,
            metric_date__range=[start_date, end_date]
        )
        
        totals = metrics.aggregate(
            total_views=Sum('page_views'),
            total_visitors=Sum('unique_visitors'),
            total_tickets=Sum('tickets_sold'),
            total_revenue=Sum('revenue'),
            total_refunds=Sum('refunds'),
            total_refund_amount=Sum('refund_amount'),
        )
        
        return {
            'event': event.title,
            'period_days': days,
            'page_views': totals['total_views'] or 0,
            'unique_visitors': totals['total_visitors'] or 0,
            'tickets_sold': totals['total_tickets'] or 0,
            'revenue': totals['total_revenue'] or Decimal('0'),
            'refunds': totals['total_refunds'] or 0,
            'refund_amount': totals['total_refund_amount'] or Decimal('0'),
        }
    
    @staticmethod
    def get_platform_statistics(days: int = 30) -> Dict:
        """Get platform-wide statistics."""
        from datetime import timedelta
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Ticket sales
        sales = TicketSale.objects.filter(
            created_at__gte=timezone.make_aware(
                timezone.datetime.combine(start_date, timezone.time.min)
            ),
            payment_status='completed'
        )
        
        # Events
        from apps.events.models import Event
        active_events = Event.objects.filter(
            created_at__gte=timezone.make_aware(
                timezone.datetime.combine(start_date, timezone.time.min)
            ),
            is_published=True
        )
        
        # Organizers
        from apps.organization.models import Organization
        active_orgs = Organization.objects.filter(
            created_at__gte=timezone.make_aware(
                timezone.datetime.combine(start_date, timezone.time.min)
            )
        ).distinct()
        
        total_revenue = sales.aggregate(total=Sum('commission_amount'))['total'] or Decimal('0')
        
        return {
            'period_days': days,
            'total_ticket_sales': sales.count(),
            'total_tickets_sold': sales.aggregate(total=Sum('ticket_quantity'))['total'] or 0,
            'active_events': active_events.count(),
            'active_organizers': active_orgs.count(),
            'platform_revenue': total_revenue,
            'currency': 'USD',
        }
