# ArkEvent Financial System - COMPLETE IMPLEMENTATION GUIDE

## 📋 TABLE OF CONTENTS

1. [System Architecture](#system-architecture)
2. [Database Models](#database-models)
3. [API Endpoints](#api-endpoints)
4. [Service Layer](#service-layer)
5. [Setup Instructions](#setup-instructions)
6. [Production Deployment](#production-deployment)
7. [Security Checklist](#security-checklist)
8. [Monitoring & Alerts](#monitoring--alerts)

---

## 🏗️ SYSTEM ARCHITECTURE

### Apps Structure

```
arkevent_backend/
├── apps/
│   ├── payments/          # Commission, invoices, refunds
│   ├── wallets/           # User wallets, transactions, deposits/withdrawals
│   ├── subscriptions/     # Plans, user subscriptions, premium features
│   ├── finance/           # Analytics, reports, revenue tracking
│   ├── core/              # Permissions, utilities
│   ├── events/            # Events management
│   ├── tickets/           # Ticketing
│   └── [other apps]
```

### Service Layer Architecture

```
┌─────────────────────────────────────────────────────┐
│ REST API Layer (DRF ViewSets)                       │
│ - Serializers, Validation, Permissions              │
└─────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────┐
│ Service Layer (Business Logic)                      │
│ - CommissionService                                 │
│ - PaymentService                                    │
│ - WalletService (Deposit, Withdrawal, Payout)      │
│ - SubscriptionService                              │
│ - PremiumFeatureService                            │
│ - AnalyticsService                                 │
└─────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────┐
│ Models & Database Layer                             │
│ - Atomic transactions for consistency                │
│ - Immutable ledger pattern for wallets               │
└─────────────────────────────────────────────────────┘
```

---

## 📊 DATABASE MODELS

### Commission & Payment Models

**CommissionRule** - Flexible commission configuration
- Supports: percentage, fixed, hybrid
- Deduction models: organizer, customer
- Per-tier configuration

**TicketSale** - Individual ticket transaction record
- Tracks commission and revenue split
- Audit trail for all sales

**Invoice** - Sales/refund receipts
- Buyer and seller facing
- Tax and discount support

**PaymentMethod** - Tokenized payment methods
- Supports: MonCash, NatCash, Digicel, Card, Bank
- User's saved payment options

**RefundRequest** - Refund workflow
- Request → Review → Approve/Reject
- Full audit trail

### Wallet Models

**Wallet** - User's funds account
- Available balance (withdrawable)
- Pending balance (processing)
- Frozen state for disputes

**WalletTransaction** - Immutable ledger entries
- Append-only for audit trail
- Transaction types: deposit, withdrawal, ticket_sale, refund, payout
- Status tracking: pending, completed, failed, reversed

**Deposit** - Money going IN to wallet
- Status: pending → completed
- Provider-specific metadata

**Withdrawal** - Money going OUT from wallet
- User-initiated
- Fee structure (standard free, instant 100 HTG)
- Approval workflow

**Payout** - System-initiated payments to organizers
- Automatic based on schedule/thresholds
- Tracks included transactions

### Subscription Models

**SubscriptionPlan** - Tier definitions
- FREE: 10% commission, 2 events max
- PRO: 5% commission, 1000 HTG/month
- BUSINESS: 2.5% commission, 5000 HTG/month

**UserSubscription** - User's active subscription
- Links user to plan
- Renewal date tracking
- Auto-renew capability

**PremiumFeature** - Monetized features
- Event Boost: 500-1000 HTG, 7-30 days
- Custom Branding: unlock ArkEvent branding requirement
- Sponsored Ads: premium placement

**UserPremiumFeature** - Active feature purchases
- Tracks purchase and expiration
- Per-event tracking for boosts

### Finance Models

**PlatformRevenue** - Daily revenue tracking
- Aggregated from all transaction types
- Currency-specific

**RevenueReport** - Organizer revenue summaries
- Daily/weekly/monthly periods
- Commission calculations
- Refund tracking

**EventBoost** - Visibility boost metrics
- Impressions, clicks, conversions
- Expiration tracking

**AnalyticsDailyMetric** - Event performance data
- Daily views, sales, revenue
- Refunds tracking

---

## 🔌 API ENDPOINTS

### Payments API (`/api/v1/payments/`)

```
GET    /commission-rules/                # View commission rules
GET    /ticket-sales/                    # View ticket sales
GET    /ticket-sales/my-purchases/       # My ticket purchases
GET    /ticket-sales/my-sales/           # My event's sales
GET    /invoices/                        # View invoices
GET    /payment-methods/                 # List my payment methods
POST   /payment-methods/                 # Add new payment method
POST   /payment-methods/{id}/set-default/ # Set default method

POST   /refund-requests/request-refund/  # Request refund
GET    /refund-requests/my-refund-requests/  # My refund requests
GET    /refund-requests/pending-refunds/ # Admin: pending refunds
POST   /refund-requests/approve-refund/  # Admin: approve refund
POST   /refund-requests/reject-refund/   # Admin: reject refund
```

### Wallets API (`/api/v1/wallets/`)

```
GET    /wallets/my-wallet/               # Get wallet info
GET    /wallets/summary/                 # Wallet + statistics
GET    /transactions/                    # Transaction history
POST   /deposits/create-deposit/         # Create deposit request
GET    /deposits/my-deposits/            # Deposit history
POST   /withdrawals/create-withdrawal/   # Request withdrawal
GET    /withdrawals/my-withdrawals/      # Withdrawal history
POST   /withdrawals/approve-withdrawal/  # Admin: approve
POST   /withdrawals/reject-withdrawal/   # Admin: reject
GET    /payouts/                         # Payout history (staff)
```

### Subscriptions API (`/api/v1/subscriptions/`)

```
GET    /plans/                           # View available plans
GET    /user-subscriptions/my-subscription/  # Current subscription
GET    /user-subscriptions/features/     # My subscription features
POST   /user-subscriptions/subscribe/    # Subscribe to plan
POST   /user-subscriptions/cancel/       # Cancel subscription
POST   /user-subscriptions/pause/        # Pause subscription
POST   /user-subscriptions/resume/       # Resume subscription

GET    /premium-features/                # Browse premium features
POST   /user-premium-features/purchase/  # Purchase feature
GET    /user-premium-features/my-features/  # Active features
GET    /user-premium-features/my-event-features/  # Event features
```

### Finance API (`/api/v1/finance/`)

```
GET    /platform-revenue/                # Platform daily revenue
GET    /revenue-reports/                 # Organizer revenue reports
GET    /event-boosts/                    # Event boost history
GET    /analytics-metrics/               # Event analytics
```

---

## 🛠️ SERVICE LAYER

### CommissionService

```python
# Calculate commission for ticket purchase
data = CommissionService.calculate_commission(
    ticket_price=Decimal('500'),
    quantity=2,
    subscription_tier='pro',  # NULL = free tier
    currency='HTG'
)
# Returns: {
#   'subtotal': 1000,
#   'commission_amount': 50,      # 5% for PRO
#   'organizer_net_revenue': 950,
#   'platform_fee': 0,
#   'total_customer_pays': 1000
# }
```

### PaymentService

```python
# Process complete ticket purchase
ticket_sale = PaymentService.process_ticket_purchase(
    event=event,
    buyer=buyer,
    ticket_quantity=2,
    ticket_price_per_unit=Decimal('500'),
    currency='HTG',
    transaction_id='txn_xyz'
)
# Atomically:
# 1. Calculates commission
# 2. Credits organizer wallet
# 3. Creates invoice
# 4. Logs transaction
```

### WalletService

```python
# Create and manage wallet
wallet = WalletService.get_or_create_wallet(user)

# Credit wallet (add funds)
WalletService.credit_wallet(
    wallet,
    Decimal('1000'),
    'ticket_sale',
    'Sale for Event X'
)

# Debit wallet (withdraw funds)
WalletService.debit_wallet(
    wallet,
    Decimal('500'),
    'withdrawal',
    'Payout to MonCash'
)
```

### SubscriptionService

```python
# Subscribe user to plan
subscription = SubscriptionService.subscribe_user(
    user,
    plan,
    currency='HTG'
)

# Get user's subscription tier
tier = SubscriptionService.get_subscription_tier(user)  # 'free'|'pro'|'business'

# Get subscription features
features = SubscriptionAnalyticsService.get_user_subscription_features(user)
```

### PremiumFeatureService

```python
# Purchase premium feature (e.g., Event Boost)
user_premium = PremiumFeatureService.purchase_premium_feature(
    user,
    feature=event_boost_feature,
    event=event,
    currency='HTG'
)

# Check if user has feature
has_boost = PremiumFeatureService.has_premium_feature(
    user,
    'event_boost',
    event=event
)
```

---

## 🚀 SETUP INSTRUCTIONS

### 1. Create Migrations

```bash
# Generate migrations for new models
python manage.py makemigrations payments wallets subscriptions finance

# Review migrations
python manage.py showmigrations

# Apply migrations
python manage.py migrate
```

### 2. Initialize Default Data

```bash
# Create default commission rules
python manage.py shell
>>> from apps.payments.models import CommissionRule
>>> from decimal import Decimal
>>>
>>> # FREE tier: 10%
>>> CommissionRule.objects.create(
...     name='FREE Tier Commission',
...     commission_type='percentage',
...     percentage=Decimal('10'),
...     subscription_tier='free',
...     is_active=True
... )
>>>
>>> # PRO tier: 5%
>>> CommissionRule.objects.create(
...     name='PRO Tier Commission',
...     commission_type='percentage',
...     percentage=Decimal('5'),
...     subscription_tier='pro',
...     is_active=True
... )
>>>
>>> # BUSINESS tier: 2.5%
>>> CommissionRule.objects.create(
...     name='BUSINESS Tier Commission',
...     commission_type='percentage',
...     percentage=Decimal('2.5'),
...     subscription_tier='business',
...     is_active=True
... )

# Create subscription plans
>>> from apps.subscriptions.models import SubscriptionPlan
>>>
>>> free_plan = SubscriptionPlan.objects.create(
...     tier='free',
...     price_htg=0,
...     price_usd=0,
...     commission_percentage=Decimal('10'),
...     max_active_events=2,
...     max_tickets_per_event=100,
...     requires_branding=True,
...     has_basic_analytics=True,
...     is_active=True
... )
>>>
>>> pro_plan = SubscriptionPlan.objects.create(
...     tier='pro',
...     price_htg=Decimal('1000'),
...     price_usd=Decimal('10'),
...     commission_percentage=Decimal('5'),
...     max_active_events=None,  # unlimited
...     max_tickets_per_event=None,  # unlimited
...     requires_branding=False,
...     has_qr_checkin=True,
...     has_advanced_analytics=True,
...     has_custom_pages=True,
...     has_marketing_tools=True,
...     priority_support_level='priority',
...     is_active=True
... )
```

### 3. Register URLs

Update `arkevent_backend/urls.py`:

```python
urlpatterns = [
    # ... existing paths ...
    path('api/v1/payments/', include('apps.payments.urls')),
    path('api/v1/wallets/', include('apps.wallets.urls')),
    path('api/v1/subscriptions/', include('apps.subscriptions.urls')),
    path('api/v1/finance/', include('apps.finance.urls')),
]
```

### 4. Create Finance URLs

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

---

## 🔐 PRODUCTION DEPLOYMENT

### Environment Configuration

```bash
# .env
DJANGO_ENV=production
DEBUG=False
SECRET_KEY=<strong-random-key>

# Database
DATABASE_URL=postgresql://user:password@host:5432/arkevent

# Redis (for Celery)
REDIS_URL=redis://user:password@host:6379/0

# Payment Providers
MONCASH_API_KEY=<key>
NATCASH_API_KEY=<key>
DIGICEL_API_KEY=<key>

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=<email>
EMAIL_HOST_PASSWORD=<password>

# AWS S3 (optional, for invoice storage)
AWS_ACCESS_KEY_ID=<key>
AWS_SECRET_ACCESS_KEY=<key>
AWS_STORAGE_BUCKET_NAME=arkevent-invoices
```

### Database Optimization

```sql
-- Create indexes for query performance
CREATE INDEX idx_wallet_user ON wallets(user_id);
CREATE INDEX idx_wallet_transaction_wallet_date ON wallets.wallet_transactions(wallet_id, created_at DESC);
CREATE INDEX idx_ticket_sale_event_date ON payments.ticket_sales(event_id, created_at DESC);
CREATE INDEX idx_ticket_sale_buyer_date ON payments.ticket_sales(buyer_id, created_at DESC);
CREATE INDEX idx_platform_revenue_date ON finance.platform_revenue(revenue_date DESC);
CREATE INDEX idx_user_subscription_user_status ON subscriptions.user_subscriptions(user_id, status);

-- Partitioning large tables by date
CREATE TABLE wallet_transactions_2024_q1 PARTITION OF wallet_transactions
    FOR VALUES FROM ('2024-01-01') TO ('2024-04-01');
```

### Celery Task Configuration

Create `apps/payments/tasks.py`:

```python
from celery import shared_task
from django.utils import timezone
from .models import Invoice, Withdrawal
from .services import PaymentService, WithdrawalService

@shared_task
def send_invoice_email(invoice_id):
    """Send invoice to buyer."""
    from django.core.mail import EmailMessage
    invoice = Invoice.objects.get(id=invoice_id)
    # ... send email logic ...

@shared_task
def process_pending_withdrawals():
    """Process pending withdrawal requests."""
    withdrawals = Withdrawal.objects.filter(status='pending')
    for withdrawal in withdrawals:
        WithdrawalService.approve_withdrawal(withdrawal)

@shared_task
def generate_daily_revenue_report():
    """Generate daily revenue snapshot."""
    from .models import PlatformRevenue
    from finance.services import PlatformRevenueService
    date = timezone.now().date()
    PlatformRevenueService.calculate_daily_revenue(date)

# Periodic tasks in celery_beat
CELERY_BEAT_SCHEDULE = {
    'process-withdrawals': {
        'task': 'apps.payments.tasks.process_pending_withdrawals',
        'schedule': crontab(hour='*/4'),  # Every 4 hours
    },
    'generate-revenue-report': {
        'task': 'apps.payments.tasks.generate_daily_revenue_report',
        'schedule': crontab(hour=23, minute=59),  # Daily at 23:59
    },
}
```

### Nginx Configuration

```nginx
upstream django {
    server web:8000;
}

server {
    listen 80;
    server_name api.arkevent.com;
    client_max_body_size 20M;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.arkevent.com;
    client_max_body_size 20M;

    ssl_certificate /etc/letsencrypt/live/api.arkevent.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.arkevent.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location /api/ {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    location /static/ {
        alias /app/staticfiles/;
        expires 30d;
    }

    location /media/ {
        alias /app/media/;
    }
}
```

---

## ✅ SECURITY CHECKLIST

- [ ] **Database Encryption**: Enable TLS for PostgreSQL connections
- [ ] **API Rate Limiting**: Implement on sensitive endpoints
  ```python
  from rest_framework.throttling import UserRateThrottle
  
  class PaymentThrottle(UserRateThrottle):
      scope = 'payment'
  
  # In settings.py
  REST_FRAMEWORK = {
      'DEFAULT_THROTTLE_RATES': {
          'payment': '10/hour',
      }
  }
  ```

- [ ] **Input Validation**: Validate all amounts, decimals, currencies
  ```python
  from decimal import Decimal
  from django.core.exceptions import ValidationError
  
  def validate_amount(value):
      try:
          amount = Decimal(str(value))
          if amount <= 0:
              raise ValidationError("Amount must be positive")
          if amount.as_tuple().exponent < -2:
              raise ValidationError("Maximum 2 decimal places")
      except:
          raise ValidationError("Invalid amount")
  ```

- [ ] **Atomic Transactions**: All financial operations use @transaction.atomic
- [ ] **Audit Trail**: Immutable WalletTransaction ledger
- [ ] **Payment PCI Compliance**: Never store raw card details, use tokenization
- [ ] **Webhook Validation**: Verify payment provider signatures
- [ ] **CORS Security**: Restrict to known Flutter domains
  ```python
  CORS_ALLOWED_ORIGINS = [
      "https://app.arkevent.com",
  ]
  ```

- [ ] **JWT Expiration**: Short token lifespan (15-30 min), long refresh tokens
- [ ] **HTTPS Only**: All APIs over HTTPS, HSTS headers
- [ ] **Admin Authentication**: Two-factor auth for staff
- [ ] **Fraud Detection**: Monitor suspicious patterns
  - Rapid withdrawals
  - Large commission jumps
  - Unusual API access patterns

---

## 📊 MONITORING & ALERTS

### Key Metrics

```python
# Monitor in Datadog/NewRelic
metrics = {
    'payment_success_rate': percentage,
    'average_commission': amount,
    'wallet_transaction_latency': milliseconds,
    'withdrawal_approval_time': hours,
    'failed_payments': count,
    'refund_rate': percentage,
}
```

### Alert Rules

```yaml
alerts:
  - name: "High Refund Rate"
    condition: "refund_rate > 5%"
    severity: "warning"
  
  - name: "Payment Provider Down"
    condition: "moncash_success_rate < 90%"
    severity: "critical"
  
  - name: "Wallet Balance Mismatch"
    condition: "wallet_balance != sum(transactions)"
    severity: "critical"
  
  - name: "Slow API Response"
    condition: "api_latency_p95 > 1000ms"
    severity: "warning"
```

### Logging Configuration

```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/financial.log',
            'maxBytes': 1024 * 1024 * 100,  # 100MB
            'backupCount': 10,
        },
    },
    'loggers': {
        'apps.payments': {'handlers': ['file'], 'level': 'INFO'},
        'apps.wallets': {'handlers': ['file'], 'level': 'INFO'},
        'apps.subscriptions': {'handlers': ['file'], 'level': 'INFO'},
    },
}

# In services, log important events
import logging
logger = logging.getLogger(__name__)

logger.info(f"Ticket sale created: {ticket_sale.id}, commission: {commission}")
logger.warning(f"High refund rate detected: {refund_percentage}%")
logger.error(f"Payment processing failed: {error}")
```

---

## 📱 Flutter Integration (Next Steps)

See `FLUTTER_INTEGRATION.md` for:
- Dio API client generation
- Repository pattern implementation
- Riverpod provider setup
- Clean architecture structure
- Flutter UI examples

---

Generated: May 27, 2024
Version: 1.0
Status: Production-Ready
