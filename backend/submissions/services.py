import unicodedata
from datetime import timedelta
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied
from assignments.models import AssignmentAccess
from core.api import Conflict
from core.models import audit
from .models import Submission, QuestionResponse


def require_access(user, assignment):
    if user.role != 'student' or not AssignmentAccess.objects.filter(assignment=assignment, student=user, is_active=True).exists() or not assignment.trainer.is_active:
        raise PermissionDenied('You do not have access to this assignment.')


def require_open(assignment):
    now = timezone.now()
    if assignment.status != 'published' or assignment.results_released:
        raise ValidationError('This assignment is not accepting attempts.')
    if assignment.starts_at and assignment.starts_at > now:
        raise ValidationError('This assignment has not started yet.')
    if assignment.deadline and assignment.deadline <= now:
        raise ValidationError('The assignment deadline has passed.')


@transaction.atomic
def start_attempt(user, assignment):
    require_access(user, assignment)
    require_open(assignment)
    # Serialize attempt creation per access record on PostgreSQL; SQLite serializes writes.
    access = AssignmentAccess.objects.select_for_update().get(student=user, assignment=assignment)
    AssignmentAccess.objects.filter(pk=access.pk).update(updated_at=timezone.now())
    attempts = Submission.objects.filter(student=user, assignment=assignment)
    current = attempts.filter(status__in=['in_progress', 'grading']).first()
    if current:
        return current
    number = attempts.count() + 1
    if number > assignment.attempts_allowed:
        raise ValidationError('You have used all available attempts.')
    expires = timezone.now() + timedelta(minutes=assignment.duration_minutes)
    if assignment.deadline:
        expires = min(expires, assignment.deadline)
    submission = Submission.objects.create(student=user, assignment=assignment, attempt=number, expires_at=expires)
    QuestionResponse.objects.bulk_create([QuestionResponse(submission=submission, question=q) for q in assignment.questions.all()])
    audit(user, 'attempt.started', submission)
    return submission


def validate_answers(answers, submission):
    if not isinstance(answers, dict) or len(answers) > 50:
        raise ValidationError('Answers must map question IDs to answers.')
    valid_ids = {str(x) for x in submission.assignment.questions.values_list('id', flat=True)}
    if not set(answers).issubset(valid_ids):
        raise ValidationError('An answer references a different assignment.')
    questions = {str(q.pk): q for q in submission.assignment.questions.all()}
    for key, value in answers.items():
        question = questions[key]
        if question.type == 'multiple_select' and value != '' and not isinstance(value, list):
            raise ValidationError('Multiple-select answers must be lists.')
        if question.type != 'multiple_select' and not isinstance(value, str):
            raise ValidationError('This question requires a text answer.')
        if question.type == 'mcq' and value and value not in question.options:
            raise ValidationError('Choose a valid option.')
        if question.type == 'multiple_select' and isinstance(value, list):
            if any(not isinstance(v, str) for v in value) or not set(value).issubset(set(question.options)) or len(value) != len(set(value)):
                raise ValidationError('Choose distinct valid options.')
        if isinstance(value, str) and len(value) <= 50000:
            continue
        if isinstance(value, list) and len(value) <= 20 and all(isinstance(v, str) and len(v) <= 2000 for v in value):
            continue
        raise ValidationError('Answers must be text (50,000 characters maximum) or selected options.')
    return answers


@transaction.atomic
def save_answers(user, submission, answers):
    require_access(user, submission.assignment)
    require_open(submission.assignment)
    locked = Submission.objects.select_for_update().get(pk=submission.pk)
    if locked.status != 'in_progress' or locked.expires_at <= timezone.now():
        raise ValidationError('This attempt is no longer editable. Submit your saved answers.')
    # A conditional write also guards SQLite against concurrent finalization.
    if not Submission.objects.filter(pk=locked.pk, status='in_progress').update(updated_at=timezone.now()):
        raise Conflict('This attempt is being submitted.')
    for qid, answer in validate_answers(answers, locked).items():
        QuestionResponse.objects.filter(submission=locked, question_id=qid).update(answer=answer)


def normalized(value):
    return ' '.join(unicodedata.normalize('NFKC', str(value)).casefold().split())


def evaluate_response(response):
    q, answer = response.question, response.answer
    response.score = Decimal('0')
    response.status = 'evaluated'
    if answer in ['', [], None]:
        response.feedback = 'No answer submitted.'
    elif q.type == 'mcq':
        response.score = q.marks if answer == q.correct_answer[0] else Decimal('0')
    elif q.type == 'multiple_select':
        chosen = set(answer) if isinstance(answer, list) else set()
        correct = set(q.correct_answer)
        if chosen == correct:
            response.score = q.marks
        elif q.marking_policy == 'partial':
            response.score = q.marks * Decimal(max(0, len(chosen & correct) - len(chosen - correct))) / Decimal(len(correct))
    elif q.type == 'fill_blank':
        response.score = q.marks if normalized(answer) in {normalized(v) for v in q.correct_answer} else Decimal('0')
    elif q.type == 'output_prediction':
        matched = any(answer.rstrip() == expected.rstrip() for expected in q.correct_answer)
        response.score = q.marks if matched else Decimal('0')
        response.execution = {'passed': int(matched), 'total': 1, 'samples': [{
            'accepted': matched, 'status': 'Accepted' if matched else 'Wrong Answer',
            'expected_output': q.correct_answer[0], 'stdout': answer, 'stderr': ''}]}
    elif q.type in ['coding', 'debugging']:
        if not isinstance(answer, str):
            raise ValidationError('Code must be text.')
        from code_execution.service import evaluate_code
        response.execution = evaluate_code(answer, q)
        response.score = q.marks * Decimal(response.execution['passed_weight']) / Decimal(response.execution['weight'])
    else:
        response.status = 'pending_review'
        response.feedback = 'Awaiting trainer review.'
    response.score = Decimal(str(response.score)).quantize(Decimal('0.01'))
    return response


def recalculate(submission):
    # Do not use a possibly prefetched relation from the read-only API queryset.
    responses = list(QuestionResponse.objects.filter(submission_id=submission.pk))
    submission.score = sum((r.score for r in responses), Decimal('0'))
    submission.percentage = (submission.score * 100 / submission.assignment.total_marks).quantize(Decimal('0.01')) if submission.assignment.total_marks else Decimal('0')
    submission.status = 'submitted' if any(r.status == 'pending_review' for r in responses) else 'evaluated'
    submission.save(update_fields=['score', 'percentage', 'status', 'updated_at'])


def finalize(user, submission, answers=None, *, require_correct=False):
    require_access(user, submission.assignment)
    if submission.student_id != user.pk:
        raise PermissionDenied('This attempt belongs to another student.')
    if require_correct:
        questions = list(submission.assignment.questions.all())
        if len(questions) != 1 or questions[0].type not in ['coding', 'debugging']:
            raise ValidationError('Check and complete is available for single Python tasks.')
    if submission.status in ['submitted', 'evaluated']:
        return submission  # Retry-safe; no second execution or duplicate attempt.
    if require_correct:
        require_open(submission.assignment)
        if submission.expires_at <= timezone.now():
            raise ValidationError('Your time has ended. Submit your saved answers.')
    if answers is not None:
        save_answers(user, submission, answers)
    if not Submission.objects.filter(pk=submission.pk, student=user, status='in_progress').update(status='grading', updated_at=timezone.now()):
        raise Conflict('This attempt is already being processed.')
    try:
        responses = [evaluate_response(r) for r in submission.responses.select_related('question').prefetch_related('question__test_cases')]
        if require_correct:
            submission.check_results = responses[0].execution.get('samples', [])
            execution = responses[0].execution
            if not execution.get('total') or execution.get('passed') != execution['total']:
                Submission.objects.filter(pk=submission.pk, status='grading').update(status='in_progress')
                submission.status = 'in_progress'
                return submission
        with transaction.atomic():
            QuestionResponse.objects.bulk_update(responses, ['score', 'status', 'feedback', 'execution'])
            submission.submitted_at = timezone.now()
            submission.duration_seconds = max(0, int((min(submission.submitted_at, submission.expires_at) - submission.started_at).total_seconds()))
            submission.save(update_fields=['submitted_at', 'duration_seconds'])
            recalculate(submission)
            audit(user, 'attempt.submitted', submission)
    except Exception:
        Submission.objects.filter(pk=submission.pk, status='grading').update(status='in_progress')
        raise
    return submission
