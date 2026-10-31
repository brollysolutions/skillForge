from django.db import transaction
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from accounts.models import User
from core.api import IsTrainer
from core.models import audit
from .models import Course, Topic, CourseEnrollment


class CourseSerializer(serializers.ModelSerializer):
    topic_count = serializers.IntegerField(source='topics.count', read_only=True)
    student_count = serializers.IntegerField(source='enrollments.count', read_only=True)

    class Meta:
        model = Course
        fields = ['id', 'title', 'description', 'is_active', 'topic_count', 'student_count', 'created_at']


class TopicSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)

    class Meta:
        model = Topic
        fields = ['id', 'course', 'course_title', 'title', 'description', 'learning_objectives', 'difficulty']

    def validate_course(self, value):
        if value.trainer_id != self.context['request'].user.id:
            raise serializers.ValidationError('Invalid course.')
        return value


class CourseViewSet(viewsets.ModelViewSet):
    permission_classes = [IsTrainer]
    serializer_class = CourseSerializer

    def get_queryset(self):
        qs = Course.objects.filter(trainer=self.request.user).prefetch_related('topics', 'enrollments').order_by('-created_at')
        return qs.filter(title__icontains=self.request.query_params.get('search', ''))

    def perform_create(self, serializer):
        course = serializer.save(trainer=self.request.user)
        audit(self.request.user, 'course.created', course)

    @action(detail=True, methods=['get', 'post'])
    def enrollments(self, request, pk=None):
        course = self.get_object()
        if request.method == 'POST':
            ids = request.data.get('student_ids', [])
            if not isinstance(ids, list) or not ids or len(ids) > 500:
                raise serializers.ValidationError('Provide 1 to 500 student IDs.')
            students = User.objects.filter(id__in=ids, trainer=request.user, role='student', is_active=True)
            if students.count() != len(set(ids)):
                raise serializers.ValidationError('One or more students are invalid.')
            with transaction.atomic():
                for student in students:
                    CourseEnrollment.objects.update_or_create(course=course, student=student, defaults={'is_active': True})
            audit(request.user, 'course.enrolled', course, count=students.count())
        return Response(list(course.enrollments.filter(is_active=True).values('student_id', 'student__name', 'student__email')))


class TopicViewSet(viewsets.ModelViewSet):
    permission_classes = [IsTrainer]
    serializer_class = TopicSerializer

    def get_queryset(self):
        qs = Topic.objects.filter(course__trainer=self.request.user).select_related('course').order_by('title')
        if self.request.query_params.get('course'):
            qs = qs.filter(course_id=self.request.query_params['course'])
        return qs
