from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from submissions.models import Submission
from core.models import audit


class Command(BaseCommand):
    help = 'Recover attempts left in grading after a worker crash. Run only after confirming workers are no longer processing them.'

    def add_arguments(self, parser):
        parser.add_argument('--older-than-minutes', type=int, default=30)
        parser.add_argument('--apply', action='store_true', help='Apply recovery; otherwise print the count only.')

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(minutes=max(options['older_than_minutes'], 30))
        stuck = Submission.objects.filter(status='grading', updated_at__lt=cutoff)
        count = stuck.count()
        if options['apply']:
            for sub in stuck:
                updated = Submission.objects.filter(pk=sub.pk, status='grading', updated_at__lt=cutoff).update(status='in_progress')
                if updated:
                    audit(None, 'grading.recovered', sub)
        self.stdout.write(f'{count} stale grading attempts found. ' + ('Recovery applied.' if options['apply'] else 'Dry run; no changes made.'))
