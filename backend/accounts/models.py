from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.db.models.functions import Lower
from core.models import Timestamped


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError('Email is required.')
        user = self.model(email=email.strip().lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra):
        extra.update(is_staff=True, is_superuser=True, role='admin')
        return self.create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin, Timestamped):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=120)
    role = models.CharField(max_length=10, choices=[('admin', 'Admin'), ('sales', 'Sales'), ('trainer', 'Trainer'), ('student', 'Student')], default='student')
    trainer = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT, related_name='students')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    bio = models.TextField(blank=True, max_length=2000)
    objects = UserManager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    class Meta:
        constraints = [models.UniqueConstraint(Lower('email'), name='unique_normalized_email'),
                       models.UniqueConstraint(fields=['role'], condition=models.Q(role='admin'), name='single_platform_admin')]

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email


class Invitation(Timestamped):
    trainer = models.ForeignKey(User, on_delete=models.CASCADE)
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=120)
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True)
