from django.db import transaction
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from accounts.models import User
from core.api import IsTrainer
from core.access import IsStaffRole, visible_courses, visible_students
from core.models import audit
from .models import Course, Topic, CourseEnrollment, Batch, BatchMembership


class CourseSerializer(serializers.ModelSerializer):
    trainer_name = serializers.CharField(source='trainer.name', read_only=True)
    trainer = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(role='trainer', is_active=True), required=False)
    topic_count = serializers.IntegerField(source='topics.count', read_only=True)
    student_count = serializers.IntegerField(source='enrollments.count', read_only=True)

    class Meta:
        model = Course
        fields = ['id', 'trainer', 'trainer_name', 'title', 'description', 'is_active', 'topic_count', 'student_count', 'created_at']


class TopicSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)

    class Meta:
        model = Topic
        fields = ['id', 'course', 'course_title', 'title', 'description', 'learning_objectives', 'difficulty']

    def validate_course(self, value):
        if not visible_courses(self.context['request'].user).filter(pk=value.pk).exists():
            raise serializers.ValidationError('Invalid course.')
        return value


class CourseViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffRole]
    serializer_class = CourseSerializer

    def get_queryset(self):
        qs = visible_courses(self.request.user).prefetch_related('topics', 'enrollments').order_by('-created_at')
        return qs.filter(title__icontains=self.request.query_params.get('search', ''))

    def perform_create(self, serializer):
        trainer = serializer.validated_data.get('trainer')
        if self.request.user.role == 'trainer':
            trainer = self.request.user
        if not trainer:
            raise serializers.ValidationError('Select the course trainer.')
        course = serializer.save(trainer=trainer)
        audit(self.request.user, 'course.created', course)

    def perform_update(self, serializer):
        if 'trainer' in serializer.validated_data and serializer.validated_data['trainer'] != serializer.instance.trainer:
            raise serializers.ValidationError('The course owner cannot be changed; assign trainers through batches.')
        serializer.save()

    @action(detail=True, methods=['get', 'post'])
    def enrollments(self, request, pk=None):
        course = self.get_object()
        if request.method == 'POST':
            ids = request.data.get('student_ids', [])
            if not isinstance(ids, list) or not ids or len(ids) > 500 or any(type(i) is not int for i in ids):
                raise serializers.ValidationError('Provide 1 to 500 student IDs.')
            students = visible_students(request.user).filter(id__in=ids, is_active=True)
            if students.count() != len(set(ids)):
                raise serializers.ValidationError('One or more students are invalid.')
            with transaction.atomic():
                for student in students:
                    CourseEnrollment.objects.update_or_create(course=course, student=student, defaults={'is_active': True})
            audit(request.user, 'course.enrolled', course, count=students.count())
        return Response(list(course.enrollments.filter(is_active=True).values('student_id', 'student__name', 'student__email')))


class TopicViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffRole]
    serializer_class = TopicSerializer

    def get_queryset(self):
        qs = Topic.objects.filter(course__in=visible_courses(self.request.user)).select_related('course').order_by('title')
        if self.request.query_params.get('course'):
            qs = qs.filter(course_id=self.request.query_params['course'])
        return qs


class BatchSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    trainer_name = serializers.CharField(source='trainer.name', read_only=True)
    student_count = serializers.SerializerMethodField()
    assignment_count = serializers.IntegerField(source='assignments.count', read_only=True)
    trainer = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(role='trainer', is_active=True), required=False)

    class Meta:
        model = Batch
        fields = ['id', 'title', 'course', 'course_title', 'trainer', 'trainer_name', 'starts_at', 'ends_at', 'is_active', 'student_count', 'assignment_count']

    def get_student_count(self, obj):
        return obj.memberships.filter(is_active=True).count()

    def validate(self, attrs):
        user = self.context['request'].user
        course = attrs.get('course', getattr(self.instance, 'course', None))
        if not course or not visible_courses(user).filter(pk=course.pk, is_active=True).exists():
            raise serializers.ValidationError('Select an accessible active course.')
        if user.role == 'trainer':
            if attrs.get('trainer', user) != user:
                raise serializers.ValidationError('You can only manage your own batches.')
            attrs['trainer'] = user
        elif not attrs.get('trainer', getattr(self.instance, 'trainer', None)):
            raise serializers.ValidationError('Select a trainer.')
        if self.instance and (course.pk != self.instance.course_id or attrs.get('trainer', self.instance.trainer) != self.instance.trainer):
            raise serializers.ValidationError('Create a new batch to change its course or trainer.')
        start = attrs.get('starts_at', getattr(self.instance, 'starts_at', None))
        end = attrs.get('ends_at', getattr(self.instance, 'ends_at', None))
        if start and end and end < start:
            raise serializers.ValidationError('Batch end must follow its start.')
        return attrs


class BatchViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffRole]
    serializer_class = BatchSerializer
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        qs = Batch.objects.select_related('course', 'trainer').prefetch_related('memberships', 'assignments')
        if self.request.user.role == 'trainer':
            qs = qs.filter(trainer=self.request.user)
        if self.request.query_params.get('course'):
            qs = qs.filter(course_id=self.request.query_params['course'])
        return qs.order_by('-created_at')

    @action(detail=True, methods=['get', 'post'])
    def members(self, request, pk=None):
        batch = self.get_object()
        if request.method == 'POST':
            ids = request.data.get('student_ids')
            if not isinstance(ids, list) or not ids or len(ids) > 500 or any(type(i) is not int for i in ids):
                raise serializers.ValidationError('Select 1 to 500 students.')
            students = visible_students(request.user).filter(pk__in=ids, is_active=True)
            if students.count() != len(set(ids)):
                raise serializers.ValidationError('Invalid students.')
            with transaction.atomic():
                for student in students:
                    BatchMembership.objects.update_or_create(batch=batch, student=student, defaults={'is_active': True})
                    CourseEnrollment.objects.update_or_create(course=batch.course, student=student, defaults={'is_active': True})
                audit(request.user, 'batch.enrolled', batch, count=students.count())
        return Response(list(batch.memberships.filter(is_active=True).values('student_id', 'student__name', 'student__email')))
