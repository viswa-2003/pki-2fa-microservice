# ---------- Stage 1: Builder ----------
FROM python:3.11-slim AS builder

WORKDIR /app

# Copy dependency file and install (cache-friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---------- Stage 2: Runtime ----------
FROM python:3.11-slim

# Install system dependencies: cron + tzdata, then clean cache [web:64][web:66]
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Set timezone to UTC [web:66][web:69]
ENV TZ=UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code and config
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY cron/ ./cron/
COPY student_private.pem .
COPY student_public.pem .
COPY instructor_public.pem .

# Setup cron job: install crontab with correct permissions [web:62][web:67]
RUN chmod 0644 cron/2fa-cron && crontab cron/2fa-cron

# Create volume mount points /data and /cron with 755
RUN mkdir -p /data /cron && chmod 755 /data /cron
VOLUME ["/data", "/cron"]

# Ensure cron script is executable
RUN chmod +x scripts/log_2fa_cron.py

# Expose API port
EXPOSE 8080

# Start cron daemon and FastAPI app (Uvicorn) on 0.0.0.0:8080 [web:53][web:57]
CMD service cron start && uvicorn app.main:app --host 0.0.0.0 --port 8080 --log-level info
