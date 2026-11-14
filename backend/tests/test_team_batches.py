from datetime import timedelta
from unittest.mock import patch
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from accounts.models import User
from courses.models import Course, Batch, BatchMembership, CourseEnrollment
from assignments.models import Assignment, AssignmentAccess


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class TeamBatchTests(TestCase):
    def setUp(self):
        cache.clear()
        self.admin = User.objects.create_user('admin@test.com', role='admin', name='Admin')
        self.sales = User.objects.create_user('sales@test.com', role='sales', name='Sales')
        self.trainer = User.objects.create_user('trainer@test.com', role='trainer', name='Trainer')
        self.other = User.objects.create_user('other@test.com', role='trainer', name='Other')
        self.student = User.objects.create_user('learner@test.com', name='Learner')
        self.course = Course.objects.create(trainer=self.other, title='Python')
        self.batch = Batch.objects.create(course=self.course, trainer=self.trainer, title='Morning')
        self.api = APIClient()

    def as_user(self, user):
        self.api.force_authenticate(user)

    def draft(self, **changes):
        payload = {'title':'Double the input', 'course':self.course.pk, 'batch':self.batch.pk,
            'deadline':(timezone.now()+timedelta(days=1)).isoformat(),
            'questions':[{'title':'Double', 'type':'coding', 'prompt':'Read a number and print twice its value.',
                'marks':10, 'test_cases':[{'input':'3', 'expected_output':'6', 'is_hidden':False, 'weight':1}]}]}
        payload.update(changes)
        self.as_user(self.trainer)
        return self.api.post('/api/assignments/', payload, format='json')

    def test_admin_and_sales_permissions(self):
        self.as_user(self.admin)
        self.assertEqual(self.api.post('/api/staff/', {'name':'Sales 2','email':'sales2@test.com','role':'sales'}).status_code, 201)
        self.as_user(self.sales)
        self.assertEqual(self.api.post('/api/staff/', {'name':'Trainer 2','email':'trainer2@test.com','role':'trainer'}).status_code, 201)
        for role in ['sales', 'admin', 'student']:
            self.assertEqual(self.api.post('/api/staff/', {'name':'Bad','email':role+'x@test.com','role':role}).status_code, 400)
        self.assertEqual(self.api.patch(f'/api/staff/{self.admin.pk}/', {'is_active':False}).status_code, 404)
        self.assertEqual(self.api.post('/api/assignments/', {}).status_code, 403)
        self.assertEqual(self.api.post('/api/ai/generate-assignment/', {}).status_code, 403)
        self.as_user(self.trainer)
        self.assertEqual(self.api.get('/api/staff/').status_code, 403)
        self.as_user(self.student)
        self.assertEqual(self.api.get('/api/batches/').status_code, 403)
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user('secondadmin@test.com', role='admin')

    def test_sales_places_students_and_trainers_on_course(self):
        self.as_user(self.sales)
        response = self.api.post('/api/courses/', {'title':'New course', 'trainer':self.trainer.pk}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        response = self.api.post('/api/batches/', {'title':'Evening', 'course':response.data['id'], 'trainer':self.trainer.pk}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        response = self.api.post(f'/api/batches/{self.batch.pk}/members/', {'student_ids':[self.student.pk]}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(CourseEnrollment.objects.filter(student=self.student, course=self.course).exists())
        self.as_user(self.trainer)
        self.assertEqual(self.api.get('/api/admin/students/').data['count'], 1)
        self.assertEqual(self.api.get('/api/courses/').data['count'], 2)
        self.as_user(self.other)
        self.assertEqual(self.api.get(f'/api/batches/{self.batch.pk}/').status_code, 404)
        self.assertEqual(self.api.get('/api/admin/students/').data['count'], 0)

    @patch('code_execution.service.run_code')
    def test_batch_publish_grade_release_and_scoped_analytics(self, run):
        BatchMembership.objects.create(batch=self.batch, student=self.student)
        outsider = User.objects.create_user('outsider@test.com', name='Outsider')
        response = self.draft()
        self.assertEqual(response.status_code, 201, response.data)
        assignment = response.data['id']
        question = response.data['questions'][0]['id']
        self.assertEqual(self.api.post(f'/api/assignments/{assignment}/publish/').status_code, 200)
        self.assertTrue(AssignmentAccess.objects.filter(assignment_id=assignment, student=self.student).exists())
        self.assertFalse(AssignmentAccess.objects.filter(assignment_id=assignment, student=outsider).exists())
        self.as_user(self.student)
        response = self.api.post(f'/api/assignments/{assignment}/start/')
        self.assertEqual(response.status_code, 201, response.data)
        submission = response.data['id']
        run.return_value = {'accepted':False, 'status':'Wrong Answer', 'stdout':'5', 'stderr':''}
        response = self.api.post(f'/api/submissions/{submission}/submit/', {'answers':{str(question):'print(5)'}}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIsNone(response.data['score'])
        self.as_user(self.sales)
        self.assertEqual(self.api.post(f'/api/submissions/{submission}/review/', {}).status_code, 403)
        data = self.api.get(f'/api/analytics/overview/?batch={self.batch.pk}').data
        self.assertEqual(data['metrics']['coding_tests_total'], 1)
        self.assertEqual(data['metrics']['coding_tests_passed'], 0)
        self.assertEqual(data['student_summary'][0]['id'], self.student.pk)
        self.as_user(self.other)
        self.assertEqual(self.api.get(f'/api/submissions/{submission}/').status_code, 404)
        self.as_user(self.trainer)
        self.api.post(f'/api/assignments/{assignment}/close/')
        self.assertEqual(self.api.post(f'/api/assignments/{assignment}/release-results/').status_code, 200)
        self.as_user(self.student)
        response = self.api.get(f'/api/submissions/{submission}/')
        sample = response.data['responses'][0]['execution']['samples'][0]
        self.assertEqual(sample['expected_output'], '6')
        self.assertEqual(sample['stdout'], '5')
        self.assertFalse(sample['accepted'])
        self.assertEqual(self.api.get('/api/student/dashboard/').data['metrics']['coding_tests_total'], 1)
        self.assertEqual(self.api.get('/api/student/learning-path/').status_code, 200)
        self.assertEqual(self.api.get('/api/leaderboard/').status_code, 200)

    def test_deadline_and_batch_isolation_and_question_limit(self):
        self.assertEqual(self.draft(deadline=None).status_code, 400)
        foreign = Batch.objects.create(course=self.course, trainer=self.other, title='Other batch')
        self.assertEqual(self.draft(batch=foreign.pk).status_code, 400)
        response = self.draft(deadline=(timezone.now()-timedelta(days=1)).isoformat())
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.api.post(f"/api/assignments/{response.data['id']}/publish/").status_code, 400)
        q = {'title':'One', 'prompt':'Write a response.', 'marks':10, 'type':'short_answer', 'rubric':'Clear response'}
        self.assertEqual(self.draft(questions=[q, {**q,'title':'Two'}]).status_code, 201)
        self.assertEqual(self.draft(questions=[{**q, 'title':f'Question {i}'} for i in range(11)]).status_code, 400)
        self.assertEqual(self.api.post('/api/ai/generate-assignment/', {'number_of_questions':2}, format='json').status_code, 400)

    def test_upload_imports_one_question_and_rejects_bad_files(self):
        self.as_user(self.trainer)
        response = self.api.post('/api/assignments/import-question/', {'file':SimpleUploadedFile('task.txt', b'Double the input.')})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['prompt'], 'Double the input.')
        response = self.api.post('/api/assignments/import-question/', {'file':SimpleUploadedFile('task.exe', b'bad')})
        self.assertEqual(response.status_code, 400)
        self.as_user(self.sales)
        self.assertEqual(self.api.post('/api/assignments/import-question/', {}).status_code, 403)

    def test_course_enrollment_rejects_malformed_ids_without_server_errors(self):
        self.as_user(self.sales)
        for ids in [['not-an-id'], [{}], [None], [True], [1.5]]:
            with self.subTest(ids=ids):
                response = self.api.post(f'/api/courses/{self.course.pk}/enrollments/',
                                         {'student_ids': ids}, format='json')
                self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(CourseEnrollment.objects.exists())

    def test_output_prediction_compares_case_and_internal_spacing(self):
        from assignments.models import Question
        from submissions.models import Submission, QuestionResponse
        from submissions.services import evaluate_response
        assignment = Assignment.objects.create(trainer=self.trainer, course=self.course, title='Predict output')
        question = Question.objects.create(assignment=assignment, type='output_prediction', title='Output',
            prompt='Predict the output.', marks=10, correct_answer=['Hello  World'])
        submission = Submission.objects.create(assignment=assignment, student=self.student, attempt=1,
            expires_at=timezone.now()+timedelta(hours=1))
        response = QuestionResponse(submission=submission, question=question, answer='hello world')
        evaluate_response(response)
        self.assertEqual(response.score, 0)
        self.assertFalse(response.execution['samples'][0]['accepted'])
        response.answer = 'Hello  World\n'
        evaluate_response(response)
        self.assertEqual(response.score, 10)
        self.assertTrue(response.execution['samples'][0]['accepted'])
