"""Piston's isolated execution API; source is sent as data, never evaluated here."""
import json
import math
import os
from urllib.parse import urlsplit

import httpx
from core.api import ServiceUnavailable

MAX_RESPONSE_BYTES = 256 * 1024
MAX_OUTPUT_CHARS = 16000


def _stage(value):
    if not isinstance(value, dict):
        raise ValueError('Missing execution stage')
    if not isinstance(value.get('stdout'), str) or not isinstance(value.get('stderr'), str):
        raise ValueError('Invalid output')
    code, signal, status = value.get('code'), value.get('signal'), value.get('status')
    if code is not None and type(code) is not int:
        raise ValueError('Invalid exit code')
    if signal is not None and not isinstance(signal, str):
        raise ValueError('Invalid signal')
    if status not in (None, 'RE', 'SG', 'TO', 'OL', 'EL', 'XX'):
        raise ValueError('Invalid execution status')
    if status == 'XX' or (code is None and signal is None and status is None):
        raise ValueError('Execution did not finish')
    if status == 'TO':
        return 'Time Limit Exceeded'
    if status in ('OL', 'EL') or max(len(value['stdout']), len(value['stderr'])) > MAX_OUTPUT_CHARS:
        return 'Output Limit Exceeded'
    if code != 0 or signal or status:
        return 'Runtime Error'
    return 'Accepted'


def _metric(value, divisor):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        return None
    return value / divisor


def run_python(source, stdin='', expected=None):
    endpoint = os.getenv('PISTON_URL', '').strip().rstrip('/')
    if not endpoint:
        raise ServiceUnavailable('Piston is not configured. Ask your trainer to set PISTON_URL for the self-hosted code runner.')
    parsed = urlsplit(endpoint)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ServiceUnavailable('Invalid PISTON_URL. Use the runner API base URL ending in /api/v2.')
    headers = {}
    if os.getenv('PISTON_API_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['PISTON_API_TOKEN']
    payload = {
        'language': 'python', 'version': os.getenv('PISTON_PYTHON_VERSION', '3.x'),
        'files': [{'name': 'solution.py', 'content': source, 'encoding': 'utf8'}],
        'stdin': stdin, 'args': [],
        'run_timeout': 5000, 'compile_timeout': 5000,
        'run_cpu_time': 2000, 'compile_cpu_time': 2000,
        'run_memory_limit': 128000000, 'compile_memory_limit': 128000000,
    }
    try:
        with httpx.Client(timeout=httpx.Timeout(15, connect=5), headers=headers, follow_redirects=False) as client:
            with client.stream('POST', endpoint + '/execute', json=payload) as response:
                response.raise_for_status()
                raw = bytearray()
                for chunk in response.iter_bytes():
                    if len(raw) + len(chunk) > MAX_RESPONSE_BYTES:
                        raise ValueError('Execution response too large')
                    raw.extend(chunk)
        data = json.loads(raw)
        if not isinstance(data, dict) or data.get('language') != 'python':
            raise ValueError('Invalid execution response')
        compile_result = data.get('compile')
        compile_status = _stage(compile_result) if compile_result is not None else 'Accepted'
        if compile_status != 'Accepted':
            stage = compile_result
            status = 'Compilation Error' if compile_status == 'Runtime Error' else compile_status
        else:
            stage = data.get('run')
            status = _stage(stage)
        if status == 'Accepted' and expected is not None and stage['stdout'].rstrip() != expected.rstrip():
            status = 'Wrong Answer'
        return {
            'status': status, 'accepted': status == 'Accepted',
            'stdout': stage['stdout'][:MAX_OUTPUT_CHARS] if compile_status == 'Accepted' else '',
            'stderr': stage['stderr'][:MAX_OUTPUT_CHARS] if compile_status == 'Accepted' else '',
            'compile_output': (stage['stderr'] or stage['stdout'])[:MAX_OUTPUT_CHARS] if compile_status != 'Accepted' else '',
            'time': _metric(stage.get('wall_time'), 1000),
            'memory': _metric(stage.get('memory'), 1000),
        }
    except httpx.TimeoutException:
        raise ServiceUnavailable('Piston did not respond in time. Your work is preserved; retry when the runner is available.')
    except httpx.ConnectError:
        raise ServiceUnavailable('Cannot connect to Piston. Ask your trainer to start the self-hosted runner and check PISTON_URL.')
    except httpx.HTTPStatusError as error:
        status = error.response.status_code
        if status in (401, 403):
            detail = 'Piston access was denied. Check the runner proxy credentials.'
        elif status == 400:
            detail = 'Piston rejected the run. Check that Python is installed and its version and resource limits match the configuration.'
        elif status == 404:
            detail = 'Piston execution endpoint was not found. Check that PISTON_URL ends in /api/v2.'
        elif status == 429:
            detail = 'The code runner is busy. Wait and try again.'
        else:
            detail = 'Piston is unavailable. Your work has been preserved.'
        raise ServiceUnavailable(detail)
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        raise ServiceUnavailable('Piston returned an invalid execution result. Your work has been preserved.')
