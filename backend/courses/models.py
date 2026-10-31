from django.conf import settings
from django.db import models
from core.models import Timestamped


class Course(Timestamped):
    trainer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title


class Topic(Timestamped):
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name='topics')
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    learning_objectives = models.TextField(blank=True)
    difficulty = models.CharField(max_length=10, choices=[('easy','Easy'), ('medium','Medium'), ('hard','Hard')], default='medium')


class CourseEnrollment(Timestamped):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['course', 'student'], name='unique_enrollment')]
