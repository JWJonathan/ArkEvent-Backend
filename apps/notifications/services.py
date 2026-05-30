from django.core.mail import send_mail
from django.conf import settings
from .models import NotificationLog, PushToken, EventNotificationSetting
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    @staticmethod
    def send_notification(user, title, body, notification_type='push', event=None, order=None, metadata=None):
        """
        Base method to send a notification and log it.
        """
        # Check user settings for this event if applicable
        if event:
            setting = EventNotificationSetting.objects.filter(user=user, event=event).first()
            if setting:
                if notification_type == 'push' and not setting.push_enabled:
                    logger.info(f"Push disabled for user {user.id} on event {event.id}")
                    return False
                if notification_type == 'email' and not setting.email_enabled:
                    logger.info(f"Email disabled for user {user.id} on event {event.id}")
                    return False

        # Create log entry
        log = NotificationLog.objects.create(
            user=user,
            type=notification_type,
            title=title,
            body=body,
            event=event,
            order=order,
            metadata=metadata or {}
        )

        if notification_type == 'email':
            return NotificationService._send_email(user.email, title, body)
        elif notification_type == 'push':
            return NotificationService._send_push(user, title, body, metadata)
        elif notification_type == 'sms':
            return NotificationService._send_sms(user, title, body)
        
        return False

    @staticmethod
    def _send_email(email, title, body):
        try:
            send_mail(
                title,
                body,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {email}: {str(e)}")
            return False

    @staticmethod
    def _send_push(user, title, body, metadata=None):
        # Find active push tokens for user
        tokens = PushToken.objects.filter(user=user, is_active=True)
        if not tokens.exists():
            logger.info(f"No active push tokens for user {user.id}")
            return False
        
        # Integration with FCM or similar would go here
        logger.info(f"Sending push notification to user {user.id}: {title}")
        # Placeholder for actual push delivery
        return True

    @staticmethod
    def _send_sms(user, title, body):
        # Placeholder for SMS provider (e.g., Twilio)
        logger.info(f"Sending SMS to user {user.id}: {body}")
        return True

    @classmethod
    def notify_ticket_purchase(cls, user, order):
        title = "Confirmation d'achat de billet"
        body = f"Félicitations ! Votre achat pour l'événement {order.event.title} est confirmé."
        
        # Send Push
        cls.send_notification(user, title, body, notification_type='push', event=order.event, order=order)
        # Send Email
        cls.send_notification(user, title, body, notification_type='email', event=order.event, order=order)

    @classmethod
    def notify_ticket_transfer(cls, sender, receiver, ticket):
        # Notify Receiver
        title_rec = "Nouveau billet reçu !"
        body_rec = f"{sender.profile.full_name if sender.profile else sender.email} vous a envoyé un billet pour {ticket.ticket_type.event.title}."
        cls.send_notification(receiver, title_rec, body_rec, notification_type='push', event=ticket.ticket_type.event)
        
        # Notify Sender
        title_send = "Transfert de billet réussi"
        body_send = f"Votre billet pour {ticket.ticket_type.event.title} a été transféré avec succès à {receiver.profile.full_name if receiver.profile else receiver.email}."
        cls.send_notification(sender, title_send, body_send, notification_type='push', event=ticket.ticket_type.event)

    @classmethod
    def notify_event_reminder(cls, user, event):
        title = f"Rappel : {event.title}"
        body = f"Votre événement {event.title} commence bientôt. Préparez vos billets !"
        cls.send_notification(user, title, body, notification_type='push', event=event)

    @classmethod
    def notify_all_participants(cls, event, title, body, metadata=None):
        """
        Sends a notification to all users who have a ticket for the event.
        """
        from apps.tickets.models import Ticket
        # Get unique owners of confirmed/sold tickets for this event
        participants = Ticket.objects.filter(
            ticket_type__event=event,
            status__in=['confirmed', 'sold', 'used'],
            owner__isnull=False
        ).values_list('owner', flat=True).distinct()

        from django.contrib.auth import get_user_model
        User = get_user_model()
        users = User.objects.filter(id__in=participants)

        for user in users:
            cls.send_notification(user, title, body, notification_type='push', event=event, metadata=metadata)


    @classmethod
    def notify_organization_created(cls, user, organization):
        """
        Sends notifications when a user creates a new organization.
        """
        title = "Félicitations ! Organisation créée"
        body = f"Vous avez créé l'organisation '{organization.name}'."
        
        # Assuming organization has a 'name' attribute and can act as an event/metadata source
        # We'll use the organization object as metadata and potentially the event if it's linked.
        # For simplicity, we'll treat it as a general notification event for now.
        
        # Send Push
        cls.send_notification(user, title, body, notification_type='push', event=None, metadata={'organization': organization})
        # Send Email
        cls.send_notification(user, title, body, notification_type='email', event=None, metadata={'organization': organization})
