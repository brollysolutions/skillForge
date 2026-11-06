from django.conf import settings
from django.db import models
from core.models import Timestamped

QUESTION_TYPES = [(key, key.replace('_', ' ').title()) for key in [
    'mcq', 'multiple_select', 'fill_blank', 'short_answer', 'descriptive', 'coding',
    'debugging', 'output_prediction', 'scenario', 'genai_practical', 'project']]


class Assignment(Timestamped):
    trainer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    course = models.ForeignKey('courses.Course', on_delete=models.PROTECT, related_name='assignments')
    batch = models.ForeignKey('courses.Batch', on_delete=models.PROTECT, related_name='assignments', null=True, blank=True)
    topic = models.ForeignKey('courses.Topic', on_delete=models.PROTECT, null=True, blank=True)
    material = models.ForeignKey('materials.StudyMaterial', on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    learning_objectives = models.TextField(blank=True)
    difficulty = models.CharField(max_length=10, choices=[(x, x.title()) for x in ['easy', 'medium', 'hard', 'mixed']], default='medium')
    status = models.CharField(max_length=12, choices=[(x,x.title()) for x in ['draft','published','closed','archived']], default='draft')
    total_marks = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    duration_minutes = models.PositiveIntegerField(default=60)
    attempts_allowed = models.PositiveSmallIntegerField(default=1)
    passing_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=50)
    starts_at = models.DateTimeField(null=True, blank=True)
    deadline = models.DateTimeField(null=True, blank=True)
    hints_enabled = models.BooleanField(default=False)
    results_released = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True)


class Question(Timestamped):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='questions')
    position = models.PositiveIntegerField(default=1)
    type = models.CharField(max_length=25, choices=QUESTION_TYPES)
    title = models.CharField(max_length=200)
    prompt = models.TextField()
    difficulty = models.CharField(max_length=10, default='medium')
    marks = models.DecimalField(max_digits=8, decimal_places=2)
    options = models.JSONField(default=list)
    correct_answer = models.JSONField(default=list)
    explanation = models.TextField(blank=True)
    rubric = models.TextField(blank=True)
    marking_policy = models.CharField(max_length=12, choices=[('exact','Exact'), ('partial','Partial')], default='exact')
    constraints = models.TextField(blank=True)
    input_format = models.TextField(blank=True)
    output_format = models.TextField(blank=True)
    starter_code = models.TextField(blank=True)
    language = models.CharField(max_length=20, default='python')

    class Meta:
        ordering = ['position', 'id']


class TestCase(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='test_cases')
    input = models.TextField(blank=True)
    expected_output = models.TextField(blank=True)
    is_hidden = models.BooleanField(default=True)
    weight = models.PositiveIntegerField(default=1)


class AssignmentAccess(Timestamped):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='access_records')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['assignment','student'], name='unique_assignment_access')]
