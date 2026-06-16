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
    def notify_event_reminder(cls, event, timeframe):
        titles = {
            '7d': f"Rappel : 7 jours avant {event.title}",
            '24h': f"Rappel : 24 heures avant {event.title}",
            '1h': f"Rappel : 1 heure avant {event.title}",
        }
        bodies = {
            '7d': f"Plus que 7 jours avant {event.title} ! Préparez-vous pour l'expérience.",
            '24h': f"J-1 ! L'événement {event.title} commence dans 24 heures. Avez-vous vos billets ?",
            '1h': f"H-1 ! {event.title} commence dans une heure. Nous vous attendons !",
        }
        title = titles.get(timeframe, f"Rappel : {event.title}")
        body = bodies.get(timeframe, f"Votre événement {event.title} commence bientôt.")
        cls.notify_all_participants(event, title, body)

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
        cls.send_notification(user, title, body, notification_type='push', metadata={'organization_id': str(organization.id)})
        cls.send_notification(user, title, body, notification_type='email', metadata={'organization_id': str(organization.id)})

    @classmethod
    def notify_organization_verified(cls, user, organization):
        """
        Sends notifications when an organization is verified.
        """
        title = "Organisation vérifiée"
        body = f"Félicitations ! Votre organisation '{organization.name}' a été vérifiée."
        cls.send_notification(user, title, body, notification_type='push', metadata={'organization_id': str(organization.id)})
        cls.send_notification(user, title, body, notification_type='email', metadata={'organization_id': str(organization.id)})

    @classmethod
    def notify_event_created(cls, user, event):
        """
        Sends notifications when a user creates a new event.
        """
        title = "Nouvel événement créé"
        body = f"Vous avez créé l'événement '{event.title}'."
        cls.send_notification(user, title, body, notification_type='push', event=event, metadata={'event_id': str(event.id)})
        # Optional: Email as well if desired
        cls.send_notification(user, title, body, notification_type='email', event=event, metadata={'event_id': str(event.id)})

    @classmethod
    def notify_event_published(cls, user, event):
        """
        Sends an email notification when an event status is set to published.
        """
        title = "Événement publié !"
        body = f"Félicitations ! Votre événement '{event.title}' est maintenant publié."
        # Email as requested
        cls.send_notification(user, title, body, notification_type='email', event=event, metadata={'event_id': str(event.id)})
        # Also push for better visibility
        cls.send_notification(user, title, body, notification_type='push', event=event, metadata={'event_id': str(event.id)})

    @classmethod
    def notify_plan_activated(cls, user, subscription):
        """
        Sends notifications when a user activates a plan.
        """
        plan = subscription.plan
        title = "Plan activé avec succès"
        body = (
            f"Votre plan '{plan.get_tier_display()}' a été activé.\n"
            f"Détails :\n"
            f"- Prix : {subscription.amount_paid} {subscription.currency}\n"
            f"- Cycle : {plan.get_billing_cycle_display()}\n"
            f"- Renouvellement : {subscription.renewal_date}"
        )
        metadata = {
            'plan_id': str(plan.id),
            'subscription_id': str(subscription.id),
            'tier': plan.tier
        }
        cls.send_notification(user, title, body, notification_type='push', metadata=metadata)
        cls.send_notification(user, title, body, notification_type='email', metadata=metadata)

    @classmethod
    def notify_ticket_order_placed(cls, user, order):
        """
        Sends notifications when a user places a ticket order, with all details.
        """
        # Retrieve items for the order to get ticket details
        items = order.items.all()
        items_details = "\n".join(
            [f"- {item.quantity}x {item.ticket_type.name} à {item.price_at_purchase} {order.currency}" 
             for item in items]
        )
        
        title = "Commande confirmée"
        body = (
            f"Votre commande pour l'événement '{order.event.title}' a été passée avec succès.\n"
            f"Détails des billets :\n"
            f"{items_details}\n"
            f"Total : {order.total_amount} {order.currency}"
        )
        
        metadata = {
            'order_id': str(order.id),
            'event_id': str(order.event.id)
        }
        
        cls.send_notification(user, title, body, notification_type='push', event=order.event, order=order, metadata=metadata)
        cls.send_notification(user, title, body, notification_type='email', event=order.event, order=order, metadata=metadata)

    @classmethod
    def notify_provider_created(cls, user, provider):
        """
        Sends notification when a provider account is created.
        """
        title = "Compte prestataire créé"
        body = f"Votre demande de création de compte prestataire pour '{provider.business_name}' a été reçue."
        cls.send_notification(user, title, body, notification_type='push')
        cls.send_notification(user, title, body, notification_type='email')

    @classmethod
    def notify_provider_verified(cls, user, provider):
        """
        Sends notification when a provider account is verified.
        """
        title = "Compte prestataire vérifié"
        body = f"Félicitations ! Votre compte prestataire '{provider.business_name}' est maintenant vérifié."
        cls.send_notification(user, title, body, notification_type='push')
        cls.send_notification(user, title, body, notification_type='email')

    @classmethod
    def notify_service_created(cls, user, service):
        """
        Sends notification when a user creates a new marketplace service.
        """
        title = "Nouveau service créé"
        body = f"Vous avez créé le service '{service.title}' avec succès."
        metadata = {'service_id': str(service.id)}
        cls.send_notification(user, title, body, notification_type='push', metadata=metadata)
        cls.send_notification(user, title, body, notification_type='email', metadata=metadata)

    @classmethod
    def notify_service_published(cls, user, service):
        """
        Sends notification when a marketplace service is published.
        """
        title = "Service publié !"
        body = f"Félicitations ! Votre service '{service.title}' est maintenant publié sur la marketplace."
        metadata = {'service_id': str(service.id)}
        cls.send_notification(user, title, body, notification_type='push', metadata=metadata)
        cls.send_notification(user, title, body, notification_type='email', metadata=metadata)

    @classmethod
    def notify_booking_created(cls, user, booking):
        """
        Sends notification when a user places a service booking.
        """
        title = "Nouvelle réservation"
        body = f"Votre réservation pour '{booking.service.title}' (Réf: {booking.reference}) a été créée et est en attente."
        metadata = {'booking_id': str(booking.id)}
        cls.send_notification(user, title, body, notification_type='push', metadata=metadata)
        cls.send_notification(user, title, body, notification_type='email', metadata=metadata)

    @classmethod
    def notify_booking_status_changed(cls, user, booking):
        """
        Sends notification when a service booking status changes.
        """
        title = f"Mise à jour de réservation : {booking.reference}"
        body = f"Le statut de votre réservation pour '{booking.service.title}' est passé à : {booking.get_status_display()}."
        metadata = {'booking_id': str(booking.id)}
        cls.send_notification(user, title, body, notification_type='push', metadata=metadata)
        cls.send_notification(user, title, body, notification_type='email', metadata=metadata)

    # 🎉 Événements
    @classmethod
    def notify_event_update(cls, event, change_type):
        titles = {
            'time': f"Modification de l'heure : {event.title}",
            'location': f"Modification du lieu : {event.title}",
            'schedule': f"Changement du programme : {event.title}",
            'cancelled': f"Événement annulé : {event.title}",
            'started': f"L'événement commence maintenant : {event.title}",
        }
        bodies = {
            'time': f"L'heure de l'événement {event.title} a été modifiée. Consultez les nouveaux horaires.",
            'location': f"Le lieu de l'événement {event.title} a changé. Vérifiez la nouvelle adresse.",
            'schedule': f"Le programme de l'événement {event.title} a été mis à jour.",
            'cancelled': f"Nous sommes au regret de vous annoncer que l'événement {event.title} est annulé.",
            'started': f"C'est parti ! L'événement {event.title} commence dès maintenant. Rejoignez-nous !",
        }
        title = titles.get(change_type, f"Mise à jour : {event.title}")
        body = bodies.get(change_type, f"Il y a du nouveau pour l'événement {event.title}.")
        cls.notify_all_participants(event, title, body)

    @classmethod
    def notify_during_event(cls, event, notify_type, extra_data=None):
        titles = {
            'checkin': "Check-in disponible",
            'activity': "Une activité commence bientôt",
            'organizer_msg': "Nouveau message des organisateurs",
            'photo': "Nouvelle photo ajoutée",
        }
        bodies = {
            'checkin': f"Le check-in pour {event.title} est maintenant ouvert. Présentez votre billet !",
            'activity': f"Une activité de l'événement {event.title} va commencer dans quelques minutes.",
            'organizer_msg': f"Les organisateurs de {event.title} ont envoyé un nouveau message.",
            'photo': f"De nouvelles photos ont été ajoutées à l'album de {event.title}.",
        }
        title = titles.get(notify_type, event.title)
        body = bodies.get(notify_type, "")
        cls.notify_all_participants(event, title, body, metadata=extra_data)

    @classmethod
    def notify_post_event(cls, event, notify_type):
        titles = {
            'thanks': f"Merci d'avoir participé à {event.title}",
            'review': "Laissez une évaluation",
            'certificate': "Téléchargez votre certificat",
            'photos': "Consultez les photos de l'événement",
        }
        bodies = {
            'thanks': f"Merci de votre présence à {event.title}. Nous espérons que vous avez apprécié !",
            'review': f"Votre avis compte ! Donnez une note à l'événement {event.title}.",
            'certificate': f"Votre certificat de participation pour {event.title} est prêt.",
            'photos': f"Les photos souvenirs de {event.title} sont disponibles.",
        }
        title = titles.get(notify_type, event.title)
        body = bodies.get(notify_type, "")
        cls.notify_all_participants(event, title, body)

    # 👥 Organisations
    @classmethod
    def notify_member_invite(cls, organization, invited_user, inviter):
        title = f"Invitation : {organization.name}"
        body = f"{inviter.profile.full_name if hasattr(inviter, 'profile') and inviter.profile else inviter.email} vous a invité à rejoindre '{organization.name}'."
        cls.send_notification(invited_user, title, body, metadata={'organization_id': str(organization.id)})

    @classmethod
    def notify_membership_status(cls, organization, user, status):
        titles = {
            'accepted': "Demande acceptée",
            'refused': "Demande refusée",
            'role_assigned': "Nouveau rôle attribué",
        }
        bodies = {
            'accepted': f"Votre demande pour rejoindre '{organization.name}' a été acceptée. Bienvenue !",
            'refused': f"Désolé, votre demande pour rejoindre '{organization.name}' n'a pas été retenue.",
            'role_assigned': f"Un nouveau rôle vous a été attribué au sein de '{organization.name}'.",
        }
        title = titles.get(status, organization.name)
        body = bodies.get(status, "")
        cls.send_notification(user, title, body, metadata={'organization_id': str(organization.id)})

    # 🎫 Billetterie
    @classmethod
    def notify_ticket_status(cls, user, ticket, status):
        titles = {
            'generated': "Votre ticket est prêt",
            'refunded': "Ticket remboursé",
            'failed': "Paiement échoué",
        }
        bodies = {
            'generated': f"Le ticket pour {ticket.ticket_type.event.title} a été généré avec succès.",
            'refunded': f"Votre ticket pour {ticket.ticket_type.event.title} a été remboursé.",
            'failed': f"Le paiement pour votre ticket à l'événement {ticket.ticket_type.event.title} a échoué.",
        }
        title = titles.get(status, "Mise à jour de ticket")
        body = bodies.get(status, "")
        cls.send_notification(user, title, body, event=ticket.ticket_type.event)

    @classmethod
    def notify_organizer_sales(cls, event, notify_type, extra_data=None):
        organization = event.organization
        admins = organization.members.filter(org_role__in=['owner', 'admin']).select_related('user')
        
        titles = {
            'sale': "Nouveau ticket vendu",
            'milestone': "Vente importante atteinte",
            'low_stock': "Stock de tickets faible",
            'sold_out': "Tous les tickets sont vendus",
        }
        bodies = {
            'sale': f"Un nouveau ticket a été vendu pour {event.title}.",
            'milestone': f"Félicitations ! Un jalon de vente a été atteint pour {event.title}.",
            'low_stock': f"Attention : le stock de tickets pour {event.title} est presque épuisé.",
            'sold_out': f"Succès ! Tous les tickets pour {event.title} ont été vendus.",
        }
        title = titles.get(notify_type, event.title)
        body = bodies.get(notify_type, "")
        
        for admin in admins:
            cls.send_notification(admin.user, title, body, event=event, metadata=extra_data)

    # 💳 Paiements & Abonnements
    @classmethod
    def notify_payment_user(cls, user, notify_type, amount=None, currency="USD"):
        titles = {
            'success': "Paiement réussi",
            'failed': "Paiement échoué",
            'invoice': "Facture disponible",
            'sub_renewed': "Abonnement renouvelé",
            'sub_expiring': "Abonnement expirera bientôt",
            'withdrawal_approved': "Retrait approuvé",
            'withdrawal_refused': "Retrait refusé",
        }
        bodies = {
            'success': f"Votre paiement de {amount} {currency} a été effectué avec succès.",
            'failed': f"Le paiement de {amount} {currency} a échoué. Veuillez vérifier vos informations.",
            'invoice': "Une nouvelle facture est disponible dans votre espace personnel.",
            'sub_renewed': "Votre abonnement a été renouvelé automatiquement.",
            'sub_expiring': "Votre abonnement arrive à échéance prochainement. Pensez à le renouveler.",
            'withdrawal_approved': f"Votre retrait de {amount} {currency} a été approuvé et envoyé.",
            'withdrawal_refused': f"Votre retrait de {amount} {currency} a été refusé.",
        }
        title = titles.get(notify_type, "Paiement")
        body = bodies.get(notify_type, "")
        cls.send_notification(user, title, body)

    # ⭐ Réseau social
    @classmethod
    def notify_social_interaction(cls, user, interaction_type, actor, event=None):
        actor_name = actor.profile.full_name if hasattr(actor, 'profile') and actor.profile else actor.email
        titles = {
            'follow': "Nouveau follower",
            'like': "Événement aimé",
            'share': "Événement partagé",
            'comment': "Nouveau commentaire",
            'reply': "Réponse à votre commentaire",
        }
        bodies = {
            'follow': f"{actor_name} a commencé à vous suivre.",
            'like': f"{actor_name} a aimé votre événement {event.title if event else ''}.",
            'share': f"{actor_name} a partagé votre événement {event.title if event else ''}.",
            'comment': f"{actor_name} a commenté votre événement {event.title if event else ''}.",
            'reply': f"{actor_name} a répondu à votre commentaire.",
        }
        title = titles.get(interaction_type, "Nouvelle interaction")
        body = bodies.get(interaction_type, "")
        cls.send_notification(user, title, body, event=event)

    @classmethod
    def notify_messaging(cls, user, msg_type, sender, extra_data=None):
        sender_name = sender.profile.full_name if hasattr(sender, 'profile') and sender.profile else sender.email
        titles = {
            'private': "Nouveau message privé",
            'group': "Nouveau message de groupe",
            'mention': "Mention dans une conversation",
        }
        bodies = {
            'private': f"Vous avez reçu un message de {sender_name}.",
            'group': f"Nouveau message dans le groupe de la part de {sender_name}.",
            'mention': f"{sender_name} vous a mentionné dans une conversation.",
        }
        title = titles.get(msg_type, "Message")
        body = bodies.get(msg_type, "")
        cls.send_notification(user, title, body, metadata=extra_data)

    # 🏆 Engagement & Gamification
    @classmethod
    def notify_gamification(cls, user, notify_type, label=None):
        titles = {
            'first_event': "Premier événement créé !",
            'first_sale': "Premier ticket vendu !",
            'event_completed': "Événement complété !",
            'badge': "Nouveau badge obtenu",
            'level': "Nouveau niveau atteint",
            'goal': "Objectif mensuel atteint",
        }
        bodies = {
            'first_event': "Félicitations ! Vous venez de créer votre premier événement sur ArkEvent.",
            'first_sale': "Bravo ! Vous avez réalisé votre première vente.",
            'event_completed': "Félicitations pour la réussite de votre événement !",
            'badge': f"Vous avez débloqué le badge : {label}.",
            'level': f"Vous êtes passé au niveau {label} !",
            'goal': "Super ! Vous avez atteint votre objectif du mois.",
        }
        title = titles.get(notify_type, "Succès !")
        body = bodies.get(notify_type, "")
        cls.send_notification(user, title, body)

    # 📢 Marketing
    @classmethod
    def notify_marketing(cls, user, notify_type, extra_data=None):
        titles = {
            'popular': "Événements populaires près de vous",
            'interests': "Événements correspondant à vos intérêts",
            'weekly': "Nouveaux événements cette semaine",
            'promo': "Offre spéciale",
            'code': "Code promo disponible",
        }
        bodies = {
            'popular': "Découvrez les événements qui font le buzz autour de vous.",
            'interests': "Nous avons trouvé des événements qui pourraient vous plaire.",
            'weekly': "Voici les nouveautés de la semaine à ne pas manquer.",
            'promo': "Profitez d'une réduction limitée sur votre prochain achat !",
            'code': f"Utilisez le code {extra_data.get('code') if extra_data else ''} pour votre prochain billet.",
        }
        title = titles.get(notify_type, "À découvrir")
        body = bodies.get(notify_type, "")
        cls.send_notification(user, title, body, metadata=extra_data)

    # 🔒 Sécurité
    @classmethod
    def notify_security(cls, user, notify_type, extra_data=None):
        titles = {
            'login': "Nouvelle connexion détectée",
            'device': "Connexion depuis un nouvel appareil",
            'password': "Changement de mot de passe",
            'email': "Adresse email modifiée",
            'failed_login': "Tentative de connexion échouée",
            '2fa': "Authentification à deux facteurs activée",
        }
        bodies = {
            'login': "Une nouvelle connexion a été effectuée sur votre compte.",
            'device': "Votre compte a été accédé depuis un nouvel appareil.",
            'password': "Le mot de passe de votre compte a été modifié avec succès.",
            'email': "Votre adresse email de contact a été mise à jour.",
            'failed_login': "Plusieurs tentatives de connexion ont échoué sur votre compte.",
            '2fa': "La sécurité 2FA est maintenant active sur votre compte.",
        }
        title = titles.get(notify_type, "Sécurité")
        body = bodies.get(notify_type, "")
        cls.send_notification(user, title, body, metadata=extra_data)

    # 🛠 Système
    @classmethod
    def notify_system(cls, user, notify_type, extra_data=None):
        titles = {
            'maintenance': "Maintenance programmée",
            'version': "Nouvelle version disponible",
            'feature': "Fonctionnalité ajoutée",
            'incident': "Incident résolu",
        }
        bodies = {
            'maintenance': "Une maintenance est prévue pour améliorer nos services.",
            'version': "Une mise à jour d'ArkEvent est disponible. Découvrez les nouveautés !",
            'feature': "Nous avons ajouté une nouvelle fonctionnalité rien que pour vous.",
            'incident': "Le problème technique a été résolu. Merci de votre patience.",
        }
        title = titles.get(notify_type, "Système")
        body = bodies.get(notify_type, "")
        cls.send_notification(user, title, body, metadata=extra_data)

    # 💎 Premium
    @classmethod
    def notify_premium(cls, user, notify_type):
        titles = {
            'first_org': "Créez votre première organisation",
            'unlimited': "Passez à Premium",
            'limit_reached': "Limite d'événements atteinte",
            'stats': "Débloquez les statistiques avancées",
            'campaigns': "Débloquez les campagnes marketing",
        }
        bodies = {
            'first_org': "Commencez dès maintenant en créant votre première organisation.",
            'unlimited': "Passez au plan Premium pour créer des événements en illimité !",
            'limit_reached': "Vous avez atteint votre limite. Passez à Premium pour continuer.",
            'stats': "Prenez de meilleures décisions avec nos analyses détaillées.",
            'campaigns': "Boostez votre visibilité avec les outils marketing Premium.",
        }
        title = titles.get(notify_type, "ArkEvent Premium")
        body = bodies.get(notify_type, "")
        cls.send_notification(user, title, body)
