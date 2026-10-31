from django.core import mail
from django.test import TestCase, override_settings
from django.urls import set_script_prefix
from rest_framework.test import APIClient
from accounts.models import User
from courses.models import Course


@override_settings(FORCE_SCRIPT_NAME='/skillforge',
                   FRONTEND_URL='https://brollysolutions.in/skillforge',
                   EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
                   PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class SubpathDeploymentTests(TestCase):
    def setUp(self):
        # Django's test Client bypasses the WSGI entry point that sets this prefix.
        set_script_prefix('/skillforge/')
        self.trainer = User.objects.create_user('trainer@subpath.test', 'Password!123', role='trainer')
        self.api = APIClient()

    def tearDown(self):
        set_script_prefix('/')

    def test_paginated_links_keep_external_prefix(self):
        Course.objects.create(title='Python', trainer=self.trainer)
        Course.objects.create(title='GenAI', trainer=self.trainer)
        self.api.force_authenticate(self.trainer)
        response = self.api.get('/api/courses/?page_size=1', secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['next'].startswith('https://testserver/skillforge/api/courses/'), response.data)

    def test_admin_redirect_keeps_prefix(self):
        response = self.api.get('/django-admin/', secure=True)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].startswith('/skillforge/django-admin/login/'), response['Location'])

    def test_invitation_and_reset_links_use_deployed_path(self):
        self.api.force_authenticate(self.trainer)
        response = self.api.post('/api/admin/students/invite/', {'name': 'Student', 'email': 'learner@subpath.test'})
        self.assertEqual(response.status_code, 201)
        self.assertIn('https://brollysolutions.in/skillforge/accept-invitation?token=', mail.outbox[-1].body)
        self.api.force_authenticate(None)
        response = self.api.post('/api/auth/password-reset/', {'email': self.trainer.email})
        self.assertEqual(response.status_code, 200)
        self.assertIn('https://brollysolutions.in/skillforge/reset-password?uid=', mail.outbox[-1].body)

    def test_api_health_under_proxy_stripped_path(self):
        response = self.api.get('/api/health/', secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['service'], 'SkillForge AI')
        self.assertEqual(self.api.get('/api/not-an-endpoint/', secure=True).status_code, 404)
