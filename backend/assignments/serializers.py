from decimal import Decimal
from django.db import transaction
from rest_framework import serializers
from .models import Assignment, Question, TestCase


class TestCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCase
        fields = ['id', 'input', 'expected_output', 'is_hidden', 'weight']

    def validate_weight(self, value):
        if not 1 <= value <= 100:
            raise serializers.ValidationError('Weight must be between 1 and 100.')
        return value


class QuestionSerializer(serializers.ModelSerializer):
    test_cases = TestCaseSerializer(many=True, required=False)

    class Meta:
        model = Question
        fields = ['id', 'position', 'type', 'title', 'prompt', 'difficulty', 'marks', 'options', 'correct_answer',
                  'explanation', 'rubric', 'marking_policy', 'constraints', 'input_format', 'output_format', 'starter_code', 'language', 'test_cases']

    def validate(self, attrs):
        if not Decimal('0') < attrs.get('marks', 0) <= 10000:
            raise serializers.ValidationError('Question marks must be positive and at most 10,000.')
        kind = attrs.get('type')
        options = attrs.get('options', [])
        answer = attrs.get('correct_answer', [])
        if not isinstance(options, list) or len(options) > 20 or any(not isinstance(o, str) or len(o) > 2000 for o in options):
            raise serializers.ValidationError('Options must be a list of at most 20 strings.')
        if len(options) != len(set(options)):
            raise serializers.ValidationError('Options must be distinct.')
        if not isinstance(answer, list) or any(not isinstance(a, str) or len(a) > 5000 for a in answer):
            raise serializers.ValidationError('Correct answer must be a list of strings.')
        if kind in ['mcq', 'multiple_select']:
            if len(options) < 2 or not answer or not set(answer).issubset(set(options)) or len(answer) != len(set(answer)):
                raise serializers.ValidationError('Choose valid correct answers from at least two unique options.')
            if kind == 'mcq' and len(answer) != 1:
                raise serializers.ValidationError('An MCQ needs exactly one correct option.')
        if kind in ['fill_blank', 'output_prediction'] and not answer:
            raise serializers.ValidationError('Provide accepted answers.')
        if kind in ['coding', 'debugging']:
            cases = attrs.get('test_cases', [])
            if not cases or len(cases) > 20 or not any(not c.get('is_hidden', True) for c in cases):
                raise serializers.ValidationError('Coding questions require a visible expected-output check (20 tests maximum for legacy assessments).')
            if attrs.get('language', 'python') != 'python':
                raise serializers.ValidationError('Only Python is supported.')
        if kind in ['short_answer', 'descriptive', 'scenario', 'genai_practical', 'project'] and not attrs.get('rubric', '').strip():
            raise serializers.ValidationError('Provide a rubric for trainer-reviewed questions.')
        return attrs


class PublicQuestionSerializer(serializers.ModelSerializer):
    examples = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = ['id', 'position', 'type', 'title', 'prompt', 'difficulty', 'marks', 'options', 'constraints',
                  'input_format', 'output_format', 'starter_code', 'language', 'examples']

    def get_examples(self, obj):
        return [{'input': c.input, 'expected_output': c.expected_output} for c in obj.test_cases.all() if not c.is_hidden]


class AssignmentSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, required=False)
    course_title = serializers.CharField(source='course.title', read_only=True)
    topic_title = serializers.CharField(source='topic.title', read_only=True, default='General')
    batch_title = serializers.CharField(source='batch.title', read_only=True, default='')
    assigned_count = serializers.IntegerField(source='access_records.count', read_only=True)

    class Meta:
        model = Assignment
        fields = ['id', 'batch', 'batch_title', 'course', 'course_title', 'topic', 'topic_title', 'material', 'title', 'description', 'learning_objectives',
                  'difficulty', 'status', 'total_marks', 'duration_minutes', 'attempts_allowed', 'passing_percentage', 'starts_at',
                  'deadline', 'hints_enabled', 'results_released', 'questions', 'assigned_count', 'created_at', 'published_at']
        read_only_fields = ['status', 'total_marks', 'results_released', 'published_at']

    def validate(self, attrs):
        user = self.context['request'].user
        course = attrs.get('course', getattr(self.instance, 'course', None))
        topic = attrs.get('topic', getattr(self.instance, 'topic', None))
        material = attrs.get('material', getattr(self.instance, 'material', None))
        from core.access import visible_courses
        if not course or not visible_courses(user).filter(pk=course.pk).exists():
            raise serializers.ValidationError('Invalid course.')
        batch = attrs.get('batch', getattr(self.instance, 'batch', None))
        if batch and (batch.trainer_id != user.id or batch.course_id != course.pk or not batch.is_active):
            raise serializers.ValidationError('Choose an active batch you teach in this course.')
        if batch and not attrs.get('deadline', getattr(self.instance, 'deadline', None)):
            raise serializers.ValidationError('Set a deadline for this batch assignment.')
        if topic and topic.course_id != course.pk:
            raise serializers.ValidationError('Topic must belong to the course.')
        if material and (material.trainer_id != user.id or material.course_id != course.pk):
            raise serializers.ValidationError('Material must belong to the course.')
        start = attrs.get('starts_at', getattr(self.instance, 'starts_at', None))
        deadline = attrs.get('deadline', getattr(self.instance, 'deadline', None))
        if start and deadline and deadline <= start:
            raise serializers.ValidationError('Deadline must be after the start date.')
        if not 1 <= attrs.get('duration_minutes', getattr(self.instance, 'duration_minutes', 60)) <= 480:
            raise serializers.ValidationError('Duration must be between 1 and 480 minutes.')
        if not 1 <= attrs.get('attempts_allowed', getattr(self.instance, 'attempts_allowed', 1)) <= 10:
            raise serializers.ValidationError('Attempts must be between 1 and 10.')
        if not 0 <= attrs.get('passing_percentage', 50) <= 100:
            raise serializers.ValidationError('Passing percentage must be between 0 and 100.')
        if self.instance and self.instance.status != 'draft':
            raise serializers.ValidationError('Published assessments are immutable. Create a new draft for changes.')
        questions = attrs.get('questions', [])
        if len(questions) > 1:
            raise serializers.ValidationError('Use one focused task per assignment.')
        if any(len(q.get('test_cases', [])) > 1 for q in questions):
            raise serializers.ValidationError('Use one expected-output check per task.')
        if len(questions) > 50:
            raise serializers.ValidationError('Maximum 50 questions.')
        titles = [q['title'].strip().lower() for q in questions]
        if len(titles) != len(set(titles)):
            raise serializers.ValidationError('Remove duplicate question titles.')
        return attrs

    def save_questions(self, assignment, questions):
        assignment.questions.all().delete()
        for index, data in enumerate(questions, 1):
            tests = data.pop('test_cases', [])
            data['position'] = index
            question = Question.objects.create(assignment=assignment, **data)
            TestCase.objects.bulk_create([TestCase(question=question, **test) for test in tests])
        assignment.total_marks = sum((q.marks for q in assignment.questions.all()), Decimal('0'))
        assignment.save(update_fields=['total_marks', 'updated_at'])

    @transaction.atomic
    def create(self, validated_data):
        questions = validated_data.pop('questions', [])
        assignment = Assignment.objects.create(**validated_data)
        self.save_questions(assignment, questions)
        return assignment

    @transaction.atomic
    def update(self, instance, validated_data):
        questions = validated_data.pop('questions', None)
        instance = super().update(instance, validated_data)
        if questions is not None:
            self.save_questions(instance, questions)
        return instance


class StudentAssignmentSerializer(serializers.ModelSerializer):
    batch_title = serializers.CharField(source='batch.title', read_only=True, default='')
    questions = serializers.SerializerMethodField()
    course_title = serializers.CharField(source='course.title', read_only=True)
    topic_title = serializers.CharField(source='topic.title', read_only=True, default='General')
    student_status = serializers.SerializerMethodField()
    attempts_used = serializers.SerializerMethodField()

    class Meta:
        model = Assignment
        fields = ['id', 'title', 'description', 'batch_title', 'course_title', 'topic_title', 'difficulty', 'status', 'total_marks',
                  'duration_minutes', 'attempts_allowed', 'passing_percentage', 'starts_at', 'deadline', 'hints_enabled',
                  'results_released', 'questions', 'student_status', 'attempts_used']

    def get_questions(self, obj):
        # A student must start an attempt before question content becomes available.
        if not obj.submissions.filter(student=self.context['request'].user).exists():
            return []
        return PublicQuestionSerializer(obj.questions.all(), many=True).data

    def get_student_status(self, obj):
        from django.utils import timezone
        submissions = obj.submissions.filter(student=self.context['request'].user)
        if submissions.filter(status='evaluated').exists():
            return 'evaluated' if obj.results_released else 'submitted'
        if submissions.filter(status='submitted').exists():
            return 'submitted'
        if obj.deadline and obj.deadline < timezone.now():
            return 'overdue'
        return 'in_progress' if submissions.exists() else 'not_started'

    def get_attempts_used(self, obj):
        return obj.submissions.filter(student=self.context['request'].user).count()
