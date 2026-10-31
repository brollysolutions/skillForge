import uuid
from pathlib import Path
from django.conf import settings
from django.db import models
from core.models import Timestamped


def private_upload(instance, filename):
    return f'materials/{instance.trainer_id}/{uuid.uuid4().hex}{Path(filename).suffix.lower()}'


class StudyMaterial(Timestamped):
    trainer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    course = models.ForeignKey('courses.Course', on_delete=models.PROTECT, related_name='materials')
    topic = models.ForeignKey('courses.Topic', null=True, blank=True, on_delete=models.PROTECT)
    title = models.CharField(max_length=200)
    subject = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    learning_objectives = models.TextField(blank=True)
    important_concepts = models.TextField(blank=True)
    trainer_instructions = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    file = models.FileField(upload_to=private_upload, blank=True)
    original_filename = models.CharField(max_length=255, blank=True)
    size_bytes = models.PositiveIntegerField(default=0)
    extracted_text = models.TextField(blank=True)
    analysis = models.JSONField(default=dict)
    analysis_approved = models.BooleanField(default=False)
    status = models.CharField(max_length=20, default='ready')
