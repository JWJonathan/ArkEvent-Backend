from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('apps.core.urls')),
    path('api/v1/users/', include('apps.users.urls')),
    path('api/v1/events/', include('apps.events.urls')),
    path('api/v1/organization/', include('apps.organization.urls')),
    path('api/v1/tickets/', include('apps.tickets.urls')),
    path('api/v1/payments/', include('apps.payments.urls')),
    path('api/v1/marketing/', include('apps.marketing.urls')),
    path('api/v1/notifications/', include('apps.notifications.urls')),
    path('api/v1/networking/', include('apps.networking.urls')),
    path('api/v1/surveys/', include('apps.surveys.urls')),
    path('api/v1/analytics/', include('apps.analytics.urls')),
]
