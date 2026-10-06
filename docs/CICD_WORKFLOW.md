# CI/CD Pipeline with Docker Compose — Greenbarrow Grocer

## 1. Overview
A push to GitHub triggers Jenkins, which tests, builds, security-scans and deploys a 3-container grocery app
(FastAPI product-service, FastAPI order-service, nginx gateway + frontend) using Docker Compose.
If the new release is unhealthy or fails after deployment starts, the pipeline rolls back automatically.

```
git push -> GitHub webhook -> Jenkins
  Checkout -> Validate (compose config, shell syntax) -> Build & Test (pytest) -> Docker Build (tag = build number)
  -> Trivy Scan (gate) -> Deploy (compose up) -> Health Check
  -> Record good release + Cleanup old images
  on failure -> Rollback to last good tag
```

## 2. Requirement coverage
| Requirement | Where |
|---|---|
| Git integration | `checkout scm`, `triggers { githubPush() }`, GitHub webhook (section 4) |
| Application build and testing | Stage *Build & Test*; pytest per service, JUnit results published |
| Docker image creation | Multi-stage non-root Python images (`services/*/`) with `HEALTHCHECK`; non-root `nginx-unprivileged` gateway (`gateway/`); stage *Docker Build* |
| Trivy security scanning | `scripts/trivy_scan.sh`; blocks on fixable HIGH/CRITICAL; reports in `reports/trivy/` (full all-severity report, gated HIGH/CRITICAL table, JSON, Dockerfile misconfig scan, SUMMARY.txt) archived by Jenkins |
| Environment configuration | `.env.example` -> `.env`, read via `env_file` and `${VAR}` in `docker-compose.yml` |
| Deployment automation | `scripts/deploy.sh` (`docker compose up -d --no-build`) |
| Health checks | Compose `healthcheck` on all services, `depends_on: service_healthy`, `scripts/healthcheck.sh` |
| Persistent storage | Named volumes `product-data`, `order-data` mounted at `/data` (never removed on deploy/rollback) |
| Image cleanup | `scripts/cleanup.sh` keeps newest 3 tags per service + last good; prunes dangling images |
| Rollback | `scripts/rollback.sh` redeploys `.deploy/last_good_tag`; runs automatically in `post { failure }` |

## 3. Design decisions
- **Immutable tags**: images are tagged with the Jenkins build number, never only `latest`, so any past release can be redeployed.
- **Scan before deploy**: a vulnerable image never reaches the running stack. `--ignore-unfixed` avoids failing on issues nobody can patch yet. Set `TRIVY_EXIT_CODE=0` for report-only mode.
- **Rollback safety**: the last good tag is recorded only after the health check passes; cleanup never deletes it.
- **Data safety**: no `down -v` anywhere, so volumes survive deploys and rollbacks.
- **Least privilege**: app containers run as non-root user (uid 10001); multi-stage builds keep images small.

## 4. Setup
1. Start Jenkins: `cd jenkins && docker compose up -d --build`; open http://localhost:8080 (password: `docker compose exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword`).
2. Install plugins: Git, Pipeline, GitHub, JUnit.
3. New Item -> Pipeline -> *Pipeline script from SCM* -> your repo URL, branch `main`, script path `Jenkinsfile`.
4. GitHub repo -> Settings -> Webhooks -> `http://<jenkins-host>:8080/github-webhook/`, type `application/json`, push events.
   (Local machine? Expose with ngrok, or use *Poll SCM* `H/2 * * * *` instead.)
5. Push a commit. The app is served on http://localhost (port from `.env`).

## 4a. Notes
- Gateway container listens on 8080 (non-root); compose maps host `GATEWAY_PORT` (default 80) to it.
- The Jenkins image detects the CPU architecture automatically (Intel/AMD and Apple Silicon both work).
- Dependencies are pinned to patched FastAPI/Starlette versions so the Trivy gate passes; if a new base-image CVE appears, bump the tag or set `TRIVY_EXIT_CODE=0` (report-only) and explain why in your write-up.
- Tests run in a fresh venv per service using `requirements-dev.txt` (adds pytest + httpx).

## 5. Demonstrating rollback
1. Run a good build (e.g. #1 or #2) so a last-good release is recorded.
2. Click **Build with Parameters**, tick `SIMULATE_BAD_RELEASE`, and build. (Editing `/health` in the code would
   instead fail the unit tests in stage 3, before any deployment, so the parameter is the right way to demonstrate it.)
3. The new release deploys, fails its health check (red at *Deploy* or *Health Check*), and the `post { failure }` block
   runs `rollback.sh`: `ROLLING BACK to tag N-1`, then `HEALTHY`. The site stays up on the previous good version.
Take screenshots of the red build and the rollback output.

## 6. Evidence checklist (screenshots/output to submit)
- [ ] Jenkins stage view of a successful build
- [ ] Console output of *Trivy Scan* + files in `reports/trivy/`
- [ ] `docker compose ps` showing all containers `healthy`
- [ ] Browser showing the running site; `curl localhost/api/products`
- [ ] Persistence: place an order, run `docker compose restart` (or redeploy), order still in `/api/orders`; `docker volume ls`
- [ ] Failed build + automatic rollback console output
- [ ] `docker images | grep grocery-hub` before/after cleanup
- [ ] GitHub webhook "Recent deliveries" with a green tick


## Addendum: rollback demo switch and hardening notes
- The Jenkinsfile has a boolean build parameter `SIMULATE_BAD_RELEASE` (default off). When ticked, product-service
  reports `/health` as 503, which makes the release fail its health check and triggers the automatic rollback
  without editing any code. It exists only for the demonstration.
- Scripts are invoked with `bash scripts/<name>.sh`, so the pipeline works even if executable bits or CRLF
  line endings were lost on Windows (`.gitattributes` also forces LF).
- Trivy is pinned to `aquasec/trivy:0.69.3`, the last known-clean release before the March 2026 Trivy
  supply-chain incident; never use `:latest`. Override with `TRIVY_IMAGE` if you must.
- The Jenkins image detects the CPU architecture, so it builds on Intel/AMD and Apple Silicon.
- Full step-by-step instructions: `docs/RUNBOOK.md`.
