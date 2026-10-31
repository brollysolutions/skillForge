from decimal import Decimal
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from core.api import IsTrainer, AIThrottle
from core.models import audit
from courses.models import Course, Topic
from materials.models import StudyMaterial
from assignments.models import Assignment, QUESTION_TYPES
from assignments.serializers import AssignmentSerializer
from .workflows import generate_assignment


class GenerateConfig(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    course = serializers.IntegerField()
    topic = serializers.IntegerField(required=False, allow_null=True)
    material = serializers.IntegerField(required=False, allow_null=True)
    number_of_questions = serializers.IntegerField(min_value=1, max_value=20)
    question_types = serializers.ListField(child=serializers.ChoiceField(choices=QUESTION_TYPES), min_length=1, max_length=11)
    difficulty = serializers.ChoiceField(choices=['easy','medium','hard','mixed'], default='medium')
    total_marks = serializers.DecimalField(max_digits=7, decimal_places=2, min_value=1, max_value=10000)
    duration_minutes = serializers.IntegerField(min_value=1, max_value=480, default=60)
    attempts_allowed = serializers.IntegerField(min_value=1, max_value=10, default=1)
    passing_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=0, max_value=100, default=50)
    starts_at = serializers.DateTimeField(required=False, allow_null=True)
    deadline = serializers.DateTimeField(required=False, allow_null=True)
    learning_objectives = serializers.CharField(required=False, allow_blank=True, max_length=5000)
    instructions = serializers.CharField(required=False, allow_blank=True, max_length=5000)


class GenerateAssignmentView(APIView):
    permission_classes = [IsTrainer]
    throttle_classes = [AIThrottle]

    def post(self, request):
        validator = GenerateConfig(data=request.data)
        validator.is_valid(raise_exception=True)
        config = validator.validated_data
        course = get_object_or_404(Course, pk=config['course'], trainer=request.user)
        material = get_object_or_404(StudyMaterial, pk=config['material'], course=course, trainer=request.user) if config.get('material') else None
        topic = get_object_or_404(Topic, pk=config['topic'], course=course) if config.get('topic') else None
        if not material and not topic and not config.get('instructions'):
            raise serializers.ValidationError('Select material or a topic, or provide detailed topic instructions.')
        draft = generate_assignment(request.user, config, material, topic)
        if len(draft['questions']) != config['number_of_questions'] or any(q['type'] not in config['question_types'] for q in draft['questions']):
            raise serializers.ValidationError('Generated questions do not match your configuration. Retry generation.')
        total = sum(Decimal(str(q['marks'])) for q in draft['questions'])
        if total != config['total_marks']:
            raise serializers.ValidationError('Generated marks do not match the requested total. Retry generation.')
        data = {key: value for key, value in config.items() if key not in ['number_of_questions','question_types','instructions','total_marks']}
        data.update(draft)
        serializer = AssignmentSerializer(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        assignment = serializer.save(trainer=request.user)
        audit(request.user, 'assignment.generated', assignment)
        return Response(serializer.data, status=201)


class RegenerateQuestionView(APIView):
    permission_classes = [IsTrainer]
    throttle_classes = [AIThrottle]

    def post(self, request, pk):
        assignment = get_object_or_404(Assignment, pk=pk, trainer=request.user, status='draft')
        question = get_object_or_404(assignment.questions, pk=request.data.get('question_id'))
        draft = generate_assignment(request.user, {'title': assignment.title, 'number_of_questions': 1, 'question_types': [question.type],
                                    'difficulty': question.difficulty, 'total_marks': str(question.marks), 'replace_question': question.title},
                                    assignment.material, assignment.topic)
        if len(draft['questions']) != 1:
            raise serializers.ValidationError('The AI did not return exactly one replacement question.')
        new_question = draft['questions'][0]
        if new_question['type'] != question.type or Decimal(str(new_question['marks'])) != question.marks:
            raise serializers.ValidationError('Replacement type or marks do not match. Retry.')
        from assignments.serializers import QuestionSerializer
        questions = [new_question if q.pk == question.pk else dict(QuestionSerializer(q).data) for q in assignment.questions.all()]
        serializer = AssignmentSerializer(assignment, data={'questions': questions}, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
