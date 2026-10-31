import json
import os
from unittest.mock import patch

import httpx
from django.test import SimpleTestCase
from code_execution.service import run_code, evaluate_code
from core.api import ServiceUnavailable

RealClient = httpx.Client


def stage(**changes):
    return {'stdout': '42\n', 'stderr': '', 'code': 0, 'signal': None, 'status': None,
            'wall_time': 20, 'memory': 2000000, **changes}


@patch.dict(os.environ, {'CODE_EXECUTION_PROVIDER': 'piston', 'PISTON_URL': 'https://piston.test/api/v2',
                        'PISTON_PYTHON_VERSION': '3.x', 'PISTON_API_TOKEN': ''})
class PistonTests(SimpleTestCase):
    def execute(self, result, *, expected='42', status_code=200):
        def transport(request):
            self.request = request
            return httpx.Response(status_code, json=result)
        with patch('code_execution.piston.httpx.Client', side_effect=lambda **kwargs: RealClient(transport=httpx.MockTransport(transport), **kwargs)):
            return run_code('print(int(input()) + 1)', '41', expected)

    def test_payload_limits_and_result_units(self):
        result = self.execute({'language': 'python', 'run': stage()})
        self.assertTrue(result['accepted'])
        self.assertEqual(result['time'], .02)
        self.assertEqual(result['memory'], 2000)
        payload = json.loads(self.request.content)
        self.assertEqual(str(self.request.url), 'https://piston.test/api/v2/execute')
        self.assertEqual(payload['files'], [{'name': 'solution.py', 'content': 'print(int(input()) + 1)', 'encoding': 'utf8'}])
        self.assertEqual(payload['stdin'], '41')
        self.assertEqual(payload['run_timeout'], 5000)
        self.assertEqual(payload['run_cpu_time'], 2000)
        self.assertEqual(payload['run_memory_limit'], 128000000)
        self.assertNotIn('expected_output', payload)
        self.assertNotIn('Authorization', self.request.headers)

    def test_wrong_answer_and_custom_input(self):
        self.assertEqual(self.execute({'language': 'python', 'run': stage(stdout='wrong')})['status'], 'Wrong Answer')
        self.assertTrue(self.execute({'language': 'python', 'run': stage(stdout='anything')}, expected=None)['accepted'])
        self.assertFalse(self.execute({'language': 'python', 'run': stage(stdout=' 42')})['accepted'])

    def test_student_failures_cannot_earn_marks(self):
        for changes, expected in [({'code': 1, 'status': 'RE'}, 'Runtime Error'),
                                  ({'code': None, 'status': 'TO', 'signal': 'SIGKILL'}, 'Time Limit Exceeded'),
                                  ({'status': 'OL'}, 'Output Limit Exceeded'),
                                  ({'signal': 'SIGSEGV', 'status': 'SG'}, 'Runtime Error')]:
            with self.subTest(changes=changes):
                result = self.execute({'language': 'python', 'run': stage(**changes)})
                self.assertFalse(result['accepted'])
                self.assertEqual(result['status'], expected)

    def test_compile_errors_take_precedence(self):
        result = self.execute({'language': 'python', 'compile': stage(code=1, status='RE', stderr='syntax error'), 'run': stage()})
        self.assertEqual(result['status'], 'Compilation Error')
        self.assertEqual(result['compile_output'], 'syntax error')
        self.assertFalse(result['accepted'])

    def test_invalid_or_internal_results_preserve_attempt(self):
        for data in [{}, [], {'language': 'python', 'run': stage(status='XX')},
                     {'language': 'python', 'run': stage(code=False)},
                     {'language': 'python', 'run': stage(stdout=None)},
                     {'language': 'python', 'run': stage(code=None)},
                     {'language': 'python', 'run': stage(status='UNKNOWN')}]:
            with self.subTest(data=data), self.assertRaises(ServiceUnavailable):
                self.execute(data)

    def test_output_is_bounded_and_never_accepted_after_truncation(self):
        result = self.execute({'language': 'python', 'run': stage(stdout='x' * 16001)}, expected='x' * 16000)
        self.assertEqual(len(result['stdout']), 16000)
        self.assertEqual(result['status'], 'Output Limit Exceeded')
        self.assertFalse(result['accepted'])
        with self.assertRaises(ServiceUnavailable):
            self.execute({'language': 'python', 'run': stage(stdout='x' * 300000)})

    def test_http_errors_do_not_leak_response_bodies(self):
        for code in [400, 401, 403, 404, 429, 500, 302]:
            with self.subTest(code=code), self.assertRaises(ServiceUnavailable) as context:
                self.execute({'message': 'PRIVATE_RUNNER_BODY'}, status_code=code)
            self.assertNotIn('PRIVATE_RUNNER_BODY', str(context.exception))

    def test_no_judge0_fallback_when_piston_is_missing(self):
        with patch.dict(os.environ, {'PISTON_URL': '', 'JUDGE0_URL': 'https://paid.test'}), self.assertRaisesMessage(ServiceUnavailable, 'Piston is not configured'):
            run_code('print(42)')

    def test_network_failure_preserves_work_and_uses_safe_message(self):
        for error, message in [(httpx.ConnectError('secret'), 'Cannot connect'), (httpx.ReadTimeout('secret'), 'did not respond')]:
            def transport(request):
                raise error
            with patch('code_execution.piston.httpx.Client', side_effect=lambda **kwargs: RealClient(transport=httpx.MockTransport(transport), **kwargs)):
                with self.assertRaisesMessage(ServiceUnavailable, message) as context:
                    run_code('print(42)')
                self.assertNotIn('secret', str(context.exception))

    def test_hidden_results_are_redacted_with_piston(self):
        from types import SimpleNamespace
        tests = [SimpleNamespace(input='visible', expected_output='42', is_hidden=False, weight=1),
                 SimpleNamespace(input='HIDDEN_INPUT', expected_output='HIDDEN_EXPECTED', is_hidden=True, weight=3)]
        question = SimpleNamespace(test_cases=SimpleNamespace(all=lambda: tests))
        def transport(request):
            hidden = json.loads(request.content)['stdin'] == 'HIDDEN_INPUT'
            return httpx.Response(200, json={'language': 'python', 'run': stage(stdout='HIDDEN_STDOUT' if hidden else '42')})
        with patch('code_execution.piston.httpx.Client', side_effect=lambda **kwargs: RealClient(transport=httpx.MockTransport(transport), **kwargs)):
            result = evaluate_code('print(input())', question)
        self.assertEqual(result['passed_weight'], 1)
        self.assertEqual(result['weight'], 4)
        self.assertEqual(result['total'], 2)
        self.assertNotIn('HIDDEN', str(result))
