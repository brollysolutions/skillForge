import io
import os
from decimal import Decimal
from unittest.mock import MagicMock, patch
from django.test import TestCase, override_settings
from rest_framework.exceptions import ValidationError
from accounts.models import User
from courses.models import Course
from assignments.models import Assignment, Question
from submissions.models import Submission, QuestionResponse
from submissions.services import evaluate_response
from materials.extraction import extract, chunks
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from core.models import AIUsageLog
from core.api import ServiceUnavailable


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class ServiceTests(TestCase):
    def setUp(self):
        self.trainer=User.objects.create_user('trainer@example.com','Password!42',name='Trainer',role='trainer')
        self.course=Course.objects.create(trainer=self.trainer,title='Python')
        self.assignment=Assignment.objects.create(trainer=self.trainer,course=self.course,title='Quiz')
        self.student=User.objects.create_user('student@example.com','Password!42',name='Student',trainer=self.trainer)
        self.submission=Submission.objects.create(assignment=self.assignment,student=self.student,attempt=1,expires_at=timezone.now())

    def response(self,kind,answer,correct,**kwargs):
        q=Question.objects.create(assignment=self.assignment,title='Question',prompt='Prompt',type=kind,marks=10,correct_answer=correct,**kwargs)
        return QuestionResponse(submission=self.submission,question=q,answer=answer)

    def test_partial_multiple_select_and_normalized_fill(self):
        response=self.response('multiple_select',['A','C'],['A','B'],marking_policy='partial')
        self.assertEqual(evaluate_response(response).score,0)
        response.answer=['A'];self.assertEqual(evaluate_response(response).score,5)
        fill=self.response('fill_blank','  HELLO   World ',['hello world'])
        self.assertEqual(evaluate_response(fill).score,10)

    def test_scanned_pdf_requires_ocr_and_docx_extracts(self):
        import pymupdf
        doc=pymupdf.open();doc.new_page();raw=doc.tobytes();doc.close()
        with self.assertRaisesMessage(ValidationError,'OCR'):
            extract(SimpleUploadedFile('scan.pdf',raw))
        from docx import Document
        document=Document();document.add_paragraph('Learning objectives: understand Python functions.')
        buffer=io.BytesIO();document.save(buffer)
        text=extract(SimpleUploadedFile('notes.docx',buffer.getvalue()))
        self.assertIn('Python functions',text)

    def test_material_bounds_and_chunks(self):
        with override_settings(MAX_UPLOAD_BYTES=2):
            with self.assertRaises(ValidationError):extract(SimpleUploadedFile('notes.txt',b'too large'))
        self.assertEqual([len(c) for c in chunks('x'*25001)],[10000,10000,5001])

    def test_pptx_text_and_entity_rejection(self):
        import zipfile
        def presentation(xml):
            buffer=io.BytesIO()
            with zipfile.ZipFile(buffer,'w') as archive:
                archive.writestr('ppt/presentation.xml','<presentation/>')
                archive.writestr('ppt/slides/slide1.xml',xml)
            return SimpleUploadedFile('lesson.pptx',buffer.getvalue())
        slide='<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:t>Python functions</a:t></p:sld>'
        self.assertEqual(extract(presentation(slide)),'Python functions')
        with self.assertRaises(ValidationError):extract(presentation('<!DOCTYPE x [<!ENTITY a "expanded">]><x>&a;</x>'))

    @patch.dict(os.environ,{'GROQ_API_KEY':'test-key-not-real'})
    @patch('groq.Groq')
    def test_invalid_ai_response_retries_and_logs_no_content(self,client_class):
        from ai_services.providers import generate_json
        from ai_services.schemas import MaterialAnalysis
        client=client_class.return_value.__enter__.return_value
        response=MagicMock();response.choices[0].message.content='{"invalid":"sensitive educational content"}';response.usage=None
        client.chat.completions.create.return_value=response
        with self.assertRaises(ServiceUnavailable):
            generate_json(self.trainer,'groq','test',MaterialAnalysis,'Analyze.',{'content':'private notes'})
        self.assertEqual(client.chat.completions.create.call_count,2)
        self.assertEqual(AIUsageLog.objects.count(),2)
        self.assertNotIn('private notes',str(list(AIUsageLog.objects.values())))
        self.assertNotIn('sensitive educational content',str(list(AIUsageLog.objects.values())))

    @patch.dict(os.environ,{'CODE_EXECUTION_PROVIDER':'judge0','JUDGE0_URL':'https://judge.test'})
    @patch('code_execution.service.httpx.Client')
    def test_judge0_limits_network_and_base64_protocol(self,client_class):
        import base64
        from code_execution.service import run_code
        client=client_class.return_value.__enter__.return_value
        client.post.return_value.json.return_value={'token':'safe-token'}
        client.get.return_value.json.return_value={'status':{'id':3,'description':'Accepted'},'stdout':base64.b64encode(b'42\n').decode(),'time':'0.01','memory':100}
        result=run_code('print(42)','','42')
        self.assertTrue(result['accepted'])
        payload=client.post.call_args.kwargs['json']
        self.assertFalse(payload['enable_network'])
        self.assertEqual(payload['cpu_time_limit'],2)
        self.assertEqual(payload['memory_limit'],128000)
        self.assertEqual(base64.b64decode(payload['source_code']),b'print(42)')

    @patch.dict(os.environ,{'CODE_EXECUTION_PROVIDER':'judge0','JUDGE0_URL':''})
    def test_unconfigured_executor_fails_closed(self):
        from code_execution.service import run_code
        with self.assertRaises(ServiceUnavailable):run_code('print(1)')
