Docker Compose for local development

This project includes a `Dockerfile` and `docker-compose.yml` to run the full stack locally (Django + MySQL + Redis).

Quick start
1. Copy `.env.example` to `.env` and fill values (especially `SECRET_KEY`, DB passwords).

2. Build and start containers:

```bash
# On Windows cmd
docker-compose up --build
```

3. The Django app will be available at http://localhost:8000

Notes
- Data stored in the MySQL container is persisted in Docker volumes (`db_data`).
- For quick local testing you can enable `RUN_SEED_ON_DEPLOY=1` in `.env` to automatically seed demo users.
- In production we recommend using managed services (RDS, Elasticache, S3) and building a production Docker image.

Next steps
- I can add an example `docker-compose.prod.yml` that uses an external RDS and S3, and a small Makefile to manage builds.
