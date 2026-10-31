from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from accounts.models import User
from core.api import IsTrainer, AIThrottle
from core.models import audit, Notification, PlatformSettings
from assignments.views import accessible_assignments
from .models import PerformanceReport, BatchReport
from .services import build_report, render_pdf


class ReportSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.name', read_only=True)

    class Meta:
        model = PerformanceReport
        fields = ['id','student','student_name','metrics','narrative','published_at','recommendations_enabled','created_at']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if self.context['request'].user.role != 'trainer':
            data['narrative'] = dict(data['narrative'])
            data['narrative'].pop('trainer_feedback', None)
            data['narrative'].pop('recommendations', None)  # Authorized live links come from learning-path endpoint.
        return data


class ReportViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ReportSerializer

    def get_queryset(self):
        qs = PerformanceReport.objects.select_related('student').order_by('-created_at')
        if self.request.user.role == 'trainer':
            qs = qs.filter(trainer=self.request.user)
            if self.request.query_params.get('student'):
                qs = qs.filter(student_id=self.request.query_params['student'])
            return qs
        return qs.filter(student=self.request.user, published_at__isnull=False)

    @action(detail=True, methods=['post'], permission_classes=[IsTrainer])
    def publish(self, request, pk=None):
        report = self.get_object()
        if report.published_at is None:
            report.published_at = timezone.now()
            report.save(update_fields=['published_at'])
            audit(request.user, 'report.published', report)
            Notification.objects.create(user=report.student, title='Your learning report is ready', link=f'/reports/{report.pk}')
        return Response(self.get_serializer(report).data)

    @action(detail=True, methods=['post'], permission_classes=[IsTrainer])
    def recommendations(self, request, pk=None):
        report = self.get_object()
        if type(request.data.get('enabled')) is not bool:
            raise serializers.ValidationError('enabled must be boolean.')
        report.recommendations_enabled = request.data['enabled']
        report.save(update_fields=['recommendations_enabled'])
        return Response(self.get_serializer(report).data)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        report = self.get_object()
        narrative = dict(report.narrative)
        narrative.pop('evidence_submission_ids', None)
        narrative.pop('recommendations', None)
        if request.user.role != 'trainer':
            narrative.pop('trainer_feedback', None)
        return FileResponse(render_pdf(f'{report.student.name} - Performance Report', report.metrics, narrative),
                            as_attachment=True, filename=f'skillforge-report-{report.pk}.pdf')


class GenerateReportView(APIView):
    permission_classes = [IsTrainer]
    throttle_classes = [AIThrottle]

    def post(self, request, student_id):
        student = get_object_or_404(User, pk=student_id, trainer=request.user, role='student')
        report = build_report(request.user, student)
        return Response(ReportSerializer(report, context={'request': request}).data, status=201)


class LearningPathView(APIView):
    def get(self, request):
        if request.user.role != 'student':
            raise serializers.ValidationError('Use individual reports to review student recommendations.')
        settings, _ = PlatformSettings.objects.get_or_create(trainer=request.user.trainer)
        if not settings.recommendations_enabled:
            return Response([])
        report = PerformanceReport.objects.filter(student=request.user, published_at__isnull=False).order_by('-created_at').first()
        if not report or not report.recommendations_enabled:
            return Response([])
        available = accessible_assignments(request.user).filter(status='published')
        return Response([{'id': r.pk, 'topic': r.topic.title, 'reason': r.reason, 'steps': r.steps, 'difficulty': r.difficulty,
                          'assignments': list(r.assignments.filter(pk__in=available).values('id','title'))}
                         for r in report.learning_recommendations.select_related('topic').prefetch_related('assignments')])


class BatchReportView(APIView):
    permission_classes = [IsTrainer]

    def get_throttles(self):
        return [AIThrottle()] if self.request.method == 'POST' else super().get_throttles()

    def get(self, request):
        return Response(list(BatchReport.objects.filter(trainer=request.user).order_by('-created_at').values('id','metrics','narrative','created_at')[:20]))

    def post(self, request):
        from analytics.services import analytics
        from ai_services.providers import generate_json
        from ai_services.schemas import BatchNarrative
        from courses.models import Topic
        snapshot = analytics(request.user)
        if not snapshot['topic_scores']:
            raise serializers.ValidationError('Evaluate student assessments before analyzing classroom learning gaps.')
        topics = list(Topic.objects.filter(course__trainer=request.user).values('id','title','learning_objectives'))
        evidence = {key: snapshot[key] for key in ['metrics','topic_scores','difficulty_scores','distribution','trends']}
        evidence['available_topics'] = topics
        narrative = generate_json(request.user, 'gemini', 'batch.report', BatchNarrative,
            'Analyze aggregate classroom evidence. Identify learning gaps and practical teaching interventions. '
            'Use qualitative prose only; Django separately displays numerical metrics. Do not invent student histories or statistics. '
            'Use only supplied topic IDs. Do not infer individual performance from batch averages.', evidence)
        if not set(narrative['priority_topic_ids']).issubset({t['id'] for t in topics}):
            raise serializers.ValidationError('The batch report references unknown topics. Regenerate it.')
        report = BatchReport.objects.create(trainer=request.user, metrics=snapshot['metrics'], narrative=narrative)
        audit(request.user, 'batch_report.generated', report)
        return Response({'id':report.pk, 'metrics':report.metrics, 'narrative':report.narrative, 'created_at':report.created_at}, status=201)


class BatchReportDownloadView(APIView):
    permission_classes = [IsTrainer]

    def get(self, request, pk):
        report = get_object_or_404(BatchReport, pk=pk, trainer=request.user)
        sections = {key: value for key,value in report.narrative.items() if key != 'priority_topic_ids'}
        return FileResponse(render_pdf('SkillForge AI - Classroom Learning Gaps', report.metrics, sections),
                            as_attachment=True, filename=f'skillforge-batch-report-{pk}.pdf')
