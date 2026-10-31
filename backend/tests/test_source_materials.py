import json
from pathlib import Path
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from accounts.models import User
from courses.models import Course
from materials.extraction import extract, MAX_TEXT
from materials.models import StudyMaterial


def notebook(cells, **extra):
    return json.dumps({'nbformat': 4, 'nbformat_minor': 5, 'metadata': {}, 'cells': cells, **extra}).encode()


class SourceExtractionTests(SimpleTestCase):
    def test_python_preserves_indentation_strings_and_never_executes(self):
        source = 'import os\r\nos.remove("must-not-run")\r\nfor key in data:\r\n    print("two  spaces", key)\r\n\t# tab\r\n'
        upload = SimpleUploadedFile('DICTIONARIES.PY', source.encode())
        with patch('os.remove') as remove:
            self.assertEqual(extract(upload), source.replace('\r\n', '\n').strip('\n'))
            remove.assert_not_called()
        self.assertEqual(upload.read(), source.encode())

    def test_python_supports_encoding_cookie_and_bom(self):
        source = '# coding: latin-1\n# café\nvalues = {}'
        self.assertEqual(extract(SimpleUploadedFile('lesson.py', source.encode('latin-1'))), source)
        self.assertEqual(extract(SimpleUploadedFile('lesson.py', b'\xef\xbb\xbfvalues = {}')), 'values = {}')

    def test_notebook_extracts_sources_in_order_and_ignores_outputs(self):
        cells = [
            {'cell_type': 'markdown', 'source': ['# Dictionaries\n', 'Store key-value pairs.'], 'attachments': {'secret-image': 'ignored'}},
            {'cell_type': 'code', 'source': 'for key in data:\n    print(key)', 'outputs': [{'text': 'PRIVATE_OUTPUT'}], 'execution_count': 7},
            {'cell_type': 'raw', 'source': 'Practice: count words.'},
        ]
        text = extract(SimpleUploadedFile('lesson.ipynb', notebook(cells, metadata={'token': 'PRIVATE_METADATA'})))
        self.assertEqual(text, '[Cell 1: markdown]\n# Dictionaries\nStore key-value pairs.\n\n[Cell 2: code]\nfor key in data:\n    print(key)\n\n[Cell 3: raw]\nPractice: count words.')
        for excluded in ['PRIVATE_OUTPUT', 'PRIVATE_METADATA', 'secret-image']:
            self.assertNotIn(excluded, text)

    def test_rejects_invalid_notebooks(self):
        invalid = [b'not json', b'[]', notebook([], nbformat=3), notebook({}),
                   notebook([None]), notebook([{'cell_type': 'code', 'source': [1]}]),
                   notebook([{'cell_type': 'unknown', 'source': 'text'}]),
                   notebook([{'cell_type': 'code', 'source': 'binary\x00content'}]),
                   notebook([{'cell_type': 'code', 'source': '\ud800'}])]
        for raw in invalid:
            with self.subTest(raw=raw), self.assertRaises(ValidationError):
                extract(SimpleUploadedFile('lesson.ipynb', raw))

    def test_rejects_empty_sources_even_if_notebook_has_outputs(self):
        for name, raw in [('empty.py', b' \n\t'), ('empty.ipynb', notebook([])),
                          ('outputs.ipynb', notebook([{'cell_type': 'code', 'source': '', 'outputs': [{'text': 'Result'}]}]))]:
            with self.subTest(name=name), self.assertRaisesMessage(ValidationError, 'No readable text or code'):
                extract(SimpleUploadedFile(name, raw))

    def test_rejects_binary_python_and_invalid_encoding(self):
        for raw in [b'MZ\x00\x01', b'\xff\xfe\x00', b'# coding: unknown-encoding\nprint(1)']:
            with self.subTest(raw=raw), self.assertRaises(ValidationError):
                extract(SimpleUploadedFile('lesson.py', raw))

    def test_source_upload_and_extraction_limits(self):
        for name, raw in [('large.py', b'x' * (MAX_TEXT + 1)),
                          ('large.ipynb', notebook([{'cell_type': 'code', 'source': 'x' * MAX_TEXT}]))]:
            with self.subTest(name=name):
                with override_settings(MAX_UPLOAD_BYTES=10), self.assertRaisesMessage(ValidationError, 'File exceeds'):
                    extract(SimpleUploadedFile(name, raw))
                with self.assertRaisesMessage(ValidationError, '120,000'):
                    extract(SimpleUploadedFile(name, raw))
        with self.assertRaisesMessage(ValidationError, '2,000 cells'):
            extract(SimpleUploadedFile('large.ipynb', notebook([{'cell_type': 'code', 'source': ''}] * 2001)))


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
                   MEDIA_ROOT=Path(__file__).resolve().parents[2] / '.task-temp' / 'test-source-media')
class SourceUploadTests(TestCase):
    def setUp(self):
        self.trainer = User.objects.create_user('trainer@materials.test', 'password', role='trainer')
        self.other = User.objects.create_user('other@materials.test', 'password', role='trainer')
        self.student = User.objects.create_user('student@materials.test', 'password', trainer=self.trainer)
        self.course = Course.objects.create(title='Python', trainer=self.trainer)
        self.api = APIClient()
        self.api.force_authenticate(self.trainer)

    def tearDown(self):
        for material in StudyMaterial.objects.all():
            material.file.delete(save=False)

    def test_upload_review_original_download_and_permissions(self):
        for filename, raw in [('dictionaries.py', b'for key in data:\n    print(key)'),
                              ('dictionaries.ipynb', notebook([{'cell_type': 'code', 'source': 'for key in data:\n    print(key)'}]))]:
            with self.subTest(filename=filename):
                self.api.force_authenticate(self.trainer)
                result = self.api.post('/api/materials/upload/', {'title': 'Dictionaries', 'course': self.course.pk,
                                       'file': SimpleUploadedFile(filename, raw)}, format='multipart')
                self.assertEqual(result.status_code, 201, result.data)
                self.assertIn('\n    print(key)', result.data['extracted_text'])
                self.assertEqual(result.data['original_filename'], filename)
                self.assertEqual(result.data['size_bytes'], len(raw))
                self.assertFalse(result.data['analysis_approved'])
                url = f"/api/materials/{result.data['id']}/"
                self.assertEqual(self.api.get(url).status_code, 200)
                download = self.api.get(url + 'download/')
                self.assertEqual(b''.join(download.streaming_content), raw)
                download.close()
                for user, status in [(self.student, 403), (self.other, 404)]:
                    self.api.force_authenticate(user)
                    self.assertEqual(self.api.get(url).status_code, status)
                    self.assertEqual(self.api.get(url + 'download/').status_code, status)

    def test_invalid_notebook_does_not_create_material(self):
        result = self.api.post('/api/materials/upload/', {'title': 'Invalid', 'course': self.course.pk,
                               'file': SimpleUploadedFile('invalid.ipynb', b'not json')}, format='multipart')
        self.assertEqual(result.status_code, 400)
        self.assertIn('file', result.data)
        self.assertFalse(StudyMaterial.objects.exists())
