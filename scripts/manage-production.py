"""Django management commands using the server's private production environment."""
import os
from pathlib import Path
import sys

from dotenv import load_dotenv

root = Path(__file__).resolve().parents[1]
environment = Path('/etc/skillforge/skillforge.env')
if not environment.is_file():
    raise SystemExit('Production environment file /etc/skillforge/skillforge.env is missing.')
load_dotenv(environment, override=True)
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
sys.path.insert(0, str(root / 'backend'))
from django.core.management import execute_from_command_line
execute_from_command_line([str(root / 'backend' / 'manage.py'), *sys.argv[1:]])
