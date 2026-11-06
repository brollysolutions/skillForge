from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from accounts.models import User


class Command(BaseCommand):
    help = 'Create the single platform administrator for email-only sign-in.'

    def add_arguments(self, parser):
        parser.add_argument('email')
        parser.add_argument('--name', required=True)

    def handle(self, *args, **options):
        email = options['email'].strip().lower()
        try:
            validate_email(email)
        except ValidationError:
            raise CommandError('Provide a valid email address.')
        if User.objects.filter(role='admin').exists():
            raise CommandError('An admin already exists. Only one admin is permitted.')
        if User.objects.filter(email=email).exists():
            raise CommandError('This email belongs to an existing account.')
        User.objects.create_user(email, name=options['name'], role='admin', is_staff=True, is_superuser=True)
        self.stdout.write(self.style.SUCCESS('Admin access granted. Sign in with this email. No email was sent.'))
