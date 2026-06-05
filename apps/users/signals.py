from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from apps.notifications.services import NotificationService

# @receiver(user_logged_in)
# def notify_user_login(sender, request, user, **kwargs):
#     # Detect if it's a new device/IP (optional, but requested)
#     # For now, just send a basic login notification
#     NotificationService.notify_security(user, 'login')
