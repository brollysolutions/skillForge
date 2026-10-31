import io
import json
import re
import tokenize
import zipfile
from pathlib import Path
from django.conf import settings
from rest_framework.exceptions import ValidationError

MAX_TEXT = 120000


def normalize(text):
    return re.sub(r'[ \t]+', ' ', text.replace('\x00', '')).strip()


def source_text(text):
    # Keep indentation and spacing: they carry meaning in Python examples.
    text.encode('utf-8')  # Reject unpaired surrogate escapes from notebook JSON.
    if any(ord(char) < 32 and char not in '\n\r\t\f' for char in text):
        raise ValueError('binary content in source')
    return text.replace('\r\n', '\n').replace('\r', '\n').strip('\n')


def notebook_text(raw):
    notebook = json.loads(raw.decode('utf-8-sig'))
    if not isinstance(notebook, dict) or notebook.get('nbformat') != 4:
        raise ValidationError({'file': 'Use a Jupyter notebook saved in notebook format version 4.'})
    cells = notebook.get('cells')
    if not isinstance(cells, list) or len(cells) > 2000:
        raise ValidationError({'file': 'Notebook must contain a cells list with at most 2,000 cells.'})
    parts = []
    for index, cell in enumerate(cells, 1):
        if not isinstance(cell, dict) or cell.get('cell_type') not in {'code', 'markdown', 'raw'}:
            raise ValueError('invalid notebook cell')
        source = cell.get('source')
        if isinstance(source, list) and all(isinstance(line, str) for line in source):
            source = ''.join(source)
        if not isinstance(source, str):
            raise ValueError('invalid notebook source')
        source = source_text(source)
        if source.strip():
            parts.append(f"[Cell {index}: {cell['cell_type']}]\n{source}")
    # Outputs, attachments, execution counts and metadata are not learning sources.
    return '\n\n'.join(parts)


def extract(upload):
    ext = Path(upload.name).suffix.lower()
    if ext not in {'.pdf', '.docx', '.txt', '.pptx', '.py', '.ipynb'}:
        raise ValidationError({'file': 'Use a PDF, DOCX, TXT, PPTX, PY, or IPYNB file.'})
    if upload.size > settings.MAX_UPLOAD_BYTES:
        raise ValidationError({'file': f'File exceeds {settings.MAX_UPLOAD_BYTES // 1024 // 1024} MB.'})
    raw = upload.read()
    upload.seek(0)
    try:
        if ext == '.py':
            encoding, _ = tokenize.detect_encoding(io.BytesIO(raw).readline)
            text = source_text(raw.decode(encoding))
        elif ext == '.ipynb':
            text = notebook_text(raw)
        elif ext == '.txt':
            if b'\x00' in raw:
                raise ValueError('binary content')
            text = raw.decode('utf-8-sig')
        elif ext == '.pdf':
            if not raw.startswith(b'%PDF-'):
                raise ValueError('invalid signature')
            import pymupdf
            with pymupdf.open(stream=raw, filetype='pdf') as document:
                if document.needs_pass or len(document) > 500:
                    raise ValidationError({'file': 'Use an unencrypted PDF with at most 500 pages.'})
                text = '\n'.join(page.get_text() for page in document)
        else:
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                if len(archive.infolist()) > 2000 or sum(i.file_size for i in archive.infolist()) > 50 * 1024 * 1024:
                    raise ValidationError({'file': 'Document expands beyond the processing limit.'})
                required = 'word/document.xml' if ext == '.docx' else 'ppt/presentation.xml'
                if required not in archive.namelist() or any('vbaProject' in n for n in archive.namelist()):
                    raise ValueError('invalid document')
            if ext == '.docx':
                from docx import Document
                document = Document(io.BytesIO(raw))
                text = '\n'.join([p.text for p in document.paragraphs] + [c.text for table in document.tables for row in table.rows for c in row.cells])
            else:
                # Read slide text from the validated OOXML archive, without executing embedded content.
                from xml.etree import ElementTree
                with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                    names = sorted((n for n in archive.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml', n)),
                                   key=lambda n: int(re.search(r'slide(\d+)\.xml', n).group(1)))
                    slides = []
                    for name in names:
                        xml = archive.read(name)
                        if b'<!DOCTYPE' in xml.upper() or b'<!ENTITY' in xml.upper():
                            raise ValueError('unsupported document entities')
                        root = ElementTree.fromstring(xml)
                        slides.append('\n'.join(node.text or '' for node in root.iter('{http://schemas.openxmlformats.org/drawingml/2006/main}t')))
                    text = '\n'.join(slides)
    except ValidationError:
        raise
    except Exception:
        if ext == '.ipynb':
            raise ValidationError({'file': 'Invalid notebook. Upload UTF-8 JSON with valid code, markdown, or raw cell sources.'})
        if ext == '.py':
            raise ValidationError({'file': 'Invalid Python text file. Use UTF-8 or a valid Python encoding declaration, without binary content.'})
        raise ValidationError({'file': 'The document is invalid, encrypted, or not UTF-8 text.'})
    if ext not in {'.py', '.ipynb'}:
        text = normalize(text)
    if not text.strip():
        message = 'No readable text found. Scanned PDFs require OCR before upload.' if ext == '.pdf' else 'No readable text or code found. Add learning content before uploading.'
        raise ValidationError({'file': message})
    if len(text) > MAX_TEXT:
        raise ValidationError({'file': 'Document exceeds 120,000 extracted characters. Split it into smaller documents.'})
    return text


def chunks(text, size=10000):
    return [text[i:i + size] for i in range(0, len(text), size)]
