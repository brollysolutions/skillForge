import csv
import io
from datetime import timedelta
from django.http import HttpResponse, FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from accounts.models import User
from courses.models import Course
from assignments.models import Assignment
from submissions.models import Submission
from core.api import IsTrainer
from core.access import IsStaffRole, visible_students, visible_courses
from core.models import PlatformSettings
from .services import analytics


class AnalyticsFilter(serializers.Serializer):
    batch = serializers.IntegerField(required=False, min_value=1)
    course = serializers.IntegerField(required=False, min_value=1)
    topic = serializers.IntegerField(required=False, min_value=1)
    student = serializers.IntegerField(required=False, min_value=1)
    assignment = serializers.IntegerField(required=False, min_value=1)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)


class DashboardView(APIView):
    def get(self, request):
        filters = AnalyticsFilter(data=request.query_params)
        filters.is_valid(raise_exception=True)
        if request.user.role == 'student' and filters.validated_data:
            raise serializers.ValidationError('Student analytics always use your own records.')
        return Response(analytics(request.user, filters.validated_data))


class AdminDashboardView(DashboardView):
    permission_classes = [IsStaffRole]


class ScopedAnalyticsView(APIView):
    permission_classes = [IsStaffRole]

    def get(self, request, kind, pk):
        if kind not in ['student', 'course', 'assignment']:
            from rest_framework.exceptions import NotFound
            raise NotFound()
        if kind == 'student':
            get_object_or_404(visible_students(request.user), pk=pk)
        elif kind == 'course':
            get_object_or_404(visible_courses(request.user), pk=pk)
        else:
            get_object_or_404(Assignment.objects.all() if request.user.role in ('admin', 'sales') else Assignment.objects.filter(trainer=request.user), pk=pk)
        return Response(analytics(request.user, {kind: pk}))


class ExportAnalyticsView(APIView):
    permission_classes = [IsStaffRole]

    def get(self, request):
        filters = AnalyticsFilter(data=request.query_params)
        filters.is_valid(raise_exception=True)
        data = analytics(request.user, filters.validated_data)
        if request.query_params.get('format') == 'pdf':
            from reports.services import render_pdf
            return FileResponse(render_pdf('SkillForge AI - Classroom Analytics', data['metrics'],
                                {'topic_performance': [f"{t['name']}: {t['score']}%" for t in data['topic_scores']]}),
                                as_attachment=True, filename='skillforge-analytics.pdf')
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(['Student','Email','Average score','Completed','Assigned'])
        for s in data.get('student_summary', []):
            # Prevent spreadsheet formula execution for user-controlled fields.
            safe = lambda v: "'" + v if v.startswith(('=', '+', '-', '@', '\t', '\r')) else v
            writer.writerow([safe(s['name']), safe(s['email']), s['average_score'], s['completed'], s['assigned']])
        response = HttpResponse(buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="skillforge-analytics.csv"'
        return response


class LeaderboardView(APIView):
    def get(self, request):
        trainer = request.user if request.user.role == 'trainer' else request.user.trainer
        if not trainer:
            return Response({'enabled': False, 'rankings': []})
        settings, _ = PlatformSettings.objects.get_or_create(trainer=trainer)
        if not settings.leaderboard_enabled:
            return Response({'enabled': False, 'rankings': []})
        qs = Submission.objects.filter(assignment__trainer=trainer, assignment__results_released=True, status='evaluated', student__is_active=True).select_related('student')
        if request.query_params.get('period') == 'week':
            qs = qs.filter(submitted_at__gte=timezone.now() - timedelta(days=7))
        best = {}
        for s in qs:
            key = (s.student_id, s.assignment_id)
            if key not in best or s.score > best[key].score:
                best[key] = s
        scores = {}
        for s in best.values():
            entry = scores.setdefault(s.student_id, {'student_id':s.student_id, 'name':s.student.name, 'points':0, 'completed':0, 'badges':set()})
            entry['points'] += float(s.score)
            entry['completed'] += 1
            entry['badges'].add('First Assignment Completed')
            if s.percentage == 100:
                entry['badges'].add('Perfect Score')
            if entry['completed'] >= 5:
                entry['badges'].add('Consistent Learner')
        rankings = sorted(scores.values(), key=lambda x:(-x['points'], x['student_id']))[:100]
        for index, row in enumerate(rankings, 1):
            row['rank'] = index
            row['badges'] = sorted(row['badges'])
        return Response({'enabled':True, 'rankings':rankings})
