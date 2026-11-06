import io
import re
from xml.sax.saxutils import escape
from django.db import transaction
from rest_framework.exceptions import ValidationError
from ai_services.providers import generate_json
from ai_services.schemas import ReportNarrative
from analytics.services import analytics
from assignments.views import accessible_assignments
from courses.models import Topic
from submissions.models import Submission
from core.models import audit
from .models import PerformanceReport, LearningRecommendation


def build_report(trainer, student):
    snapshot = analytics(student, {'trainer': trainer.pk})
    submissions = list(Submission.objects.filter(student=student, assignment__trainer=trainer, status='evaluated', assignment__results_released=True)
                       .select_related('assignment').prefetch_related('responses__question').order_by('-submitted_at')[:100])
    if not submissions:
        raise ValidationError('Release at least one evaluated assessment result before generating a report.')
    assignments = accessible_assignments(student).filter(trainer=trainer, status='published', results_released=False)
    from core.access import visible_courses
    topics = Topic.objects.filter(course__in=visible_courses(trainer))
    evidence = {
        'metrics': snapshot['metrics'], 'topic_scores': snapshot['topic_scores'], 'trends': snapshot['trends'],
        'history': [{'submission_id': s.pk, 'assignment_id': s.assignment_id, 'topic_id': s.assignment.topic_id,
                     'score': str(s.score), 'percentage': str(s.percentage), 'attempt': s.attempt, 'duration_seconds': s.duration_seconds,
                     'date': s.submitted_at.isoformat(), 'questions': [{'type': r.question.type, 'title': r.question.title,
                     'score': str(r.score), 'max_marks': str(r.question.marks), 'passed': r.execution.get('passed'),
                     'total': r.execution.get('total'), 'trainer_feedback': r.feedback} for r in s.responses.all()]} for s in submissions],
        'available_topics': list(topics.values('id','title','learning_objectives')),
        'available_assignments': list(assignments.values('id','title','topic_id','difficulty')),
    }
    narrative = generate_json(trainer, 'gemini', 'performance.report', ReportNarrative,
        'Interpret only supplied evidence. Do not invent history, statistics or assessment links. '
        'Numerical metrics are rendered separately by Django: use qualitative prose without numerical claims, percentages, or counts. '
        'Use only supplied topic IDs and available assignment IDs. Cite supporting submission IDs in evidence_submission_ids. '
        'Identify uncertainty and insufficient evidence. Recommend realistic next learning steps.', evidence)
    allowed_topics = set(topics.values_list('id', flat=True))
    allowed_assignments = set(assignments.values_list('id', flat=True))
    if not set(narrative['evidence_submission_ids']).issubset({s.pk for s in submissions}):
        raise ValidationError('Report references unsupported evidence. Regenerate it.')
    for rec in narrative['recommendations']:
        if rec['topic_id'] not in allowed_topics or not set(rec['assignment_ids']).issubset(allowed_assignments):
            raise ValidationError('Report contains recommendations outside the available course content. Regenerate it.')
    # Reject numeric claims in prose; the UI displays verified Django metrics separately.
    prose = [narrative[k] for k in ['overall_performance','coding_analysis','progress_analysis','trainer_feedback']]
    prose += narrative['strengths'] + narrative['weaknesses']
    prose += [r['reason'] for r in narrative['recommendations']] + [step for r in narrative['recommendations'] for step in r['steps']]
    if any(re.search(r'\b\d+(?:\.\d+)?\s*(?:%|percent|points|marks|submissions|assignments|attempts|scores?)\b|\d+\s*%', text, re.I) for text in prose):
        raise ValidationError('Report includes numerical claims in narrative. Regenerate before publication.')
    with transaction.atomic():
        report = PerformanceReport.objects.create(trainer=trainer, student=student, metrics=snapshot['metrics'], evidence=evidence, narrative=narrative)
        for rec in narrative['recommendations']:
            record = LearningRecommendation.objects.create(report=report, topic_id=rec['topic_id'], reason=rec['reason'], steps=rec['steps'], difficulty=rec['difficulty'])
            record.assignments.set(rec['assignment_ids'])
        audit(trainer, 'report.generated', report)
    return report


def render_pdf(title, metrics, sections):
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    buffer = io.BytesIO()
    styles = getSampleStyleSheet()
    story = [Paragraph(escape(title), styles['Title']), Spacer(1, 16)]
    rows = [[key.replace('_', ' ').title(), str(value)] for key,value in metrics.items()]
    table = Table(rows, colWidths=[330, 120])
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#f4f6fa')), ('BOTTOMPADDING',(0,0),(-1,-1),8), ('TOPPADDING',(0,0),(-1,-1),8)]))
    story.extend([table, Spacer(1,20)])
    for title, value in sections.items():
        story.append(Paragraph(escape(title.replace('_',' ').title()), styles['Heading2']))
        values = value if isinstance(value, list) else [value]
        for text in values:
            story.append(Paragraph(escape(str(text)).replace('\n','<br/>'), styles['BodyText']))
            story.append(Spacer(1,8))
    SimpleDocTemplate(buffer, title='SkillForge AI Performance Report').build(story)
    buffer.seek(0)
    return buffer
