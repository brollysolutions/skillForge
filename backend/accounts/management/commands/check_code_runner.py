from django.core.management.base import BaseCommand, CommandError
from core.api import ServiceUnavailable
from code_execution.service import run_code, execution_provider


class Command(BaseCommand):
    help = 'Verify the selected external code runner using small fixed Python probes.'

    def add_arguments(self, parser):
        parser.add_argument('--check-limits', action='store_true', help='Also test timeout and output-limit handling (Piston).')

    def handle(self, *args, **options):
        try:
            result = run_code('print(int(input()) + 1)', '41', '42')
            if not result['accepted'] or result['stdout'].strip() != '42':
                raise CommandError('The runner did not pass the input/output probe.')
            self.stdout.write(self.style.SUCCESS(f'{execution_provider()} Python input/output check passed.'))
            if options['check_limits']:
                timeout = run_code('while True:\n    pass')
                if timeout['status'] != 'Time Limit Exceeded':
                    raise CommandError('CPU/time limit probe failed. Do not accept student runs until corrected.')
                output = run_code('print("x" * 100000)')
                if output['status'] != 'Output Limit Exceeded':
                    raise CommandError('Output limit probe failed. Check the runner output limits.')
                self.stdout.write(self.style.SUCCESS('Timeout and output-limit probes passed.'))
        except ServiceUnavailable as error:
            raise CommandError(str(error.detail)) from None
