from sqlalchemy import Column, Integer, String, Boolean, Float, Text, Date
from .database import Base

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    location = Column(String, nullable=True)
    is_remote = Column(Boolean, nullable=True)
    salary_min = Column(Float, nullable=True)
    salary_max = Column(Float, nullable=True)
    source = Column(String, nullable=True)
    job_url = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    date_posted = Column(Date, nullable=True)
    url_hash = Column(String, unique=True, index=True, nullable=False)
    evaluation = Column(Text, nullable=True)
