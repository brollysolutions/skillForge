"""Check the real WSGI endpoint without loading or printing credentials."""
import json
from urllib.request import urlopen

with urlopen('http://127.0.0.1:8000/api/health/', timeout=3) as response:
    if response.status != 200 or json.load(response).get('status') != 'ok':
        raise SystemExit(1)
