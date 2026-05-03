FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for pandas, psycopg2, and weasyprint
RUN apt-get update && apt-get install -y \
    gcc libpq-dev \
    libpango-1.0-0 libpangoft2-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy local JobSpy repository
COPY JobSpy/ /JobSpy/

# Install the local JobSpy library
RUN pip install -e /JobSpy

# Copy requirements
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend app
COPY backend/app /app/app

# Expose port
EXPOSE 8000

# Start application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
