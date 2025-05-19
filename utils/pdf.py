"""Single helper that converts HTML (string) → PDF file path using WeasyPrint."""
from pathlib import Path
from uuid import uuid4
from django.conf import settings
from weasyprint import HTML


REPORT_DIR = Path(settings.REPORT_PDF_DIR)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

def html_to_pdf(html: str) -> str:
    filename = REPORT_DIR / f"{uuid4()}.pdf"
    HTML(string=html, base_url=settings.STATIC_ROOT).write_pdf(target=str(filename))
    return str(filename)