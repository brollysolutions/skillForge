from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from core.api import CodeThrottle
from submissions.models import Submission
from submissions.services import require_access, require_open
from .service import run_code


class RunCodeView(APIView):
    throttle_classes = [CodeThrottle]

    def post(self, request):
        submission = get_object_or_404(Submission, pk=request.data.get('submission_id'), student=request.user)
        require_access(request.user, submission.assignment)
        require_open(submission.assignment)
        if submission.status != 'in_progress' or submission.expires_at <= timezone.now():
            raise serializers.ValidationError('Start an active attempt before running code.')
        question = get_object_or_404(submission.assignment.questions, pk=request.data.get('question_id'), type__in=['coding','debugging'])
        source = request.data.get('code', '')
        if not isinstance(source, str) or not 1 <= len(source) <= 50000:
            raise serializers.ValidationError('Provide Python code, up to 50,000 characters.')
        if 'input' in request.data:
            stdin = request.data['input']
            if not isinstance(stdin, str) or len(stdin) > 10000:
                raise serializers.ValidationError('Custom input must be text, up to 10,000 characters.')
            return Response({'results': [run_code(source, stdin)]})
        cases = question.test_cases.filter(is_hidden=False)
        return Response({'results': [run_code(source, c.input, c.expected_output) for c in cases]})
