from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from accounts.models import User
from core.models import AuditLog


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
                   EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class DirectStudentAccessTests(TestCase):
    def setUp(self):
        cache.clear()
        self.trainer = User.objects.create_user('trainer@access.test','StrongPassword!123',name='Trainer',role='trainer')
        self.api = APIClient()
        self.api.force_authenticate(self.trainer)

    def grant(self):
        response = self.api.post('/api/admin/students/',{'name':'Student','email':'LEARNER@ACCESS.TEST','role':'trainer'})
        self.assertEqual(response.status_code,201,response.data)
        return response.data

    def test_direct_access_sends_no_mail_and_allows_login(self):
        data = self.grant()
        user = User.objects.get(pk=data['student']['id'])
        self.assertEqual(user.email,'learner@access.test')
        self.assertEqual(user.role,'student')
        self.assertEqual(user.trainer_id,self.trainer.pk)
        self.assertTrue(user.is_active)
        self.assertTrue(user.check_password(data['initial_password']))
        self.assertNotEqual(user.password,data['initial_password'])
        self.assertEqual(len(mail.outbox),0)
        self.assertNotIn(data['initial_password'],str(list(AuditLog.objects.values())))
        self.assertNotIn('initial_password',str(self.api.get('/api/admin/students/').data))
        self.api.force_authenticate(None)
        login = self.api.post('/api/auth/login/',{'email':user.email,'password':data['initial_password']})
        self.assertEqual(login.status_code,200,login.data)
        self.api.credentials(HTTP_AUTHORIZATION='Bearer '+login.data['access'])
        dashboard = self.api.get('/api/student/dashboard/')
        self.assertEqual(dashboard.status_code,200,dashboard.data)
        self.assertEqual(dashboard.data['metrics']['assigned_assignments'],0)

    def test_duplicate_case_insensitive_email_does_not_reset_account(self):
        data = self.grant()
        response = self.api.post('/api/admin/students/',{'name':'Imposter','email':'learner@access.test'})
        self.assertEqual(response.status_code,400)
        self.assertTrue(User.objects.get(pk=data['student']['id']).check_password(data['initial_password']))

    def test_student_and_anonymous_cannot_grant_access(self):
        student = User.objects.create_user('student@access.test','Password!123',name='Student',trainer=self.trainer)
        self.api.force_authenticate(student)
        self.assertEqual(self.api.post('/api/admin/students/',{'name':'Other','email':'other@access.test'}).status_code,403)
        self.api.force_authenticate(None)
        self.assertEqual(self.api.post('/api/admin/students/',{'name':'Other','email':'other@access.test'}).status_code,401)

    def test_reset_access_is_private_and_invalidates_old_password_and_access_token(self):
        data = self.grant()
        self.api.force_authenticate(None)
        old = self.api.post('/api/auth/login/',{'email':data['student']['email'],'password':data['initial_password']}).data
        self.api.force_authenticate(self.trainer)
        reset = self.api.post(f"/api/admin/students/{data['student']['id']}/reset-access/")
        self.assertEqual(reset.status_code,200)
        self.assertEqual(reset['Cache-Control'],'no-store')
        self.assertEqual(len(mail.outbox),0)
        self.api.force_authenticate(None)
        self.assertEqual(self.api.post('/api/auth/login/',{'email':data['student']['email'],'password':data['initial_password']}).status_code,401)
        self.api.credentials(HTTP_AUTHORIZATION='Bearer '+old['access'])
        self.assertEqual(self.api.get('/api/auth/profile/').status_code,401)
        self.api.credentials()
        other = User.objects.create_user('othertrainer@access.test','Password!123',name='Other trainer',role='trainer')
        self.api.force_authenticate(other)
        self.assertEqual(self.api.post(f"/api/admin/students/{data['student']['id']}/reset-access/").status_code,404)

    def test_change_password_requires_current_password_and_no_email(self):
        data = self.grant()
        student = User.objects.get(pk=data['student']['id'])
        self.api.force_authenticate(student)
        response = self.api.post('/api/auth/change-password/',{'current_password':'wrong','password':'NewStrongPassword!134'})
        self.assertEqual(response.status_code,400)
        response = self.api.post('/api/auth/change-password/',{'current_password':data['initial_password'],'password':'NewStrongPassword!134'})
        self.assertEqual(response.status_code,200,response.data)
        student.refresh_from_db()
        self.assertTrue(student.check_password('NewStrongPassword!134'))
        self.assertEqual(len(mail.outbox),0)

    def test_email_alone_cannot_authenticate(self):
        data = self.grant()
        self.api.force_authenticate(None)
        self.assertEqual(self.api.post('/api/auth/login/',{'email':data['student']['email']}).status_code,400)
