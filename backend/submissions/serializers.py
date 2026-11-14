from rest_framework import serializers
from .models import Submission, QuestionResponse


class ResponseSerializer(serializers.ModelSerializer):
    question_title = serializers.CharField(source='question.title', read_only=True)
    question_type = serializers.CharField(source='question.type', read_only=True)
    max_marks = serializers.DecimalField(source='question.marks', max_digits=8, decimal_places=2, read_only=True)
    rubric = serializers.CharField(source='question.rubric', read_only=True)
    explanation = serializers.CharField(source='question.explanation', read_only=True)

    class Meta:
        model = QuestionResponse
        fields = ['id', 'question', 'question_title', 'question_type', 'max_marks', 'answer', 'score', 'status', 'feedback', 'execution', 'rubric', 'explanation', 'ai_suggestion']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        user = self.context['request'].user
        if user.role == 'student':
            data.pop('rubric', None)
            data.pop('ai_suggestion', None)
            if not instance.submission.assignment.results_released or instance.submission.status != 'evaluated':
                for key in ['score', 'feedback', 'execution', 'explanation']:
                    data.pop(key, None)
                data['status'] = 'pending' if instance.submission.status == 'in_progress' else 'submitted'
        return data


class SubmissionSerializer(serializers.ModelSerializer):
    task_completed = serializers.BooleanField(read_only=True)
    responses = ResponseSerializer(many=True, read_only=True)
    assignment_title = serializers.CharField(source='assignment.title', read_only=True)
    student_name = serializers.CharField(source='student.name', read_only=True)
    student_email = serializers.EmailField(source='student.email', read_only=True)
    total_marks = serializers.DecimalField(source='assignment.total_marks', max_digits=8, decimal_places=2, read_only=True)
    results_released = serializers.BooleanField(source='assignment.results_released', read_only=True)

    class Meta:
        model = Submission
        fields = ['id', 'assignment', 'assignment_title', 'student', 'student_name', 'student_email', 'attempt', 'status', 'started_at',
                  'expires_at', 'submitted_at', 'score', 'percentage', 'duration_seconds', 'total_marks', 'results_released', 'task_completed', 'responses']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if self.context['request'].user.role == 'student' and (not instance.assignment.results_released or instance.status != 'evaluated'):
            data['score'] = None
            data['percentage'] = None
            if instance.status == 'evaluated':
                data['status'] = 'submitted'
        return data
