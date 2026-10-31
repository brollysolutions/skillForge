"""Create an isolated, disposable database for opt-in full-stack tests."""
import json
import os
import secrets
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
temporary = root / '.task-temp'
temporary.mkdir(exist_ok=True)
sys.path.insert(0, str(root / 'backend'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
os.environ['DJANGO_DB_PATH'] = str(temporary / 'browser.sqlite3')
import django
django.setup()
from django.core.management import call_command
from accounts.models import User

call_command('migrate', verbosity=0)
password = secrets.token_urlsafe(24)
trainer, _ = User.objects.get_or_create(email='trainer@browser.test', defaults={'name':'Alex Morgan', 'role':'trainer'})
trainer.set_password(password)
trainer.save()
student, _ = User.objects.get_or_create(email='student@browser.test', defaults={'name':'Jordan Lee', 'role':'student', 'trainer':trainer})
student.set_password(password)
student.save()
(temporary / 'browser-credentials.json').write_text(json.dumps({'trainer':trainer.email, 'student':student.email, 'password':password, 'student_id':student.pk}))
print('Prepared isolated test database and random test credentials under .task-temp. The normal database was not changed.')
