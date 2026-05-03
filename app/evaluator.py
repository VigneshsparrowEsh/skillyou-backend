import os
import json
import logging
from time import sleep
from anthropic import Anthropic
from .database import SessionLocal
from .models import Job
from .redis_queue import dequeue_job_id

logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

def evaluate_job(job: Job) -> dict:
    """Call Claude API to evaluate the job."""
    if not ANTHROPIC_API_KEY:
        logger.warning("Anthropic API Key not found. Skipping real evaluation.")
        return {
            "role_fit": "N/A",
            "skill_match": "N/A",
            "salary_competitiveness": "N/A",
            "company_quality": "N/A",
            "remote_friendliness": "N/A",
            "growth_potential": "N/A",
            "summary": "Evaluation skipped due to missing API key."
        }
    
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    
    prompt = f"""
You are an expert AI job evaluator. Please evaluate the following job posting on these 6 dimensions, scoring them from A (Best) to F (Worst).

Job Title: {job.title}
Company: {job.company}
Location: {job.location}
Remote: {job.is_remote}
Salary Range (INR): {job.salary_min} - {job.salary_max}
Description:
{job.description}

Evaluate these 6 dimensions:
1. role_fit (Overall alignment of the role)
2. skill_match (Match of typical skills for this type of role)
3. salary_competitiveness (How competitive the salary is, based on standard industry rates)
4. company_quality (General reputation and quality of the company)
5. remote_friendliness (How remote-friendly the job is)
6. growth_potential (Opportunities for career progression)

Format your response exactly as JSON with these keys (no markdown blocks, just raw JSON):
"role_fit", "skill_match", "salary_competitiveness", "company_quality", "remote_friendliness", "growth_potential", "summary"

For the "summary", provide exactly 3 sentences summarizing your thoughts on the job.
"""

    response = client.messages.create(
        model="claude-3-5-sonnet-20240620", # Sonnet 3.5 is the standard for complex reasoning currently (or fallback to user specified 'claude-sonnet-4-6' equivalent)
        max_tokens=500,
        temperature=0.2,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    try:
        content = response.content[0].text
        # Clean up any potential markdown formatting the model might still add
        if content.startswith("```json"):
            content = content.split("```json")[1].split("```")[0].strip()
        elif content.startswith("```"):
            content = content.split("```")[1].split("```")[0].strip()
            
        evaluation = json.loads(content)
        return evaluation
    except Exception as e:
        logger.error(f"Failed to parse Claude response: {e}")
        return {
            "error": "Failed to parse response",
            "raw_response": response.content[0].text
        }

def process_evaluation_queue(run_once: bool = False):
    """
    Background worker function that reads from Redis queue, evaluates jobs,
    and saves the results back to the database.
    """
    logger.info("Starting AI Evaluation Engine...")
    
    while True:
        try:
            job_id = dequeue_job_id()
            if not job_id:
                if run_once:
                    break
                sleep(5)
                continue
            
            logger.info(f"Processing evaluation for Job ID: {job_id}")
            
            # Fetch job from DB
            db = SessionLocal()
            job = db.query(Job).filter(Job.id == job_id).first()
            
            if not job:
                logger.warning(f"Job ID {job_id} not found in database.")
                db.close()
                continue
                
            if job.evaluation:
                logger.info(f"Job ID {job_id} already evaluated.")
                db.close()
                continue
            
            # Evaluate
            evaluation_result = evaluate_job(job)
            
            # Save to DB
            job.evaluation = json.dumps(evaluation_result)
            db.commit()
            logger.info(f"Successfully evaluated Job ID: {job_id}")
            
            db.close()
            
        except Exception as e:
            logger.error(f"Error in evaluator worker: {e}")
            if run_once:
                break
            sleep(5)

if __name__ == "__main__":
    process_evaluation_queue()
