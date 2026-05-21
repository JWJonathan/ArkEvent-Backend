import jwt
from django.conf import settings
from rest_framework import authentication, exceptions
from apps.users.models import Profile
from apps.users.services.supabase_auth import SupabaseAuthAdapter

class SupabaseUser:
    def __init__(self, user_id, claims):
        self.id = user_id
        self.claims = claims
        self.is_authenticated = True

    @property
    def is_anonymous(self):
        return False

class SupabaseJWTAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header:
            return None

        try:
            parts = auth_header.split()
            if parts[0].lower() != 'bearer' or len(parts) != 2:
                raise exceptions.AuthenticationFailed('Invalid token header. Format should be: Bearer <token>')
            token = parts[1]
        except (IndexError, AttributeError):
            raise exceptions.AuthenticationFailed('Invalid token header. No credentials provided.')

        try:
            # Decode with signature verification and audience/issuer/expiry checks
            options = {
                'verify_signature': True,
                'verify_exp': True,
                'verify_aud': True,
                'require': ['exp', 'sub', 'aud']
            }

            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
                # Supabase tokens typically have an issuer like "https://<project>.supabase.co/auth/v1"
                # but we'll stick to audience which is most critical and standard for Supabase
                options=options
            )
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Token has expired')
        except jwt.InvalidAudienceError:
            raise exceptions.AuthenticationFailed('Invalid audience')
        except jwt.InvalidTokenError as e:
            raise exceptions.AuthenticationFailed(f'Invalid token: {str(e)}')
        except Exception as e:
            raise exceptions.AuthenticationFailed(str(e))

        user_id = payload.get('sub')
        if not user_id:
            raise exceptions.AuthenticationFailed('User ID (sub) not found in token')

        # Sync Profile
        user_data = {
            "id": user_id,
            "email": payload.get('email', '')
        }
        SupabaseAuthAdapter.sync_profile(user_data)

        return (SupabaseUser(user_id, payload), None)

    def authenticate_header(self, request):
        return 'Bearer'
