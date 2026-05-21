import jwt
from django.test import TestCase, RequestFactory
from django.conf import settings
from .auth import SupabaseJWTAuthentication
from rest_framework import exceptions

class SupabaseAuthTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.auth = SupabaseJWTAuthentication()

    def test_authenticate_no_header(self):
        request = self.factory.get('/')
        result = self.auth.authenticate(request)
        self.assertIsNone(result)

    def test_authenticate_invalid_token(self):
        request = self.factory.get('/', HTTP_AUTHORIZATION='Bearer invalid_token')
        with self.assertRaises(exceptions.AuthenticationFailed):
            self.auth.authenticate(request)

    def test_authenticate_valid_token(self):
        payload = {'sub': '12345678-1234-1234-1234-123456789012', 'aud': 'authenticated'}
        token = jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm='HS256')
        request = self.factory.get('/', HTTP_AUTHORIZATION=f'Bearer {token}')
        user, auth = self.auth.authenticate(request)
        self.assertEqual(user.id, payload['sub'])
        self.assertEqual(user.claims, payload)
