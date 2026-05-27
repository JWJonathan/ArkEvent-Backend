# ArkEvent Financial System - QUICK START GUIDE

## Prerequisites

- Python 3.9+
- PostgreSQL 12+
- Redis 6+
- Virtual environment activated

## Installation Steps

### 1. Install Dependencies

```bash
cd /home/jwj/ArkEvent-Backend

# Create/activate venv
python3 -m venv venv
source venv/bin/activate

# Install requirements (if not already done)
pip install -r requirements.txt

# Add new packages (if needed)
pip install django-filter djangorestframework
```

### 2. Create Migrations

```bash
# Generate migrations for new financial apps
python manage.py makemigrations payments wallets subscriptions finance

# Review migrations
python manage.py showmigrations

# Apply to database
python manage.py migrate

# Verify (should show all green checkmarks)
python manage.py showmigrations --list
```

### 3. Initialize Default Commission Rules

```bash
python manage.py shell

# Paste the following code:

from apps.payments.models import CommissionRule
from decimal import Decimal

# Create default commission rules for each tier
CommissionRule.objects.bulk_create([
    CommissionRule(
        name='FREE Tier - 10% Commission',
        commission_type='percentage',
        percentage=Decimal('10'),
        deduction_model='organizer',
        subscription_tier='free',
        is_active=True
    ),
    CommissionRule(
        name='PRO Tier - 5% Commission',
        commission_type='percentage',
        percentage=Decimal('5'),
        deduction_model='organizer',
        subscription_tier='pro',
        is_active=True
    ),
    CommissionRule(
        name='BUSINESS Tier - 2.5% Commission',
        commission_type='percentage',
        percentage=Decimal('2.5'),
        deduction_model='organizer',
        subscription_tier='business',
        is_active=True
    ),
])

print("✓ Commission rules created")
```

### 4. Initialize Subscription Plans

```bash
# Continue in shell:

from apps.subscriptions.models import SubscriptionPlan
from decimal import Decimal

plans = [
    SubscriptionPlan(
        tier='free',
        price_htg=Decimal('0'),
        price_usd=Decimal('0'),
        billing_cycle='monthly',
        max_active_events=2,
        max_tickets_per_event=100,
        commission_percentage=Decimal('10'),
        requires_branding=True,
        has_basic_analytics=True,
        priority_support_level='none',
        description='Perfect for testing and small events',
        is_active=True
    ),
    SubscriptionPlan(
        tier='pro',
        price_htg=Decimal('1000'),
        price_usd=Decimal('10'),
        billing_cycle='monthly',
        max_active_events=None,  # Unlimited
        max_tickets_per_event=None,  # Unlimited
        commission_percentage=Decimal('5'),
        requires_branding=False,
        has_qr_checkin=True,
        has_basic_analytics=True,
        has_advanced_analytics=True,
        has_custom_pages=True,
        has_marketing_tools=True,
        priority_support_level='priority',
        description='For growing organizers',
        is_active=True
    ),
    SubscriptionPlan(
        tier='business',
        price_htg=Decimal('5000'),
        price_usd=Decimal('50'),
        billing_cycle='monthly',
        max_active_events=None,  # Unlimited
        max_tickets_per_event=None,  # Unlimited
        commission_percentage=Decimal('2.5'),
        requires_branding=False,
        has_qr_checkin=True,
        has_basic_analytics=True,
        has_advanced_analytics=True,
        has_custom_pages=True,
        has_marketing_tools=True,
        has_multi_admin=True,
        has_api_access=True,
        has_custom_domain=True,
        has_white_label=True,
        has_sponsor_placement=True,
        priority_support_level='dedicated',
        description='Enterprise solution',
        is_active=True
    ),
]

SubscriptionPlan.objects.bulk_create(plans)
print("✓ Subscription plans created")
```

### 5. Initialize Premium Features

```bash
# Continue in shell:

from apps.subscriptions.models import PremiumFeature
from decimal import Decimal

features = [
    PremiumFeature(
        feature_type='event_boost',
        price_htg=Decimal('500'),
        price_usd=Decimal('5'),
        duration=7,
        duration_unit='days',
        description='Boost event visibility for 7 days - appears in trending section, search results, and recommendations',
        is_active=True
    ),
    PremiumFeature(
        feature_type='event_boost',
        price_htg=Decimal('1000'),
        price_usd=Decimal('10'),
        duration=30,
        duration_unit='days',
        description='Boost event visibility for 30 days - premium homepage placement and daily recommendation boost',
        is_active=True
    ),
    PremiumFeature(
        feature_type='custom_branding',
        price_htg=Decimal('2000'),
        price_usd=Decimal('20'),
        duration=30,
        duration_unit='days',
        description='Remove ArkEvent branding from your event pages - white-label experience',
        is_active=True
    ),
    PremiumFeature(
        feature_type='sponsored_ads',
        price_htg=Decimal('3000'),
        price_usd=Decimal('30'),
        duration=30,
        duration_unit='days',
        description='Get sponsored placement - push notifications, email features, and homepage banners',
        is_active=True
    ),
]

PremiumFeature.objects.bulk_create(features)
print("✓ Premium features created")

# Exit shell
exit()
```

### 6. Register URLs in Main App

Edit `arkevent_backend/urls.py`:

```python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Financial System APIs
    path('api/v1/payments/', include('apps.payments.urls')),
    path('api/v1/wallets/', include('apps.wallets.urls')),
    path('api/v1/subscriptions/', include('apps.subscriptions.urls')),
    path('api/v1/finance/', include('apps.finance.urls')),
    
    # Existing APIs
    path('api/v1/users/', include('apps.users.urls')),
    path('api/v1/events/', include('apps.events.urls')),
    path('api/v1/tickets/', include('apps.tickets.urls')),
    # ... other existing urls ...
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
```

### 7. Create Finance ViewSets and URLs

Create `apps/finance/viewsets.py`:

```python
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from .models import PlatformRevenue, RevenueReport, EventBoost, AnalyticsDailyMetric
from .serializers import (
    PlatformRevenueSerializer, RevenueReportSerializer,
    EventBoostSerializer, AnalyticsDailyMetricSerializer
)
from .services import PlatformRevenueService, OrganizerRevenueService, AnalyticsService


class PlatformRevenueViewSet(viewsets.ReadOnlyModelViewSet):
    """Platform-wide revenue statistics (admin only)."""
    queryset = PlatformRevenue.objects.all()
    serializer_class = PlatformRevenueSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['revenue_date', 'currency']
    ordering = ['-revenue_date']
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return PlatformRevenue.objects.all()
        return PlatformRevenue.objects.none()


class RevenueReportViewSet(viewsets.ReadOnlyModelViewSet):
    """Organizer revenue reports."""
    serializer_class = RevenueReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['organizer', 'period_type']
    ordering = ['-start_date']
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return RevenueReport.objects.all()
        # Organizers see only their reports
        return RevenueReport.objects.filter(organizer__created_by=user)


class EventBoostViewSet(viewsets.ReadOnlyModelViewSet):
    """Event boost history and analytics."""
    serializer_class = EventBoostSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['event', 'is_active']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return EventBoost.objects.all()
        # Users see only their event boosts
        return EventBoost.objects.filter(event__organization__created_by=user)


class AnalyticsDailyMetricViewSet(viewsets.ReadOnlyModelViewSet):
    """Event analytics metrics."""
    serializer_class = AnalyticsDailyMetricSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['event', 'metric_date']
    ordering = ['-metric_date']
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return AnalyticsDailyMetric.objects.all()
        # Users see only their event metrics
        from apps.events.models import Event
        events = Event.objects.filter(organization__created_by=user)
        return AnalyticsDailyMetric.objects.filter(event__in=events)
```

Create `apps/finance/urls.py`:

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewsets import (
    PlatformRevenueViewSet, RevenueReportViewSet,
    EventBoostViewSet, AnalyticsDailyMetricViewSet
)

router = DefaultRouter()
router.register(r'platform-revenue', PlatformRevenueViewSet, basename='platform-revenue')
router.register(r'revenue-reports', RevenueReportViewSet, basename='revenue-reports')
router.register(r'event-boosts', EventBoostViewSet, basename='event-boosts')
router.register(r'analytics-metrics', AnalyticsDailyMetricViewSet, basename='analytics-metrics')

urlpatterns = [
    path('', include(router.urls)),
]
```

### 8. Test the APIs

```bash
# Start development server
python manage.py runserver

# Test endpoints with curl or Postman

# Get subscription plans
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/subscriptions/plans/

# Get commission rules
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/payments/commission-rules/

# Get wallet info
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/wallets/wallets/my-wallet/

# Create deposit
curl -X POST \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"amount":"500","currency":"HTG","deposit_method":"moncash"}' \
  http://localhost:8000/api/v1/wallets/deposits/create-deposit/

# Purchase premium feature
curl -X POST \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"feature_id":"<uuid>","event_id":"<uuid>","currency":"HTG"}' \
  http://localhost:8000/api/v1/subscriptions/user-premium-features/purchase/
```

### 9. Integrate with Payment Providers (Optional)

Add provider-specific integrations in `apps/payments/providers/`:

```python
# apps/payments/providers/moncash.py
import requests
from django.conf import settings

class MonCashProvider:
    def __init__(self):
        self.api_key = settings.MONCASH_API_KEY
        self.api_url = "https://sandbox.moncashbutton.com/api"  # or production
    
    def process_payment(self, amount, phone_number):
        payload = {
            'amount': amount,
            'phone': phone_number,
            'description': 'ArkEvent Ticket Purchase'
        }
        response = requests.post(
            f"{self.api_url}/transaction",
            headers={'Authorization': f'Bearer {self.api_key}'},
            json=payload
        )
        return response.json()

# apps/payments/providers/__init__.py
from .moncash import MonCashProvider
# ... import other providers ...

PAYMENT_PROVIDERS = {
    'moncash': MonCashProvider(),
    'natcash': NatCashProvider(),
    # ...
}
```

## Troubleshooting

### Issue: Migration fails with "duplicate key value"

```bash
# Reset specific app tables (development only!)
python manage.py migrate payments zero
python manage.py migrate payments
```

### Issue: Permission denied on wallet operations

Ensure user has proper permissions:
```python
from apps.wallets.models import Wallet
wallet = Wallet.objects.get(user=request.user)
# Verify wallet.is_frozen is False
```

### Issue: Commission calculation incorrect

Verify commission rule is set correctly:
```python
from apps.payments.models import CommissionRule
rule = CommissionRule.objects.filter(is_active=True).first()
print(f"Type: {rule.commission_type}, Amount: {rule.percentage or rule.fixed_amount}")
```

## Next Steps

1. **Celery Tasks**: Set up async tasks for invoices, payouts, reports
2. **WebSockets**: Implement real-time balance updates with Django Channels
3. **Flutter App**: Implement Dio API clients and UI screens
4. **Payment Webhooks**: Handle provider callbacks for payment confirmation
5. **Analytics Dashboard**: Build admin dashboard for revenue tracking
6. **Compliance**: Add audit logging and compliance reports for regulations

---

For detailed documentation, see: `FINANCIAL_SYSTEM_GUIDE.md`
