from django.conf import settings
from django.db import models
from core.models import Timestamped


class Submission(Timestamped):
    assignment = models.ForeignKey('assignments.Assignment', on_delete=models.PROTECT, related_name='submissions')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='submissions')
    attempt = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=20, default='in_progress', choices=[(x,x) for x in ['in_progress','grading','submitted','evaluated']])
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    submitted_at = models.DateTimeField(null=True)
    score = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    duration_seconds = models.PositiveIntegerField(default=0)

    @property
    def task_completed(self):
        if self.status != 'evaluated':
            return False
        responses = list(self.responses.all())
        return bool(responses) and all(response.question_completed for response in responses)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['assignment','student','attempt'], name='unique_attempt')]
        indexes = [models.Index(fields=['student', 'status']), models.Index(fields=['assignment', 'status'])]


class QuestionResponse(Timestamped):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='responses')
    question = models.ForeignKey('assignments.Question', on_delete=models.PROTECT)
    answer = models.JSONField(default=str)
    score = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    status = models.CharField(max_length=30, default='pending')
    feedback = models.TextField(blank=True)
    execution = models.JSONField(default=dict)
    ai_suggestion = models.JSONField(default=dict)

    @property
    def question_completed(self):
        return bool(self.status == 'evaluated' and self.question.type in ['coding', 'debugging']
                    and self.execution.get('total')
                    and self.execution.get('passed') == self.execution['total'])

    class Meta:
        constraints = [models.UniqueConstraint(fields=['submission','question'], name='unique_question_response')]


class Evaluation(models.Model):
    response = models.ForeignKey(QuestionResponse, on_delete=models.CASCADE, related_name='evaluations')
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    previous_score = models.DecimalField(max_digits=8, decimal_places=2)
    score = models.DecimalField(max_digits=8, decimal_places=2)
    feedback = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
