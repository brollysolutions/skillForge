from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from accounts.models import User


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
                   EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class DirectStudentAccessTests(TestCase):
    def setUp(self):
        cache.clear()
        self.trainer = User.objects.create_user('trainer@access.test', name='Trainer', role='trainer')
        self.api = APIClient()
        self.api.force_authenticate(self.trainer)

    def grant(self):
        response = self.api.post('/api/admin/students/', {'name':'Student','email':'LEARNER@ACCESS.TEST','role':'trainer'})
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def test_direct_access_sends_no_mail_and_allows_email_only_login(self):
        data = self.grant()
        user = User.objects.get(pk=data['student']['id'])
        self.assertEqual(user.email, 'learner@access.test')
        self.assertEqual(user.role, 'student')
        self.assertFalse(user.has_usable_password())
        self.assertNotIn('initial_password', data)
        self.assertEqual(len(mail.outbox), 0)
        self.api.force_authenticate(None)
        login = self.api.post('/api/auth/login/', {'email':'LEARNER@ACCESS.TEST'})
        self.assertEqual(login.status_code, 200, login.data)
        self.api.credentials(HTTP_AUTHORIZATION='Bearer '+login.data['access'])
        self.assertEqual(self.api.get('/api/student/dashboard/').status_code, 200)

    def test_duplicate_email_does_not_change_account(self):
        data = self.grant()
        response = self.api.post('/api/admin/students/', {'name':'Imposter','email':'learner@access.test'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(User.objects.get(pk=data['student']['id']).name, 'Student')

    def test_student_and_anonymous_cannot_grant_access(self):
        student = User.objects.create_user('student@access.test', name='Student', trainer=self.trainer)
        self.api.force_authenticate(student)
        self.assertEqual(self.api.post('/api/admin/students/', {'name':'Other','email':'other@access.test'}).status_code, 403)
        self.api.force_authenticate(None)
        self.assertEqual(self.api.post('/api/admin/students/', {'name':'Other','email':'other@access.test'}).status_code, 401)

    def test_deactivation_revokes_old_sessions_even_after_reactivation(self):
        data = self.grant()
        self.api.force_authenticate(None)
        old = self.api.post('/api/auth/login/', {'email':data['student']['email']}).data
        self.api.force_authenticate(self.trainer)
        url = f"/api/admin/students/{data['student']['id']}/"
        self.assertEqual(self.api.patch(url, {'is_active':False}).status_code, 200)
        self.api.force_authenticate(None)
        self.assertEqual(self.api.post('/api/auth/login/', {'email':data['student']['email']}).status_code, 401)
        self.api.force_authenticate(self.trainer)
        self.api.patch(url, {'is_active':True})
        self.api.force_authenticate(None)
        self.api.credentials(HTTP_AUTHORIZATION='Bearer '+old['access'])
        self.assertEqual(self.api.get('/api/auth/profile/').status_code, 401)
        self.api.credentials()
        self.assertEqual(self.api.post('/api/auth/token/refresh/', {'refresh':old['refresh']}).status_code, 401)

    def test_unknown_email_rejected_and_legacy_mail_endpoints_removed(self):
        self.api.force_authenticate(None)
        self.assertEqual(self.api.post('/api/auth/login/', {'email':'unknown@access.test'}).status_code, 401)
        for path in ['password-reset/', 'password-reset/confirm/', 'invitations/accept/', 'change-password/']:
            self.assertEqual(self.api.post('/api/auth/'+path, {}).status_code, 404)
        self.assertEqual(len(mail.outbox), 0)
