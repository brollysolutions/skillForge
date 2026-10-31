from django.conf import settings
from django.db import models
from core.models import Timestamped


class PerformanceReport(Timestamped):
    trainer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='generated_reports')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='performance_reports')
    metrics = models.JSONField(default=dict)
    evidence = models.JSONField(default=dict)
    narrative = models.JSONField(default=dict)
    published_at = models.DateTimeField(null=True)
    recommendations_enabled = models.BooleanField(default=True)


class LearningRecommendation(models.Model):
    report = models.ForeignKey(PerformanceReport, on_delete=models.CASCADE, related_name='learning_recommendations')
    topic = models.ForeignKey('courses.Topic', on_delete=models.PROTECT)
    assignments = models.ManyToManyField('assignments.Assignment', blank=True)
    reason = models.TextField()
    steps = models.JSONField(default=list)
    difficulty = models.CharField(max_length=10)


class BatchReport(Timestamped):
    trainer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    metrics = models.JSONField(default=dict)
    narrative = models.JSONField(default=dict)
