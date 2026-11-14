from datetime import timedelta
from unittest.mock import patch
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from accounts.models import User
from assignments.models import Assignment, AssignmentAccess, Question, TestCase as OutputCheck
from courses.models import Course
from core.api import ServiceUnavailable
from submissions.models import Submission


class CodingCompletionTests(TestCase):
    def setUp(self):
        cache.clear()
        self.trainer = User.objects.create_user('trainer@completion.test', name='Trainer', role='trainer')
        self.student = User.objects.create_user('student@completion.test', name='Student', trainer=self.trainer)
        self.other = User.objects.create_user('other@completion.test', name='Other', trainer=self.trainer)
        self.course = Course.objects.create(trainer=self.trainer, title='Python')
        self.assignment = Assignment.objects.create(trainer=self.trainer, course=self.course, title='Salary increment',
                                                    status='published', total_marks=10)
        self.question = Question.objects.create(assignment=self.assignment, type='coding', title='Increase salaries',
                                                prompt='Increase every salary by 10%.', marks=10)
        self.case = OutputCheck.objects.create(question=self.question, input='1\nAsha 20000',
                                              expected_output='Asha 22000.00', is_hidden=False)
        AssignmentAccess.objects.create(assignment=self.assignment, student=self.student)
        self.api = APIClient()
        self.api.force_authenticate(self.student)
        response = self.api.post(f'/api/assignments/{self.assignment.pk}/start/')
        self.assertEqual(response.status_code, 201, response.data)
        self.sid = response.data['id']
        self.url = f'/api/submissions/{self.sid}/check-complete/'
        self.code = 'for _ in range(int(input())):\n    name, salary = input().split()\n    print(f"{name} {int(salary) * 1.1:.2f}")'

    def check(self, code=None):
        return self.api.post(self.url, {'answers': {str(self.question.pk): self.code if code is None else code}}, format='json')

    def result(self, accepted=True):
        return {'accepted': accepted, 'status': 'Accepted' if accepted else 'Wrong Answer',
                'stdout': 'Asha 22000.00\n' if accepted else 'Asha 20000\n', 'stderr': '', 'compile_output': ''}

    @patch('code_execution.service.run_code')
    def test_mismatch_can_be_edited_and_success_is_persisted_without_reexecution(self, run):
        run.side_effect = [self.result(False), self.result()]
        failed = self.check('print("Asha 20000")')
        self.assertEqual(failed.status_code, 200, failed.data)
        self.assertFalse(failed.data['completed'])
        self.assertEqual(failed.data['results'][0]['expected_output'], self.case.expected_output)
        attempt = Submission.objects.get(pk=self.sid)
        self.assertEqual(attempt.status, 'in_progress')
        self.assertIsNone(attempt.submitted_at)
        self.assertEqual(attempt.responses.get().answer, 'print("Asha 20000")')
        passed = self.check()
        self.assertTrue(passed.data['completed'])
        self.assertTrue(passed.data['submission']['task_completed'])
        # Completion is visible immediately, while official marks still await release.
        self.assertIsNone(passed.data['submission']['score'])
        self.assertNotIn('explanation', passed.data['submission']['responses'][0])
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, 'evaluated')
        self.assertEqual(attempt.score, 10)
        self.assertEqual(attempt.responses.get().answer, self.code)
        self.assertIsNotNone(attempt.submitted_at)
        self.assertTrue(self.check().data['completed'])
        self.assertEqual(run.call_count, 2)
        run.assert_called_with(self.code, self.case.input, self.case.expected_output)
        assignment = self.api.get(f'/api/assignments/{self.assignment.pk}/').data
        self.assertEqual(assignment['student_status'], 'completed')
        self.assertTrue(self.api.get(f'/api/submissions/{self.sid}/').data['task_completed'])

    @patch('code_execution.service.run_code')
    def test_runner_failure_preserves_code_and_allows_retry(self, run):
        run.side_effect = ServiceUnavailable()
        self.assertEqual(self.check().status_code, 503)
        attempt = Submission.objects.get(pk=self.sid)
        self.assertEqual(attempt.status, 'in_progress')
        self.assertEqual(attempt.responses.get().answer, self.code)
        run.side_effect = None
        run.return_value = self.result()
        self.assertTrue(self.check().data['completed'])

    @patch('code_execution.service.run_code')
    def test_empty_code_and_runtime_errors_do_not_complete(self, run):
        empty = self.check('')
        self.assertEqual(empty.status_code, 200)
        self.assertFalse(empty.data['completed'])
        run.assert_not_called()
        run.return_value = {**self.result(False), 'status': 'Runtime Error', 'stdout': '', 'stderr': 'ValueError'}
        response = self.check()
        self.assertFalse(response.data['completed'])
        self.assertEqual(response.data['results'][0]['stderr'], 'ValueError')
        self.assertEqual(Submission.objects.get(pk=self.sid).status, 'in_progress')

    @patch('code_execution.service.run_code')
    def test_access_deadline_and_expired_attempt_are_enforced(self, run):
        self.api.force_authenticate(self.other)
        self.assertEqual(self.check().status_code, 404)
        self.api.force_authenticate(self.trainer)
        self.assertEqual(self.check().status_code, 403)
        self.api.force_authenticate(self.student)
        AssignmentAccess.objects.filter(student=self.student).update(is_active=False)
        self.assertEqual(self.check().status_code, 403)
        AssignmentAccess.objects.filter(student=self.student).update(is_active=True)
        self.assignment.deadline = timezone.now() - timedelta(seconds=1)
        self.assignment.save()
        self.assertEqual(self.check().status_code, 400)
        self.assignment.deadline = None
        self.assignment.save()
        Submission.objects.filter(pk=self.sid).update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.check().status_code, 400)
        run.assert_not_called()

    @patch('code_execution.service.run_code')
    def test_all_checks_must_pass_and_hidden_output_is_not_returned(self, run):
        OutputCheck.objects.create(question=self.question, input='secret', expected_output='secret', is_hidden=True)
        run.side_effect = [self.result(), {**self.result(False), 'stdout': 'secret', 'stderr': 'secret'}]
        response = self.check()
        self.assertFalse(response.data['completed'])
        self.assertEqual(len(response.data['results']), 1)
        self.assertNotIn('secret', str(response.data))

    @patch('code_execution.views.run_code')
    def test_custom_run_does_not_complete_or_claim_output_match(self, run):
        run.return_value = self.result()
        response = self.api.post('/api/code/run/', {'submission_id': self.sid, 'question_id': self.question.pk,
                                                 'code': self.code, 'input': self.case.input}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('expected_output', response.data['results'][0])
        self.assertEqual(Submission.objects.get(pk=self.sid).status, 'in_progress')

    def test_trainer_input_and_expected_output_preserve_significant_whitespace(self):
        self.api.force_authenticate(self.trainer)
        response = self.api.post('/api/assignments/', {'title': 'Whitespace task', 'course': self.course.pk,
            'questions': [{'type': 'coding', 'title': 'Print indented text', 'prompt': 'Preserve indentation.', 'marks': 10,
                           'test_cases': [{'input': '\n  text\n', 'expected_output': '\n  text\n', 'is_hidden': False}]}]}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        case = response.data['questions'][0]['test_cases'][0]
        self.assertEqual(case['input'], '\n  text\n')
        self.assertEqual(case['expected_output'], '\n  text\n')

    def test_non_coding_task_cannot_use_completion_endpoint(self):
        self.question.type = 'descriptive'
        self.question.save()
        self.assertEqual(self.check().status_code, 400)
