from django.db.models import Q
from rest_framework.permissions import BasePermission


class IsStaffRole(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ('admin', 'sales', 'trainer')


class IsManager(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ('admin', 'sales')


def visible_students(user):
    from accounts.models import User
    students = User.objects.filter(role='student')
    if user.role in ('admin', 'sales'):
        return students
    if user.role == 'trainer':
        return students.filter(Q(trainer=user) | Q(batchmembership__batch__trainer=user, batchmembership__is_active=True)).distinct()
    return students.filter(pk=user.pk)


def visible_courses(user):
    from courses.models import Course
    courses = Course.objects.all()
    if user.role in ('admin', 'sales'):
        return courses
    if user.role == 'trainer':
        return courses.filter(Q(trainer=user) | Q(batches__trainer=user)).distinct()
    return courses.filter(enrollments__student=user, enrollments__is_active=True).distinct()
