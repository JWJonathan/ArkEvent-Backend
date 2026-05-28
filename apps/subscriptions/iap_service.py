import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def verify_google_purchase(package_name, product_id, purchase_token, is_subscription=True):
    """
    Verifies a purchase token with Google Play Developer API.
    
    Args:
        package_name (str): The package name of the app (e.g., com.arkevent.app)
        product_id (str): The product or subscription ID
        purchase_token (str): The purchase token from the app
        is_subscription (bool): True if verifying a subscription, False for a one-time product
        
    Returns:
        dict: The response from Google Play API if successful
    """
    # Path to Google service account JSON
    credentials_path = getattr(settings, 'GOOGLE_PLAY_CREDENTIALS_PATH', 
                               os.path.join(settings.BASE_DIR, 'config/google_service_account.json'))
    
    if not os.path.exists(credentials_path):
        logger.error(f"Google Play credentials not found at {credentials_path}")
        raise FileNotFoundError(f"Google Play credentials not found at {credentials_path}")

    scopes = ['https://www.googleapis.com/auth/androidpublisher']

    try:
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path, scopes=scopes
        )

        service = build('androidpublisher', 'v3', credentials=credentials)

        if is_subscription:
            request = service.purchases().subscriptions().get(
                packageName=package_name,
                subscriptionId=product_id,
                token=purchase_token
            )
        else:
            request = service.purchases().products().get(
                packageName=package_name,
                productId=product_id,
                token=purchase_token
            )

        response = request.execute()
        return response
    except Exception as e:
        logger.exception(f"Error verifying Google Play purchase: {str(e)}")
        raise
