import os
import redis

import logging

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    redis_client.ping()
except Exception:
    redis_client = None
    logging.warning("Redis is not available, falling back to mock queue")

def enqueue_job_ids(job_ids: list[int]):
    """
    Enqueue the primary keys of new jobs into the redis list 'new_jobs_queue'.
    """
    if not job_ids:
        return
    # Use rpush to add to the end of the list
    if redis_client:
        redis_client.rpush("new_jobs_queue", *job_ids)
    else:
        print(f"MOCK REDIS: Enqueued job IDs {job_ids}")

def dequeue_job_id() -> int | None:
    """
    Pop a job ID from the front of the 'new_jobs_queue'.
    """
    if redis_client:
        job_id_str = redis_client.lpop("new_jobs_queue")
        return int(job_id_str) if job_id_str else None
    else:
        print("MOCK REDIS: Dequeue attempt")
        return None
