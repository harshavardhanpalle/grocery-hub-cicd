# Grocery Hub: Jenkins CI/CD with Docker Compose

A FastAPI grocery store (product-service, order-service, nginx gateway) with a complete
Jenkins pipeline: Git -> test -> Docker build -> **Trivy scan** -> deploy -> **health check** ->
**rollback** -> **image cleanup**, with persistent volumes and `.env` configuration.

## Quick start (just the app)
    cp .env.example .env
    docker compose up --build        # open http://localhost
    docker compose down              # NEVER add -v (that deletes your data)

## Full CI/CD run
Follow **docs/RUNBOOK.md** (step by step, with the expected output and screenshot list).
Design and requirement mapping: **docs/CICD_WORKFLOW.md**.

## Layout
    Jenkinsfile            8-stage pipeline + automatic rollback
    docker-compose.yml     app stack: health checks, named volumes, .env
    .env.example           configuration template (.env is git-ignored)
    services/              product-service, order-service (multi-stage, non-root, tests)
    gateway/ frontend/     nginx (non-root) + single-page storefront
    scripts/               deploy, healthcheck, trivy_scan, rollback, mark_good, cleanup, demo_order
    jenkins/               Jenkins in Docker (docker CLI + compose + python)
    reports/trivy/         Trivy output (written by the pipeline)
    docs/                  RUNBOOK.md and CICD_WORKFLOW.md
