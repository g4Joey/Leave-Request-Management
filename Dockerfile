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
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy frontend directory and build React app
COPY frontend ./frontend

# Go back to app directory and copy the rest of the application
WORKDIR /app
COPY . .

# Build the frontend with retry logic and extended timeouts
RUN if [ -d ./frontend ]; then \
            cd frontend && \
            npm config set fetch-timeout 300000 && \
            npm config set fetch-retry-mintimeout 20000 && \
            npm config set fetch-retry-maxtimeout 120000 && \
            npm config set fetch-retries 3 && \
            npm ci --production=false --no-audit --no-fund && \
            npm run build; \
        fi

# Ensure build static files are copied into STATIC_ROOT so WhiteNoise can serve
# them even if collectstatic doesn't run at container start for some reason.
RUN mkdir -p /app/staticfiles && \
        if [ -d ./frontend/build/static ]; then \
            cp -R ./frontend/build/static/* /app/staticfiles/ || true; \
        fi
# Copy and set entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose port (Render populates $PORT at runtime)
EXPOSE 10000

# Use entrypoint to run migrations, collectstatic, then start gunicorn
ENTRYPOINT ["/entrypoint.sh"]