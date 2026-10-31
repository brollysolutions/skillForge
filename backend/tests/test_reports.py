from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from accounts.models import User
from courses.models import Course, Topic
from assignments.models import Assignment, Question, AssignmentAccess
from submissions.models import Submission, QuestionResponse
from reports.models import PerformanceReport


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class ReportWorkflowTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.trainer=User.objects.create_user('trainer@reports.test','StrongPassword!42',name='Private Trainer',role='trainer')
        self.student=User.objects.create_user('student@reports.test','StrongPassword!42',name='Private Student',trainer=self.trainer)
        self.other=User.objects.create_user('other@reports.test','StrongPassword!42',name='Other Student',trainer=self.trainer)
        self.course=Course.objects.create(trainer=self.trainer,title='Python')
        self.topic=Topic.objects.create(course=self.course,title='Functions')
        self.assignment=Assignment.objects.create(trainer=self.trainer,course=self.course,topic=self.topic,title='Quiz',status='closed',results_released=True,total_marks=10)
        AssignmentAccess.objects.create(student=self.student,assignment=self.assignment)
        self.question=Question.objects.create(assignment=self.assignment,title='Function definition',prompt='Explain def',type='short_answer',marks=10,rubric='Explain function definition.')
        self.submission=Submission.objects.create(student=self.student,assignment=self.assignment,attempt=1,status='evaluated',expires_at=timezone.now(),submitted_at=timezone.now(),score=8,percentage=80)
        QuestionResponse.objects.create(submission=self.submission,question=self.question,answer='Student private answer',score=8,status='evaluated',feedback='Review parameters.')
        self.api=APIClient();self.api.force_authenticate(self.trainer)
        self.narrative={'overall_performance':'Shows a sound foundation.', 'strengths':['Understands functions.'],
                        'weaknesses':['Needs more practice with parameters.'],'coding_analysis':'Insufficient coding evidence.',
                        'progress_analysis':'More assessments are needed to compare progress.',
                        'recommendations':[{'topic_id':self.topic.pk,'assignment_ids':[],'reason':'Revisit parameters.',
                                            'steps':['Review the lesson.','Write a small function.'],'difficulty':'easy'}],
                        'trainer_feedback':'Discuss parameter passing.', 'evidence_submission_ids':[self.submission.pk]}

    @patch('reports.services.generate_json')
    def test_generation_minimizes_data_and_preserves_official_metrics(self,provider):
        provider.return_value=self.narrative
        response=self.api.post(f'/api/reports/generate/{self.student.pk}/')
        self.assertEqual(response.status_code,201,response.data)
        self.assertEqual(response.data['metrics']['average_score'],80)
        self.assertIsNone(response.data['published_at'])
        evidence=str(provider.call_args.args[-1])
        self.assertNotIn(self.student.email,evidence)
        self.assertNotIn(self.student.name,evidence)
        self.assertNotIn('Student private answer',evidence)
        rid=response.data['id']
        self.api.post(f'/api/reports/{rid}/publish/')
        self.api.force_authenticate(self.student)
        path=self.api.get('/api/student/learning-path/').data
        self.assertEqual(path[0]['topic'],'Functions')
        self.assertEqual(path[0]['assignments'],[])

    @patch('reports.services.generate_json')
    def test_unknown_recommendation_is_rejected(self,provider):
        self.narrative['recommendations'][0]['assignment_ids']=[999999]
        provider.return_value=self.narrative
        response=self.api.post(f'/api/reports/generate/{self.student.pk}/')
        self.assertEqual(response.status_code,400)
        self.assertEqual(PerformanceReport.objects.count(),0)

    @patch('reports.services.generate_json')
    def test_fabricated_numeric_prose_is_rejected(self,provider):
        self.narrative['overall_performance']='You scored 99%.'
        provider.return_value=self.narrative
        self.assertEqual(self.api.post(f'/api/reports/generate/{self.student.pk}/').status_code,400)

    @patch('ai_services.providers.generate_json')
    def test_batch_report_uses_aggregates_and_is_trainer_only(self,provider):
        provider.return_value={'overview':'A developing classroom foundation.','strengths':['Function syntax.'],
                               'learning_gaps':['Parameter passing.'],'teaching_recommendations':['Practice small functions.'],
                               'priority_topic_ids':[self.topic.pk]}
        response=self.api.post('/api/reports/batch/')
        self.assertEqual(response.status_code,201,response.data)
        evidence=str(provider.call_args.args[-1])
        self.assertNotIn(self.student.email,evidence)
        self.assertNotIn(self.student.name,evidence)
        self.assertEqual(self.api.get(f"/api/reports/batch/{response.data['id']}/download/").status_code,200)
        self.api.force_authenticate(self.student)
        self.assertEqual(self.api.get('/api/reports/batch/').status_code,403)

    def test_dashboard_and_exports_are_scoped(self):
        self.api.force_authenticate(self.student)
        self.assertEqual(self.api.get('/api/admin/dashboard/').status_code,403)
        self.assertEqual(self.api.get('/api/analytics/export/').status_code,403)
        self.api.force_authenticate(self.trainer)
        self.assertEqual(self.api.get('/api/analytics/export/?format=pdf').status_code,200)
        csv=self.api.get('/api/analytics/export/')
        self.assertEqual(csv.status_code,200)
        self.assertIn(b'Private Student',csv.content)
