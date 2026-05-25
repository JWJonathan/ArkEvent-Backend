from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('apps.core.urls')),
    path('api/users/', include('apps.users.urls')),
    path('api/events/', include('apps.events.urls')),
    path('api/organizations/', include('apps.organization.urls')),
    path('api/tickets/', include('apps.tickets.urls')),
    path('api/payments/', include('apps.payments.urls')),
    path('api/marketing/', include('apps.marketing.urls')),
    path('api/notifications/', include('apps.notifications.urls')),
    path('api/networking/', include('apps.networking.urls')),
    path('api/surveys/', include('apps.surveys.urls')),
    path('api/analytics/', include('apps.analytics.urls')),
]
