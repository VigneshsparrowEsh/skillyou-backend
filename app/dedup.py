import hashlib
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from .models import Job

# Simple conversion rates (can be improved with an API later)
EXCHANGE_RATES = {
    "USD": 83.5,
    "EUR": 89.0,
    "GBP": 104.0,
    "INR": 1.0
}

def generate_url_hash(url: str) -> str:
    """Generate an MD5 hash of the URL for deduplication."""
    if not url:
        return ""
    # Removing common tracking params or trailing slashes could be done here
    return hashlib.md5(url.encode('utf-8')).hexdigest()

def convert_to_inr(amount: float, currency: str) -> float:
    if amount is None:
        return None
    if currency and currency.upper() in EXCHANGE_RATES:
        return amount * EXCHANGE_RATES[currency.upper()]
    return amount # fallback, assuming it's INR if unknown

def dedup_and_save_jobs(db: Session, scraped_jobs: List[Dict[str, Any]]) -> List[int]:
    """
    Process scraped jobs, filter out duplicates, and save to DB.
    Returns a list of newly created Job IDs.
    """
    new_job_ids = []
    
    for job_data in scraped_jobs:
        job_url = job_data.get("job_url")
        if not job_url:
            continue
            
        url_hash = generate_url_hash(job_url)
        
        # Check if already exists
        existing_job = db.query(Job).filter(Job.url_hash == url_hash).first()
        if existing_job:
            continue
            
        # Parse fields
        currency = job_data.get("currency", "INR")
        
        salary_min = job_data.get("min_amount")
        salary_max = job_data.get("max_amount")
        
        if salary_min is not None:
            salary_min = convert_to_inr(salary_min, currency)
        if salary_max is not None:
            salary_max = convert_to_inr(salary_max, currency)
            
        new_job = Job(
            title=job_data.get("title", "Unknown Title"),
            company=job_data.get("company", "Unknown Company"),
            location=job_data.get("location"),
            is_remote=job_data.get("is_remote", False),
            salary_min=salary_min,
            salary_max=salary_max,
            source=job_data.get("site"),
            job_url=job_url,
            description=job_data.get("description"),
            date_posted=job_data.get("date_posted"), # Might need parsing if it's a string, jobspy usually returns datetime/date
            url_hash=url_hash
        )
        
        db.add(new_job)
        db.commit()
        db.refresh(new_job)
        new_job_ids.append(new_job.id)
        
    return new_job_ids
