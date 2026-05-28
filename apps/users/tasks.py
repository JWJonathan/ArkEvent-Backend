from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth import get_user_model
import random
import string
from datetime import timedelta
from django.utils import timezone

User = get_user_model()


@shared_task
def send_verification_email(user_id, code):
    """
    Send email verification code to user.
    
    Args:
        user_id: UUID of the user
        code: 6-digit verification code
    """
    try:
        user = User.objects.get(id=user_id)
        
        subject = "Vérification de votre adresse email - ArkEvent"
        
        # HTML email template
        html_message = f"""
        <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; background-color: #f5f5f5; }}
                    .container {{ max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 20px; border-radius: 8px; }}
                    .header {{ text-align: center; margin-bottom: 20px; }}
                    .header h2 {{ color: #5B3FFF; margin: 0; }}
                    .content {{ text-align: center; margin: 30px 0; }}
                    .code {{ font-size: 32px; letter-spacing: 5px; color: #5B3FFF; font-weight: bold; margin: 20px 0; background-color: #f9f9f9; padding: 15px; border-radius: 5px; }}
                    .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 30px; border-top: 1px solid #eee; padding-top: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>🎉 Bienvenue sur ArkEvent!</h2>
                    </div>
                    <div class="content">
                        <p>Merci d'avoir créé un compte.</p>
                        <p>Votre code de vérification est:</p>
                        <div class="code">{code}</div>
                        <p>Ce code expire dans 24 heures.</p>
                        <p style="color: #999; font-size: 14px;">Si vous n'avez pas créé de compte, veuillez ignorer cet email.</p>
                    </div>
                    <div class="footer">
                        <p>© 2026 ArkEvent. Tous droits réservés.</p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        # Plain text version
        text_message = f"""
Bienvenue sur ArkEvent!

Votre code de vérification est: {code}

Ce code expire dans 24 heures.

Si vous n'avez pas créé de compte, veuillez ignorer cet email.

© 2026 ArkEvent. Tous droits réservés.
        """
        
        send_mail(
            subject,
            text_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        return {
            'success': True,
            'message': f'Verification email sent to {user.email}'
        }
    
    except User.DoesNotExist:
        return {
            'success': False,
            'message': f'User with id {user_id} does not exist'
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'Error sending email: {str(e)}'
        }


@shared_task
def send_password_reset_email(user_id, code):
    """
    Send password reset code to user.
    
    Args:
        user_id: UUID of the user
        code: 6-digit reset code
    """
    try:
        user = User.objects.get(id=user_id)
        
        subject = "Réinitialisation de votre mot de passe - ArkEvent"
        
        html_message = f"""
        <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; background-color: #f5f5f5; }}
                    .container {{ max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 20px; border-radius: 8px; }}
                    .header {{ text-align: center; margin-bottom: 20px; }}
                    .header h2 {{ color: #5B3FFF; margin: 0; }}
                    .content {{ text-align: center; margin: 30px 0; }}
                    .code {{ font-size: 32px; letter-spacing: 5px; color: #5B3FFF; font-weight: bold; margin: 20px 0; background-color: #f9f9f9; padding: 15px; border-radius: 5px; }}
                    .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 30px; border-top: 1px solid #eee; padding-top: 20px; }}
                    .warning {{ color: #d9534f; font-weight: bold; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>🔐 Réinitialisation de mot de passe</h2>
                    </div>
                    <div class="content">
                        <p>Vous avez demandé une réinitialisation de mot de passe.</p>
                        <p>Votre code de réinitialisation est:</p>
                        <div class="code">{code}</div>
                        <p>Ce code expire dans 15 minutes.</p>
                        <p class="warning">⚠️ Si vous n'avez pas demandé cette réinitialisation, veuillez ignorer cet email.</p>
                    </div>
                    <div class="footer">
                        <p>© 2026 ArkEvent. Tous droits réservés.</p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        text_message = f"""
Réinitialisation de mot de passe

Vous avez demandé une réinitialisation de mot de passe.

Votre code de réinitialisation est: {code}

Ce code expire dans 15 minutes.

Si vous n'avez pas demandé cette réinitialisation, veuillez ignorer cet email.

© 2026 ArkEvent. Tous droits réservés.
        """
        
        send_mail(
            subject,
            text_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        return {
            'success': True,
            'message': f'Password reset email sent to {user.email}'
        }
    
    except User.DoesNotExist:
        return {
            'success': False,
            'message': f'User with id {user_id} does not exist'
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'Error sending email: {str(e)}'
        }
