import os
import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from anthropic import Anthropic

from .database import get_db
from .models import Job

router = APIRouter(prefix="/jobs", tags=["Interview Prep"])
logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

@router.get("/{job_id}/interview-prep")
def get_interview_prep(job_id: int, db: Session = Depends(get_db)):
    """
    Generates 5 interview questions, 3 STAR story prompts, and a salary negotiation script.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="Anthropic API Key is not configured.")

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    
    prompt = f"""
You are an expert career coach and technical recruiter. Given the following job description, generate an interview preparation guide.

Job Title: {job.title}
Company: {job.company}
Salary Range: {job.salary_min} - {job.salary_max}
Description:
{job.description}

Please generate:
1. 5 highly likely interview questions specifically tailored to this role and company.
2. 3 STAR (Situation, Task, Action, Result) story prompts that the candidate should prepare, targeting the core skills required.
3. A short salary negotiation script based on the provided salary range. If the range is None or missing, provide a script to ask for the budget.

Output your response ONLY as a JSON object with these keys: "interview_questions" (list of strings), "star_prompts" (list of strings), and "negotiation_script" (string).
Do not include any markdown formatting blocks like ```json.
"""

    response = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=1500,
        temperature=0.4,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    content = response.content[0].text
    
    # Clean up markdown if present
    if content.startswith("```json"):
        content = content.split("```json")[1].split("```")[0].strip()
    elif content.startswith("```"):
        content = content.split("```")[1].split("```")[0].strip()
        
    try:
        prep_data = json.loads(content)
        return {
            "status": "success",
            "job_id": job.id,
            "interview_prep": prep_data
        }
    except Exception as e:
        logger.error(f"Failed to parse Claude response for interview prep: {e}")
        return {
            "status": "error",
            "message": "Failed to parse interview preparation data from AI.",
            "raw_response": content
        }
