from collections import defaultdict
from decimal import Decimal
from django.utils import timezone
from accounts.models import User
from courses.models import Course, Topic
from assignments.models import Assignment, AssignmentAccess
from submissions.models import Submission
from core.models import AuditLog


def percent(numerator, denominator):
    return round(float(numerator) * 100 / denominator, 2) if denominator else 0


def analytics(user, filters=None):
    filters = filters or {}
    trainer = user if user.role == 'trainer' else user.trainer
    assignments = Assignment.objects.filter(trainer=trainer)
    access = AssignmentAccess.objects.filter(assignment__trainer=trainer, is_active=True)
    submissions = Submission.objects.filter(assignment__trainer=trainer).select_related('assignment__topic', 'student')
    students = User.objects.filter(trainer=trainer, role='student')
    if user.role == 'student':
        access = access.filter(student=user)
        assignments = assignments.filter(access_records__student=user, access_records__is_active=True, status__in=['published','closed'])
        submissions = submissions.filter(student=user)
        students = students.filter(pk=user.pk)
    for key in ['course', 'topic', 'assignment', 'student']:
        value = filters.get(key)
        if not value:
            continue
        if key == 'student':
            access, submissions, students = access.filter(student_id=value), submissions.filter(student_id=value), students.filter(pk=value)
        elif key == 'assignment':
            assignments, access, submissions = assignments.filter(pk=value), access.filter(assignment_id=value), submissions.filter(assignment_id=value)
        else:
            assignments = assignments.filter(**{f'{key}_id': value})
            access = access.filter(**{f'assignment__{key}_id': value})
            submissions = submissions.filter(**{f'assignment__{key}_id': value})
    for key, lookup in [('date_from','submitted_at__date__gte'),('date_to','submitted_at__date__lte')]:
        if filters.get(key):
            submissions = submissions.filter(**{lookup: filters[key]})
    if user.role == 'student':
        access = access.filter(assignment__in=assignments)
        submissions = submissions.filter(assignment__in=assignments)
    all_submissions = list(submissions.order_by('started_at'))
    verified = [s for s in all_submissions if s.status == 'evaluated' and (user.role == 'trainer' or s.assignment.results_released)]
    # One best result per student/assignment prevents multiple attempts inflating totals.
    best = {}
    for sub in verified:
        key = (sub.student_id, sub.assignment_id)
        if key not in best or sub.percentage > best[key].percentage:
            best[key] = sub
    results = list(best.values())
    completed = set((s.student_id, s.assignment_id) for s in all_submissions if s.status in ['submitted','evaluated'])
    eligible = set(access.values_list('student_id', 'assignment_id'))
    completed_assigned = completed & eligible
    overdue = sum((a.student_id, a.assignment_id) not in completed for a in access.select_related('assignment')
                  if a.assignment.deadline and a.assignment.deadline < timezone.now())
    topic_scores, difficulty_scores, trends, activity = defaultdict(list), defaultdict(list), defaultdict(list), defaultdict(int)
    for s in results:
        topic_scores[(s.assignment.topic_id, s.assignment.topic.title if s.assignment.topic else 'General')].append(float(s.percentage))
        difficulty_scores[s.assignment.difficulty].append(float(s.percentage))
    for s in verified:
        if s.submitted_at:
            trends[s.submitted_at.date().isoformat()].append(float(s.percentage))
    for s in all_submissions:
        activity[s.started_at.date().isoformat()] += 1
    distribution = [{'name': '0–39', 'count': 0}, {'name': '40–59', 'count': 0}, {'name': '60–79', 'count': 0}, {'name': '80–100', 'count': 0}]
    for s in results:
        distribution[0 if s.percentage < 40 else 1 if s.percentage < 60 else 2 if s.percentage < 80 else 3]['count'] += 1
    coding_passed = coding_total = 0
    for s in results:
        for r in s.responses.all():
            coding_passed += r.execution.get('passed', 0)
            coding_total += r.execution.get('total', 0)
    recent = sorted(all_submissions, key=lambda s:s.started_at, reverse=True)[:8]
    upcoming = assignments.filter(status='published', deadline__gte=timezone.now()).order_by('deadline')[:5]
    result = {
        'metrics': {
            'total_students': students.count(), 'active_students': students.filter(is_active=True).count(),
            'total_courses': Course.objects.filter(trainer=trainer).count() if user.role == 'trainer' else assignments.values('course').distinct().count(),
            'total_topics': Topic.objects.filter(course__trainer=trainer).count() if user.role == 'trainer' else assignments.exclude(topic=None).values('topic').distinct().count(),
            'total_assignments': assignments.count(), 'published_assignments': assignments.filter(status='published').count(),
            'total_submissions': sum(s.status in ['submitted','evaluated'] for s in all_submissions),
            'pending_evaluations': sum(s.status == 'submitted' for s in all_submissions),
            'assigned_assignments': len(eligible), 'completed_assignments': len(completed_assigned),
            'pending_assignments': len(eligible - completed_assigned), 'overdue_assignments': overdue,
            'average_score': round(sum(float(s.percentage) for s in results) / len(results), 2) if results else 0,
            'total_points': round(sum(float(s.score) for s in results), 2),
            'completion_percentage': percent(len(completed_assigned), len(eligible)),
            'coding_accuracy': percent(coding_passed, coding_total),
            'coding_tests_passed': coding_passed, 'coding_tests_total': coding_total,
        },
        'topic_scores': [{'id': k[0], 'name': k[1], 'score': round(sum(v)/len(v), 2), 'assessments': len(v)} for k,v in topic_scores.items()],
        'difficulty_scores': [{'name': k.title(), 'score': round(sum(v)/len(v), 2)} for k,v in difficulty_scores.items()],
        'trends': [{'date': k, 'score': round(sum(v)/len(v), 2)} for k,v in sorted(trends.items())],
        'activity': [{'date':k, 'attempts':v} for k,v in sorted(activity.items())][-30:],
        'distribution': distribution,
        'recent_submissions': [{'id': s.pk, 'assignment': s.assignment.title, 'student': s.student.name,
            'status': s.status if user.role == 'trainer' or s.assignment.results_released else ('in_progress' if s.status == 'in_progress' else 'submitted'),
            'percentage': float(s.percentage) if s in verified else None, 'date': s.started_at} for s in recent],
        'upcoming': [{'id': a.pk, 'title': a.title, 'deadline': a.deadline, 'difficulty': a.difficulty} for a in upcoming],
    }
    if user.role == 'trainer':
        result['recent_activity'] = list(AuditLog.objects.filter(actor__in=[user.pk, *students.values_list('id', flat=True)]).order_by('-created_at').values('action','created_at')[:10])
        per_student = defaultdict(list)
        for s in results:
            per_student[s.student_id].append(float(s.percentage))
        result['student_summary'] = [{'id': s.pk, 'name': s.name, 'email': s.email,
            'average_score': round(sum(per_student[s.pk])/len(per_student[s.pk]), 2) if per_student[s.pk] else None,
            'completed': sum(student_id == s.pk for student_id, _ in completed_assigned),
            'assigned': sum(student_id == s.pk for student_id, _ in eligible)} for s in students]
    return result
