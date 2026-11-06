import hashlib
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from accounts.models import User, Invitation
from courses.models import Course, Topic
from assignments.models import Assignment, Question, TestCase as CodingTestCase, AssignmentAccess
from materials.models import StudyMaterial
from submissions.models import Submission, QuestionResponse, Evaluation
from reports.models import PerformanceReport
from core.models import PlatformSettings


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
                   PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
                   REST_FRAMEWORK={'DEFAULT_AUTHENTICATION_CLASSES':['rest_framework_simplejwt.authentication.JWTAuthentication'],
                                   'DEFAULT_PERMISSION_CLASSES':['rest_framework.permissions.IsAuthenticated'],
                                   'DEFAULT_PAGINATION_CLASS':'core.api.Pagination', 'PAGE_SIZE':20,
                                   'EXCEPTION_HANDLER':'core.api.exception_handler'})
class WorkflowTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.trainer = User.objects.create_user('trainer@example.com','TrainerPassword!42',name='Trainer',role='trainer')
        self.other_trainer = User.objects.create_user('trainer2@example.com','TrainerPassword!42',name='Other',role='trainer')
        self.student = User.objects.create_user('student@example.com','StudentPassword!42',name='Ada',trainer=self.trainer)
        self.other = User.objects.create_user('other@example.com','OtherPassword!42',name='Grace',trainer=self.trainer)
        self.course = Course.objects.create(trainer=self.trainer,title='Python')
        self.topic = Topic.objects.create(course=self.course,title='Functions')
        self.assignment = Assignment.objects.create(trainer=self.trainer,course=self.course,topic=self.topic,title='Python quiz',
            status='published',total_marks=10,deadline=timezone.now()+timedelta(days=1))
        self.question = Question.objects.create(assignment=self.assignment,title='Choose the keyword',prompt='Which keyword defines a function?',
            type='mcq',marks=10,options=['def','class'],correct_answer=['def'],explanation='def defines a function.')
        AssignmentAccess.objects.create(assignment=self.assignment,student=self.student)
        self.api = APIClient()

    def login_as(self,user):
        self.api.force_authenticate(user=user)

    def start(self):
        self.login_as(self.student)
        response=self.api.post(f'/api/assignments/{self.assignment.pk}/start/',{},format='json')
        self.assertEqual(response.status_code,201,response.data)
        return response.data['id']

    def complete(self):
        sid=self.start()
        response=self.api.post(f'/api/submissions/{sid}/submit/',{'answers':{str(self.question.pk):'def'}},format='json')
        self.assertEqual(response.status_code,200,response.data)
        return Submission.objects.get(pk=sid)

    def test_login_normalizes_email_refresh_logout(self):
        response=self.api.post('/api/auth/login/',{'email':'TRAINER@EXAMPLE.COM','password':'TrainerPassword!42'})
        self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(response.data['user']['role'],'trainer')
        refresh=response.data['refresh']
        self.api.credentials(HTTP_AUTHORIZATION='Bearer '+response.data['access'])
        self.assertEqual(self.api.get('/api/auth/profile/').status_code,200)
        self.assertEqual(self.api.post('/api/auth/logout/',{'refresh':refresh}).status_code,204)
        self.assertEqual(self.api.post('/api/auth/token/refresh/',{'refresh':refresh}).status_code,401)

    def test_anonymous_and_student_admin_access_denied(self):
        self.assertEqual(self.api.get('/api/courses/').status_code,401)
        self.login_as(self.student)
        for url in ['/api/courses/','/api/topics/','/api/materials/','/api/admin/students/','/api/settings/']:
            self.assertEqual(self.api.get(url).status_code,403,url)
        self.assertEqual(self.api.post('/api/assignments/',{}).status_code,403)

    def test_legacy_invitation_cannot_activate_account(self):
        Invitation.objects.create(trainer=self.trainer, email='expired@example.com', name='Expired',
            token_hash=hashlib.sha256(b'token').hexdigest(), expires_at=timezone.now()+timedelta(days=1))
        self.assertEqual(self.api.post('/api/auth/invitations/accept/', {'token':'token'}).status_code, 404)
        self.assertFalse(User.objects.filter(email='expired@example.com').exists())

    def test_deactivation_revokes_access(self):
        response=self.api.post('/api/auth/login/',{'email':self.student.email,'password':'StudentPassword!42'})
        self.student.is_active=False;self.student.save()
        self.api.credentials(HTTP_AUTHORIZATION='Bearer '+response.data['access'])
        self.assertEqual(self.api.get('/api/auth/profile/').status_code,401)

    def test_course_ownership_and_dependency_protection(self):
        self.login_as(self.trainer)
        response=self.api.post('/api/courses/',{'title':'GenAI'})
        self.assertEqual(response.status_code,201)
        self.assertEqual(self.api.delete(f'/api/courses/{self.course.pk}/').status_code,409)
        self.login_as(self.other_trainer)
        self.assertEqual(self.api.get(f'/api/courses/{self.course.pk}/').status_code,404)
        self.assertEqual(self.api.post('/api/topics/',{'course':self.course.pk,'title':'Stolen'}).status_code,400)

    def test_material_manual_and_upload_validation(self):
        self.login_as(self.trainer)
        response=self.api.post('/api/materials/text/',{'course':self.course.pk,'title':'Functions','notes':'A function uses def.'})
        self.assertEqual(response.status_code,201,response.data)
        self.assertEqual(response.data['extracted_text'],'A function uses def.')
        bad=SimpleUploadedFile('attack.exe',b'fake',content_type='application/pdf')
        self.assertEqual(self.api.post('/api/materials/upload/',{'course':self.course.pk,'title':'Bad','file':bad},format='multipart').status_code,400)
        fake=SimpleUploadedFile('fake.pdf',b'not a PDF')
        self.assertEqual(self.api.post('/api/materials/upload/',{'course':self.course.pk,'title':'Bad','file':fake},format='multipart').status_code,400)

    def test_valid_text_upload_and_private_download(self):
        from pathlib import Path
        import tempfile
        # Use the test workspace's existing temp directory to avoid OS-specific tempfile ACLs.
        with override_settings(MEDIA_ROOT=Path(__file__).resolve().parents[2]/'.task-temp'/'test-media'):
            self.login_as(self.trainer)
            file=SimpleUploadedFile('lesson.txt',b'Functions accept parameters and return values.')
            response=self.api.post('/api/materials/upload/',{'course':self.course.pk,'title':'Notes','file':file},format='multipart')
            self.assertEqual(response.status_code,201,response.data)
            self.assertNotIn('file',response.data)
            self.login_as(self.student)
            self.assertEqual(self.api.get(f"/api/materials/{response.data['id']}/download/").status_code,403)

    def test_student_visibility_and_answer_key_secrecy(self):
        self.login_as(self.other)
        self.assertEqual(self.api.get('/api/assignments/').data['count'],0)
        self.assertEqual(self.api.get(f'/api/assignments/{self.assignment.pk}/').status_code,404)
        self.login_as(self.student)
        self.assertEqual(self.api.get(f'/api/assignments/{self.assignment.pk}/').data['questions'],[])
        self.start()
        response=self.api.get(f'/api/assignments/{self.assignment.pk}/')
        question=response.data['questions'][0]
        self.assertNotIn('correct_answer',question)
        self.assertNotIn('explanation',question)

    def test_hidden_tests_never_serialized(self):
        self.question.type='coding';self.question.save()
        CodingTestCase.objects.create(question=self.question,input='PUBLIC',expected_output='OK',is_hidden=False)
        CodingTestCase.objects.create(question=self.question,input='HIDDEN_SECRET',expected_output='HIDDEN_ANSWER',is_hidden=True)
        self.start()
        response=self.api.get(f'/api/assignments/{self.assignment.pk}/')
        self.assertNotIn('HIDDEN_SECRET',str(response.data))
        self.assertNotIn('HIDDEN_ANSWER',str(response.data))
        self.assertIn('PUBLIC',str(response.data))

    def test_submit_grade_release_and_analytics(self):
        sub=self.complete()
        self.assertEqual(sub.score,Decimal('10'))
        self.assertEqual(sub.percentage,Decimal('100'))
        self.assertEqual(self.api.get(f'/api/submissions/{sub.pk}/').data['score'],None)
        self.assertEqual(self.api.get('/api/student/dashboard/').data['metrics']['average_score'],0)
        self.login_as(self.trainer)
        self.assertEqual(self.api.post(f'/api/assignments/{self.assignment.pk}/release-results/').status_code,400)
        self.assertEqual(self.api.post(f'/api/assignments/{self.assignment.pk}/close/').status_code,200)
        self.assertEqual(self.api.post(f'/api/assignments/{self.assignment.pk}/release-results/').status_code,200)
        self.login_as(self.student)
        self.assertEqual(float(self.api.get(f'/api/submissions/{sub.pk}/').data['score']),10)
        metrics=self.api.get('/api/student/dashboard/').data['metrics']
        self.assertEqual(metrics['average_score'],100)
        self.assertEqual(metrics['completion_percentage'],100)

    def test_duplicate_submission_is_idempotent_and_attempts_limited(self):
        sub=self.complete()
        response=self.api.post(f'/api/submissions/{sub.pk}/submit/',{},format='json')
        self.assertEqual(response.status_code,200)
        self.assertEqual(Submission.objects.count(),1)
        self.assertEqual(self.api.post(f'/api/assignments/{self.assignment.pk}/start/').status_code,400)

    def test_deadline_and_expired_attempt_use_saved_answers_only(self):
        sid=self.start()
        self.api.post(f'/api/submissions/{sid}/save/',{'answers':{str(self.question.pk):'def'}},format='json')
        Submission.objects.filter(pk=sid).update(expires_at=timezone.now()-timedelta(seconds=1))
        self.assertEqual(self.api.post(f'/api/submissions/{sid}/save/',{'answers':{str(self.question.pk):'class'}},format='json').status_code,400)
        self.assertEqual(self.api.post(f'/api/submissions/{sid}/submit/',{},format='json').status_code,200)
        self.assertEqual(Submission.objects.get(pk=sid).score,10)
        self.assignment.deadline=timezone.now()-timedelta(days=1);self.assignment.save()
        self.assertEqual(self.api.post(f'/api/assignments/{self.assignment.pk}/start/').status_code,400)

    def test_submission_idor_and_cross_assignment_answers(self):
        sid=self.start()
        self.assertEqual(self.api.post(f'/api/submissions/{sid}/save/',{'answers':{'999999':'def'}},format='json').status_code,400)
        self.login_as(self.other)
        self.assertEqual(self.api.get(f'/api/submissions/{sid}/').status_code,404)
        self.assertEqual(self.api.post(f'/api/submissions/{sid}/submit/').status_code,404)

    def test_revoked_access_cannot_continue(self):
        sid=self.start()
        AssignmentAccess.objects.filter(student=self.student).update(is_active=False)
        self.assertEqual(self.api.post(f'/api/submissions/{sid}/submit/').status_code,403)

    def test_manual_review_and_audit(self):
        self.question.type='descriptive';self.question.rubric='Explain parameters and return values.';self.question.save()
        sid=self.start()
        self.api.post(f'/api/submissions/{sid}/submit/',{'answers':{str(self.question.pk):'A function accepts inputs.'}},format='json')
        sub=Submission.objects.get(pk=sid);self.assertEqual(sub.status,'submitted')
        response=sub.responses.get()
        self.login_as(self.trainer)
        self.assertEqual(self.api.post(f'/api/submissions/{sid}/review/',{'response_id':response.pk,'score':11,'feedback':'Too high'}).status_code,400)
        reviewed=self.api.post(f'/api/submissions/{sid}/review/',{'response_id':response.pk,'score':7,'feedback':'Explain returns too.'})
        self.assertEqual(reviewed.status_code,200,reviewed.data)
        sub.refresh_from_db();self.assertEqual(sub.status,'evaluated');self.assertEqual(sub.score,7)
        self.assertEqual(Evaluation.objects.count(),1)

    def test_ai_schema_rejects_invalid_questions(self):
        from ai_services.schemas import GeneratedAssignment
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            GeneratedAssignment.model_validate({'description':'Invalid','questions':[{'type':'mcq','title':'Bad','prompt':'Question','difficulty':'easy','marks':5,'options':['A','B'],'correct_answer':['C']}]})

    @patch('ai_services.workflows.generate_json')
    def test_ai_generation_creates_draft_never_publishes(self,generate):
        generate.return_value={'description':'Functions quiz','questions':[{'type':'mcq','title':'Keyword','prompt':'Define a function with which keyword?',
            'difficulty':'easy','marks':10,'options':['def','class'],'correct_answer':['def'],'explanation':'The def keyword.'}]}
        self.login_as(self.trainer)
        response=self.api.post('/api/ai/generate-assignment/',{'title':'Generated quiz','course':self.course.pk,'topic':self.topic.pk,
            'number_of_questions':1,'question_types':['mcq'],'difficulty':'easy','total_marks':10},format='json')
        self.assertEqual(response.status_code,201,response.data)
        self.assertEqual(response.data['status'],'draft')
        self.assertEqual(response.data['assigned_count'],0)

    @patch('code_execution.service.run_code')
    def test_coding_score_and_hidden_output_redaction(self,run):
        self.question.type='coding';self.question.save()
        CodingTestCase.objects.create(question=self.question,input='1',expected_output='1',is_hidden=False)
        CodingTestCase.objects.create(question=self.question,input='secret',expected_output='secret',is_hidden=True)
        run.side_effect=[{'accepted':True,'status':'Accepted','stdout':'1','stderr':'','time':'0.01','memory':100},
                         {'accepted':False,'status':'Wrong Answer','stdout':'HIDDEN LEAK','stderr':'secret','time':'0.01','memory':100}]
        sid=self.start()
        response=self.api.post(f'/api/submissions/{sid}/submit/',{'answers':{str(self.question.pk):'print(input())'}},format='json')
        self.assertEqual(response.status_code,200,response.data)
        sub=Submission.objects.get(pk=sid);self.assertEqual(sub.score,5)
        self.assertNotIn('HIDDEN LEAK',str(sub.responses.get().execution))
        self.assertNotIn('secret',str(sub.responses.get().execution))

    @patch('code_execution.service.run_code')
    def test_execution_failure_preserves_retryable_attempt(self,run):
        from core.api import ServiceUnavailable
        self.question.type='coding';self.question.save()
        CodingTestCase.objects.create(question=self.question,input='',expected_output='',is_hidden=False)
        run.side_effect=ServiceUnavailable()
        sid=self.start()
        self.assertEqual(self.api.post(f'/api/submissions/{sid}/submit/',{'answers':{str(self.question.pk):'print(1)'}},format='json').status_code,503)
        self.assertEqual(Submission.objects.get(pk=sid).status,'in_progress')

    def test_report_publication_and_student_isolation(self):
        report=PerformanceReport.objects.create(trainer=self.trainer,student=self.student,metrics={'average_score':100},narrative={'overall_performance':'Strong evidence','trainer_feedback':'Private trainer note'})
        self.login_as(self.student)
        self.assertEqual(self.api.get(f'/api/reports/{report.pk}/').status_code,404)
        self.login_as(self.trainer)
        self.assertEqual(self.api.post(f'/api/reports/{report.pk}/publish/').status_code,200)
        self.login_as(self.student)
        data=self.api.get(f'/api/reports/{report.pk}/').data
        self.assertNotIn('trainer_feedback',data['narrative'])
        self.assertEqual(self.api.get(f'/api/reports/{report.pk}/download/').status_code,200)
        self.login_as(self.other)
        self.assertEqual(self.api.get(f'/api/reports/{report.pk}/').status_code,404)

    def test_leaderboard_counts_best_result_once(self):
        sub=self.complete()
        self.assignment.results_released=True;self.assignment.attempts_allowed=2;self.assignment.save()
        Submission.objects.create(assignment=self.assignment,student=self.student,attempt=2,status='evaluated',expires_at=timezone.now(),score=5,percentage=50,submitted_at=timezone.now())
        PlatformSettings.objects.create(trainer=self.trainer,leaderboard_enabled=True)
        ranking=self.api.get('/api/leaderboard/').data['rankings'][0]
        self.assertEqual(ranking['points'],10)
        self.assertEqual(ranking['completed'],1)
        self.assertNotIn('email',ranking)
