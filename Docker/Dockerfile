FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies as root
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev netcat-traditional && \
    rm -rf /var/lib/apt/lists/*

# Copy entrypoint and make executable as root
COPY Docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create non-root user and switch
RUN useradd -m -s /bin/bash app_user
USER app_user

WORKDIR /app

COPY ../requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY .. .

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
