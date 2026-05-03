from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json
from sqlalchemy.orm import Session
from pydantic import BaseModel
from contextlib import asynccontextmanager

from .database import engine, Base, get_db
from .models import Job
from .scraper import search_jobs
from .dedup import dedup_and_save_jobs
from .redis_queue import enqueue_job_ids
from . import resume
from . import interview

# Create database tables
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables exist
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown

app = FastAPI(title="SkillYou Job Ingestion API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resume.router)
app.include_router(interview.router)

class JobSearchRequest(BaseModel):
    search_term: str
    location: str
    is_remote: bool = False

@app.post("/jobs/search")
def search_and_ingest_jobs(request: JobSearchRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Search jobs, deduplicate, save to PostgreSQL, and enqueue into Redis.
    """
    scraped_jobs = search_jobs(
        search_term=request.search_term,
        location=request.location,
        is_remote=request.is_remote
    )
    
    if not scraped_jobs:
        return {"status": "success", "total_found": 0, "new_jobs_added": 0, "new_job_ids": []}
    
    # Dedup and save
    new_job_ids = dedup_and_save_jobs(db, scraped_jobs)
    
    # Enqueue to Redis in background to avoid blocking response if Redis is slow
    if new_job_ids:
        background_tasks.add_task(enqueue_job_ids, new_job_ids)
        
    return {
        "status": "success",
        "total_found": len(scraped_jobs),
        "new_jobs_added": len(new_job_ids),
        "new_job_ids": new_job_ids
    }

@app.get("/jobs/{job_id}/score")
def get_job_score(job_id: int, db: Session = Depends(get_db)):
    """
    Get the AI evaluation score for a specific job.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if not job.evaluation:
        return {"status": "pending", "message": "Job evaluation is pending or not started."}
        
    try:
        evaluation = json.loads(job.evaluation)
        return {
            "status": "completed",
            "job_id": job.id,
            "evaluation": evaluation
        }
    except json.JSONDecodeError:
        return {
            "status": "error",
            "message": "Evaluation data is corrupted or invalid."
        }
