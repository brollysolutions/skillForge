"""Dispatch to isolated HTTP runners. Never execute student code in Django."""
import base64
import os
import time
import httpx
from core.api import ServiceUnavailable


def _encode(value):
    return base64.b64encode(value.encode()).decode()


def _decode(value):
    try:
        return base64.b64decode(value or '').decode('utf-8', errors='replace')[:16000]
    except Exception:
        return ''


def execution_provider():
    return os.getenv('CODE_EXECUTION_PROVIDER', 'judge0').strip().lower()


def execution_configured():
    variable = {'piston': 'PISTON_URL', 'judge0': 'JUDGE0_URL'}.get(execution_provider())
    return bool(variable and os.getenv(variable, '').strip())


def run_code(source, stdin='', expected=None):
    provider = execution_provider()
    if provider == 'piston':
        from .piston import run_python
        return run_python(source, stdin, expected)
    if provider == 'judge0':
        return run_judge0(source, stdin, expected)
    raise ServiceUnavailable('Unknown code runner. Configure CODE_EXECUTION_PROVIDER as piston or judge0.')


def run_judge0(source, stdin='', expected=None):
    endpoint = os.getenv('JUDGE0_URL', '').rstrip('/')
    if not endpoint:
        raise ServiceUnavailable('Code execution is not configured. Ask your trainer to configure Judge0.')
    headers = {}
    if os.getenv('JUDGE0_API_KEY'):
        headers[os.getenv('JUDGE0_AUTH_HEADER', 'X-Auth-Token')] = os.environ['JUDGE0_API_KEY']
    if os.getenv('JUDGE0_RAPIDAPI_HOST'):
        headers['X-RapidAPI-Host'] = os.environ['JUDGE0_RAPIDAPI_HOST']
    payload = {
        'source_code': _encode(source), 'stdin': _encode(stdin),
        'language_id': int(os.getenv('JUDGE0_PYTHON_LANGUAGE_ID', '71')),
        'cpu_time_limit': 2, 'wall_time_limit': 5, 'memory_limit': 128000,
        'max_file_size': 64, 'max_processes_and_or_threads': 16,
        'enable_network': False, 'number_of_runs': 1,
    }
    if expected is not None:
        payload['expected_output'] = _encode(expected)
    try:
        with httpx.Client(timeout=10, headers=headers, follow_redirects=False) as client:
            response = client.post(f'{endpoint}/submissions', params={'base64_encoded': 'true', 'wait': 'false'}, json=payload)
            response.raise_for_status()
            token = response.json()['token']
            result = None
            for _ in range(20):
                response = client.get(f'{endpoint}/submissions/{token}', params={'base64_encoded': 'true', 'fields': 'stdout,stderr,compile_output,status,time,memory'})
                response.raise_for_status()
                result = response.json()
                if result['status']['id'] > 2:
                    break
                time.sleep(0.5)
            if not result or result['status']['id'] <= 2 or result['status']['id'] >= 13:
                raise ServiceUnavailable('The execution service could not complete this run. Try again.')
            status_id = result['status']['id']
            stdout = _decode(result.get('stdout'))
            # Compare deterministically in application code. Only trailing whitespace is ignored.
            accepted = status_id == 3 and (expected is None or stdout.rstrip() == expected.rstrip())
            status = 'Accepted' if accepted else ('Wrong Answer' if status_id in [3,4] else result['status']['description'])
            return {'status': status, 'accepted': accepted, 'stdout': stdout,
                    'stderr': _decode(result.get('stderr')), 'compile_output': _decode(result.get('compile_output')),
                    'time': result.get('time'), 'memory': result.get('memory')}
    except ServiceUnavailable:
        raise
    except (httpx.HTTPError, ValueError, KeyError):
        raise ServiceUnavailable('The execution service is unavailable. Your work has been preserved.')


def evaluate_code(source, question):
    passed = total = passed_weight = weight = 0
    sample_results = []
    for case in question.test_cases.all():
        result = run_code(source, case.input, case.expected_output)
        total += 1
        weight += case.weight
        if result['accepted']:
            passed += 1
            passed_weight += case.weight
        if not case.is_hidden:
            sample_results.append(result)
    # Never persist hidden inputs, expected outputs, stdout, stderr, or timings in student-facing execution data.
    return {'passed': passed, 'total': total, 'passed_weight': passed_weight, 'weight': weight, 'samples': sample_results}
