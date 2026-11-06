from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from accounts.models import User
from core.api import IsTrainer
from core.access import visible_students
from core.models import audit, Notification
from .models import Assignment, AssignmentAccess
from .serializers import AssignmentSerializer, StudentAssignmentSerializer, QuestionSerializer


def accessible_assignments(user):
    qs = Assignment.objects.select_related('course', 'topic').prefetch_related('questions__test_cases', 'access_records')
    if user.role in ('admin', 'sales'):
        return qs
    if user.role == 'trainer':
        return qs.filter(trainer=user)
    return qs.filter(access_records__student=user, access_records__is_active=True, status__in=['published', 'closed'], trainer__is_active=True)


class AssignmentViewSet(viewsets.ModelViewSet):
    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']

    def get_permissions(self):
        if self.action not in ['list', 'retrieve', 'start']:
            return [IsTrainer()]
        return super().get_permissions()

    def get_queryset(self):
        qs = accessible_assignments(self.request.user).order_by('-created_at')
        for key in ['course', 'topic', 'status', 'batch']:
            if self.request.query_params.get(key):
                qs = qs.filter(**{key: self.request.query_params[key]})
        if self.request.query_params.get('search'):
            qs = qs.filter(title__icontains=self.request.query_params['search'])
        return qs

    def get_serializer_class(self):
        return AssignmentSerializer if self.request.user.role != 'student' else StudentAssignmentSerializer

    @action(detail=False, methods=['post'], url_path='import-question')
    def import_question(self, request):
        from pathlib import Path
        from materials.extraction import extract
        upload = request.FILES.get('file')
        if not upload or Path(upload.name).suffix.lower() not in {'.pdf', '.docx', '.txt'}:
            raise serializers.ValidationError('Upload a PDF, DOCX, or TXT question file.')
        text = extract(upload)
        if len(text) > 12000:
            raise serializers.ValidationError('Use a single task with at most 12,000 characters.')
        return Response({'prompt': text})

    def perform_create(self, serializer):
        assignment = serializer.save(trainer=self.request.user)
        audit(self.request.user, 'assignment.created', assignment)

    def perform_destroy(self, instance):
        if instance.status != 'draft':
            raise serializers.ValidationError('Only drafts can be deleted; archive published assignments.')
        instance.delete()

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        with transaction.atomic():
            assignment = self.get_object()
            if assignment.status != 'draft' or not assignment.questions.exists():
                raise serializers.ValidationError('A nonempty draft is required.')
            if assignment.deadline and assignment.deadline <= timezone.now():
                raise serializers.ValidationError('The deadline must be in the future.')
            if assignment.batch_id and (not assignment.batch.is_active or assignment.batch.trainer_id != request.user.id):
                raise serializers.ValidationError('The assigned batch is not active.')
            for question in assignment.questions.all():
                data = QuestionSerializer(question).data
                validator = QuestionSerializer(data=data)
                validator.is_valid(raise_exception=True)
            assignment.status = 'published'
            assignment.published_at = timezone.now()
            assignment.save(update_fields=['status', 'published_at', 'updated_at'])
            if assignment.batch_id:
                for member in assignment.batch.memberships.filter(is_active=True, student__is_active=True):
                    AssignmentAccess.objects.update_or_create(assignment=assignment, student=member.student, defaults={'is_active': True})
                    Notification.objects.create(user=member.student, title='New batch assignment', message=assignment.title, link=f'/assignments/{assignment.pk}')
            audit(request.user, 'assignment.published', assignment)
        return Response(self.get_serializer(assignment).data)

    @action(detail=True, methods=['post'], url_path='assign-students')
    def assign_students(self, request, pk=None):
        assignment = self.get_object()
        if assignment.status != 'published':
            raise serializers.ValidationError('Publish the assignment before assigning students.')
        if request.data.get('all_enrolled') is True:
            students = visible_students(request.user).filter(is_active=True,
                                          courseenrollment__course=assignment.course, courseenrollment__is_active=True)
        else:
            ids = request.data.get('student_ids', [])
            if not isinstance(ids, list) or not ids or len(ids) > 500 or any(type(i) is not int for i in ids):
                raise serializers.ValidationError('Provide 1 to 500 student IDs.')
            students = visible_students(request.user).filter(pk__in=ids, is_active=True)
            if students.count() != len(set(ids)):
                raise serializers.ValidationError('One or more students are invalid.')
        if assignment.batch_id:
            if request.data.get('all_enrolled') is True:
                students = students.filter(batchmembership__batch=assignment.batch, batchmembership__is_active=True)
            eligible = students.filter(batchmembership__batch=assignment.batch, batchmembership__is_active=True)
            if eligible.count() != students.count():
                raise serializers.ValidationError('Select only students enrolled in this batch.')
            students = eligible
        with transaction.atomic():
            for student in students:
                access, created = AssignmentAccess.objects.update_or_create(assignment=assignment, student=student, defaults={'is_active': True})
                if created:
                    Notification.objects.create(user=student, title='New assignment', message=assignment.title, link=f'/assignments/{assignment.pk}')
            audit(request.user, 'assignment.assigned', assignment, count=students.count())
        return Response({'assigned': students.count()})

    @action(detail=True, methods=['get', 'post'])
    def access(self, request, pk=None):
        assignment = self.get_object()
        if request.method == 'POST':
            access = get_object_or_404(AssignmentAccess, assignment=assignment, student_id=request.data.get('student_id'))
            if type(request.data.get('is_active')) is not bool:
                raise serializers.ValidationError('is_active must be a boolean.')
            access.is_active = request.data['is_active']
            access.save()
            audit(request.user, 'assignment.access_changed', access)
        return Response(list(assignment.access_records.values('student_id', 'student__name', 'student__email', 'is_active')))

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        assignment = self.get_object()
        if assignment.status != 'published':
            raise serializers.ValidationError('Only published assignments can be closed.')
        assignment.status = 'closed'
        assignment.save()
        audit(request.user, 'assignment.closed', assignment)
        return Response(self.get_serializer(assignment).data)

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        assignment = self.get_object()
        assignment.status = 'archived'
        assignment.save()
        audit(request.user, 'assignment.archived', assignment)
        return Response(self.get_serializer(assignment).data)

    @action(detail=True, methods=['post'], url_path='release-results')
    def release_results(self, request, pk=None):
        assignment = self.get_object()
        if assignment.status not in ['published', 'closed']:
            raise serializers.ValidationError('Publish the assignment first.')
        if assignment.status == 'published' and (not assignment.deadline or assignment.deadline > timezone.now()):
            raise serializers.ValidationError('Close the assignment or wait until its deadline before releasing results.')
        if assignment.submissions.filter(status__in=['submitted', 'grading']).exists():
            raise serializers.ValidationError('Complete pending evaluations before releasing results.')
        assignment.results_released = True
        assignment.save()
        audit(request.user, 'results.released', assignment)
        return Response(self.get_serializer(assignment).data)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        from submissions.services import start_attempt
        from submissions.serializers import SubmissionSerializer
        if request.user.role != 'student':
            raise serializers.ValidationError('Only students can start an assessment.')
        submission = start_attempt(request.user, self.get_object())
        return Response(SubmissionSerializer(submission, context={'request': request}).data, status=201)
