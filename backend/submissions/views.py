from decimal import Decimal, InvalidOperation
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from core.api import IsTrainer, AIThrottle
from core.models import audit
from .models import Submission, QuestionResponse, Evaluation
from .serializers import SubmissionSerializer
from .services import save_answers, finalize, recalculate


class SubmissionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SubmissionSerializer

    def get_queryset(self):
        qs = Submission.objects.select_related('assignment', 'student').prefetch_related('responses__question').order_by('-started_at')
        if self.request.user.role == 'trainer':
            qs = qs.filter(assignment__trainer=self.request.user)
        elif self.request.user.role == 'student':
            qs = qs.filter(student=self.request.user)
        for key in ['assignment', 'status']:
            if self.request.query_params.get(key):
                qs = qs.filter(**{key: self.request.query_params[key]})
        if self.request.user.role != 'student' and self.request.query_params.get('student'):
            qs = qs.filter(student_id=self.request.query_params['student'])
        return qs

    @action(detail=True, methods=['post'])
    def save(self, request, pk=None):
        submission = self.get_object()
        save_answers(request.user, submission, request.data.get('answers', {}))
        return Response({'detail': 'Answers saved.'})

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        submission = finalize(request.user, self.get_object(), request.data.get('answers'))
        submission.refresh_from_db()
        return Response(self.get_serializer(submission).data)

    @action(detail=True, methods=['post'], permission_classes=[IsTrainer])
    def review(self, request, pk=None):
        with transaction.atomic():
            submission = self.get_object()
            submission = Submission.objects.select_for_update().get(pk=submission.pk)
            if submission.status not in ['submitted', 'evaluated'] or submission.assignment.results_released:
                raise serializers.ValidationError('Only submitted, unreleased work may be reviewed.')
            response = get_object_or_404(QuestionResponse, pk=request.data.get('response_id'), submission=submission)
            try:
                score = Decimal(str(request.data.get('score')))
                if not score.is_finite() or score < 0 or score > response.question.marks or score.as_tuple().exponent < -2:
                    raise ValueError()
            except (ValueError, InvalidOperation, TypeError):
                raise serializers.ValidationError('Score must be within the question marks, with at most two decimal places.')
            feedback = request.data.get('feedback', '')
            if not isinstance(feedback, str) or len(feedback) > 5000:
                raise serializers.ValidationError('Feedback must be text, up to 5,000 characters.')
            Evaluation.objects.create(response=response, reviewer=request.user, previous_score=response.score, score=score, feedback=feedback)
            response.score, response.feedback, response.status = score, feedback, 'evaluated'
            response.save()
            recalculate(submission)
            audit(request.user, 'evaluation.reviewed', response, score=str(score))
        return Response(self.get_serializer(submission).data)

    @action(detail=True, methods=['post'], permission_classes=[IsTrainer], throttle_classes=[AIThrottle], url_path='ai-review')
    def ai_review(self, request, pk=None):
        from ai_services.workflows import assist_evaluation
        submission = self.get_object()
        response = get_object_or_404(QuestionResponse, submission=submission, pk=request.data.get('response_id'))
        if submission.status not in ['submitted','evaluated']:
            raise serializers.ValidationError('The attempt must be submitted first.')
        response.ai_suggestion = assist_evaluation(request.user, response)
        response.save(update_fields=['ai_suggestion'])
        return Response({'suggestion': response.ai_suggestion, 'detail': 'Advisory only. Official marks require trainer review.'})
