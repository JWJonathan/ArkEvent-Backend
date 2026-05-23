from time import timezone

import jwt
from django.test import TestCase, RequestFactory
from django.conf import settings
from rest_framework import exceptions

class JWTAuthenticationTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.valid_payload = {
            'user_id': 1,
            'exp': timezone.now() + timezone.timedelta(hours=1)
        }
        self.invalid_payload = {
            'user_id': 1,
            'exp': timezone.now() - timezone.timedelta(hours=1)  # Expired token
        }
        self.valid_token = jwt.encode(self.valid_payload, settings.SECRET_KEY, algorithm='HS256')
        self.invalid_token = jwt.encode(self.invalid_payload, settings.SECRET_KEY, algorithm='HS256')

    def test_valid_token(self):
        request = self.factory.get('/some-url/', HTTP_AUTHORIZATION=f'Bearer {self.valid_token}')
        # Simulate authentication process and assert user is authenticated

    def test_invalid_token(self):
        request = self.factory.get('/some-url/', HTTP_AUTHORIZATION=f'Bearer {self.invalid_token}')
        # Simulate authentication process and assert it raises an exception