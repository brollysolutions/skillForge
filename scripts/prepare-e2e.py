"""Create an isolated, disposable database for opt-in full-stack tests."""
import json
import os
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
trainer, _ = User.objects.get_or_create(email='trainer@browser.test', defaults={'name':'Alex Morgan', 'role':'trainer'})
trainer.set_unusable_password()
trainer.save()
student, _ = User.objects.get_or_create(email='student@browser.test', defaults={'name':'Jordan Lee', 'role':'student', 'trainer':trainer})
student.set_unusable_password()
student.save()
admin, _ = User.objects.get_or_create(email='admin@browser.test', defaults={'name':'Admin Test', 'role':'admin'})
sales, _ = User.objects.get_or_create(email='sales@browser.test', defaults={'name':'Sales Test', 'role':'sales'})
(temporary / 'browser-credentials.json').write_text(json.dumps({'trainer':trainer.email, 'student':student.email,
    'admin':admin.email, 'sales':sales.email, 'student_id':student.pk}))
print('Prepared isolated test database and email access fixture under .task-temp. The normal database was not changed.')

# Representative detail pages use explicitly marked fixtures in this same disposable DB.
import runpy
runpy.run_path(str(root / "scripts" / "prepare-ui-details.py"))
