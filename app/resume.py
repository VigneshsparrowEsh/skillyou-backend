import os
import markdown
import base64
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from anthropic import Anthropic
import logging

try:
    from weasyprint import HTML
except ImportError:
    HTML = None
    logging.warning("WeasyPrint could not be imported. PDF generation will fail.")

from .database import get_db
from .models import Job

router = APIRouter(prefix="/resume", tags=["Resume"])
logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

class ResumeRequest(BaseModel):
    cv_markdown: str
    job_id: int

@router.post("/generate")
def generate_tailored_resume(request: ResumeRequest, db: Session = Depends(get_db)):
    """
    Takes a markdown CV and Job ID, rewrites the CV tailored to the job description,
    and generates an ATS-friendly PDF.
    """
    job = db.query(Job).filter(Job.id == request.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="Anthropic API Key is not configured.")

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    
    prompt = f"""
You are an expert resume writer. Please rewrite the following user CV to be highly tailored for the given Job Description.
Inject relevant keywords from the Job Description naturally into the CV, especially in the summary and experience bullets.
Do not invent fake experience or skills that the user does not have.
Output ONLY the fully tailored CV in Markdown format.

Job Title: {job.title}
Company: {job.company}
Job Description:
{job.description}

User's Original CV:
{request.cv_markdown}
"""

    response = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=2500,
        temperature=0.2,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    tailored_markdown = response.content[0].text
    
    # Convert to HTML for PDF generation
    html_content = markdown.markdown(tailored_markdown)
    
    # Wrap in basic HTML structure with simple ATS-friendly CSS
    full_html = f"""
    <html>
    <head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.4; color: #333; margin: 40px; }}
        h1 {{ font-size: 24px; border-bottom: 1px solid #ccc; padding-bottom: 5px; }}
        h2 {{ font-size: 18px; margin-top: 20px; }}
        h3 {{ font-size: 16px; margin-top: 15px; font-weight: bold; }}
        ul {{ margin-top: 5px; padding-left: 20px; }}
        li {{ margin-bottom: 5px; }}
    </style>
    </head>
    <body>
    {html_content}
    </body>
    </html>
    """
    
    if HTML is None:
        raise HTTPException(status_code=500, detail="WeasyPrint dependencies missing on the server, cannot generate PDF.")
        
    try:
        pdf_bytes = HTML(string=full_html).write_pdf()
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
    except Exception as e:
        logger.error(f"Failed to generate PDF: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate PDF document.")
        
    return {
        "status": "success",
        "job_id": job.id,
        "tailored_cv_markdown": tailored_markdown,
        "tailored_cv_pdf_base64": pdf_base64
    }
