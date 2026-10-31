from django.conf import settings
from django.db import models


class Timestamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AuditLog(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=100)
    object_type = models.CharField(max_length=60)
    object_id = models.CharField(max_length=60, blank=True)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True)
    link = models.CharField(max_length=200, blank=True)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class PlatformSettings(models.Model):
    trainer = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    leaderboard_enabled = models.BooleanField(default=False)
    recommendations_enabled = models.BooleanField(default=True)
    organization_name = models.CharField(max_length=100, default='SkillForge Academy')


class AIUsageLog(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    provider = models.CharField(max_length=20)
    operation = models.CharField(max_length=60)
    model = models.CharField(max_length=100)
    status = models.CharField(max_length=20)
    error_type = models.CharField(max_length=100, blank=True)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    duration_ms = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)


def audit(actor, action, obj, **metadata):
    AuditLog.objects.create(actor=actor, action=action, object_type=obj.__class__.__name__, object_id=str(obj.pk), metadata=metadata)
