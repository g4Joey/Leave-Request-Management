# Use Python 3.12 as base image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies including Node.js
RUN apt-get update && apt-get install -y \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements-render.txt .
RUN pip install --no-cache-dir -r requirements-render.txt

# Copy frontend directory and build React app
COPY frontend ./frontend
WORKDIR /app/frontend
RUN npm ci && npm run build

# Go back to app directory and copy the rest of the application
WORKDIR /app
COPY . .

# Collect static files and run migrations
RUN python manage.py collectstatic --noinput

# Expose port
EXPOSE 10000

# Start command
CMD python manage.py migrate && gunicorn leave_management.wsgi:application --bind 0.0.0.0:$PORT