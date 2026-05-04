FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for pandas, psycopg2, and weasyprint
RUN apt-get update && apt-get install -y \
    gcc libpq-dev \
    libpango-1.0-0 libpangoft2-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source code
COPY app /app/app

# Expose port
EXPOSE 8000

# Start application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
