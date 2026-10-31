import os
from unittest.mock import patch

import httpx
from groq import APIConnectionError, APITimeoutError, AuthenticationError, RateLimitError, NotFoundError
from django.test import TestCase, override_settings

from accounts.models import User
from ai_services.providers import generate_json
from ai_services.schemas import MaterialAnalysis
from core.api import ServiceUnavailable
from core.models import AIUsageLog


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
@patch.dict(os.environ, {'GROQ_API_KEY': 'private-test-key', 'AI_DAILY_LIMIT': '100'})
class ProviderErrorTests(TestCase):
    def setUp(self):
        self.actor = User.objects.create_user('trainer@provider.test', 'password', role='trainer')
        self.request = httpx.Request('POST', 'https://api.groq.com/openai/v1/chat/completions')

    def check_error(self, error, expected, attempts):
        with patch('groq.Groq') as client, patch('ai_services.providers.time.sleep'):
            create = client.return_value.__enter__.return_value.chat.completions.create
            create.side_effect = error
            with self.assertRaisesMessage(ServiceUnavailable, expected) as raised:
                generate_json(self.actor, 'groq', 'material.analysis', MaterialAnalysis, 'Analyze.', {'content': 'PRIVATE_NOTES'})
            self.assertEqual(create.call_count, attempts)
        self.assertEqual(AIUsageLog.objects.count(), attempts)
        for log in AIUsageLog.objects.all():
            self.assertEqual(log.status, 'error')
            self.assertEqual(log.error_type, type(error).__name__)
        for secret in ['PRIVATE_NOTES', 'PRIVATE_PROVIDER_BODY', 'private-test-key']:
            self.assertNotIn(secret, str(raised.exception))
            self.assertNotIn(secret, str(list(AIUsageLog.objects.values())))

    def status_error(self, cls, status):
        return cls('PRIVATE_PROVIDER_BODY', response=httpx.Response(status, request=self.request), body={'message': 'PRIVATE_PROVIDER_BODY'})

    def test_connection_failure_is_not_reported_as_quota(self):
        self.check_error(APIConnectionError(request=self.request), 'cannot connect to Groq', 2)

    def test_timeout_has_specific_message(self):
        self.check_error(APITimeoutError(request=self.request), 'timed out', 2)

    def test_invalid_key_is_not_retried(self):
        self.check_error(self.status_error(AuthenticationError, 401), 'rejected the API key', 1)

    def test_quota_is_not_immediately_retried(self):
        self.check_error(self.status_error(RateLimitError, 429), 'rate or quota limit', 1)

    def test_unavailable_model_is_not_retried(self):
        self.check_error(self.status_error(NotFoundError, 404), 'model or endpoint was not found', 1)
