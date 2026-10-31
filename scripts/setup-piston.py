"""Run on the Piston host to install Python through its loopback API."""
import argparse
import json
import re
import sys
from urllib.error import URLError
from urllib.request import Request, urlopen

API = 'http://127.0.0.1:2000/api/v2'


def request(path, body=None):
    payload = json.dumps(body).encode() if body is not None else None
    req = Request(API + path, data=payload, headers={'Content-Type': 'application/json'})
    with urlopen(req, timeout=600 if body is not None else 20) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install-python', action='store_true', help='Install the newest Python 3 package if none is installed.')
    args = parser.parse_args()
    runtimes = request('/runtimes')
    installed = [item for item in runtimes if item.get('language') == 'python' and str(item.get('version', '')).startswith('3.')]
    if not installed:
        if not args.install_python:
            raise ValueError('Python is not installed. Re-run with --install-python on the runner host.')
        packages = [item for item in request('/packages') if item.get('language') == 'python'
                    and re.fullmatch(r'3\.\d+\.\d+', str(item.get('language_version', '')))]
        if not packages:
            raise ValueError('The Piston package repository has no Python 3 package available.')
        selected = max(packages, key=lambda item: tuple(map(int, item['language_version'].split('.'))))
        version = selected['language_version']
        print(f'Installing Python {version} inside Piston. This may take several minutes.', flush=True)
        request('/packages', {'language': 'python', 'version': version})
        installed = [item for item in request('/runtimes') if item.get('language') == 'python' and item.get('version') == version]
        if not installed:
            raise ValueError('Python package installation did not produce a usable runtime.')
    print('Available Python versions:', ', '.join(item['version'] for item in installed))
    print('Next: connect Django to this host and run manage.py check_code_runner --check-limits.')


if __name__ == '__main__':
    try:
        main()
    except (URLError, TimeoutError, ValueError, KeyError, TypeError) as error:
        print(f'Piston setup failed ({type(error).__name__}). Check the runner container and its package-network access.', file=sys.stderr)
        sys.exit(1)
