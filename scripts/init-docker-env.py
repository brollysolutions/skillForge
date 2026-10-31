"""Create the Docker environment once, without copying local development secrets."""
import os
from pathlib import Path
import secrets

root = Path(__file__).resolve().parents[1]
destination = root / '.env'
content = (root / '.env.example').read_text(encoding='utf-8')
content = content.replace('DJANGO_SECRET_KEY=\n', f'DJANGO_SECRET_KEY={secrets.token_urlsafe(64)}\n', 1)
try:
    descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
except FileExistsError:
    raise SystemExit('.env already exists; kept unchanged. Edit it to configure your integrations.')
with os.fdopen(descriptor, 'w', encoding='utf-8', newline='\n') as stream:
    stream.write(content)
print('Created .env with a new secret. Edit .env to set your provider keys and private runner URL.')
