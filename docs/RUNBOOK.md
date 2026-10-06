# Runbook: run everything locally, step by step

Works on Windows (Docker Desktop + WSL2), macOS and Linux. On Windows run commands in
**Git Bash** (not PowerShell) so the shell scripts and `curl` behave the same.

## 0. Prerequisites
- Docker Desktop / Docker Engine running (`docker version` shows Client and Server)
- Git, and a GitHub account
- Free ports: **80** (app) and **8080** (Jenkins). If 80 is busy, set `GATEWAY_PORT=8081` in `.env`
  and use `http://localhost:8081` everywhere below (and `BASE=http://localhost:8081` for demo_order.sh).

## 1. Prove the app runs (5 min)
    cd grocery-hub
    cp .env.example .env
    docker compose up --build -d
    docker compose ps                        # all three show (healthy) after ~20 s
    bash scripts/demo_order.sh               # places an order through the gateway
    # open http://localhost in the browser
    docker compose down                      # keeps data. NEVER use -v
Take screenshots: browser, `docker compose ps`, demo_order output.

## 2. Push to GitHub
Create an empty **public** repo named `grocery-hub` on github.com (no README), then:

    git init
    git add .
    git commit -m "Grocery Hub CI/CD"
    git branch -M main
    git remote add origin https://github.com/<your-username>/grocery-hub.git
    git push -u origin main
    # Windows only, if scripts lost their executable bit (the pipeline calls them with bash, so optional):
    git update-index --chmod=+x scripts/*.sh && git commit -m "make scripts executable" && git push

Confirm `.env` is NOT in the repo (it is git-ignored; only `.env.example` is committed).

## 3. Start Jenkins
    cd jenkins
    docker compose up -d --build
    docker compose logs -f jenkins           # wait for "Jenkins is fully up and running", Ctrl+C
    docker compose exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
Open http://localhost:8080, paste the password, choose **Install suggested plugins**, create the admin user.
Sanity check from inside Jenkins:
    docker compose exec jenkins docker version
    docker compose exec jenkins docker compose version

## 4. Create the pipeline job
1. New Item, name `grocery-hub`, type **Pipeline**, OK.
2. Build Triggers: tick **GitHub hook trigger for GITScm polling** (and/or Poll SCM `H/2 * * * *`).
3. Pipeline: Definition **Pipeline script from SCM**, SCM **Git**, Repository URL = your repo URL,
   Branch `*/main`, Script Path `Jenkinsfile`. Save.
4. Click **Build Now**. (After the first run the button becomes **Build with Parameters**.)
Screenshot: the job configuration page.

## 5. Build #1: the happy path
Watch **Console Output** / Stage View. Expected: Checkout, Validate, Build & Test, Docker Build,
Trivy Scan, Deploy, Health Check, Record Release & Cleanup all green.
- The first Trivy run downloads its vulnerability database (a few minutes).
- Reports appear under **Build Artifacts** (`reports/trivy/*`).
Then on your host:
    docker compose -f ../docker-compose.yml ps         # or run from the repo root: docker compose ps
    docker images | grep grocery-hub                    # tags equal the build number
Open http://localhost.
Screenshots: stage view, test results, Trivy console, artifacts list, docker images, docker compose ps, browser.

### If Trivy fails the build
That is the gate working. Open `reports/trivy/<service>.txt`. Fix by bumping the base image tag or
package version, then push again. For report-only mode (explain this in your write-up), set
`TRIVY_EXIT_CODE = '0'` in the Jenkinsfile. If you see TOOMANYREQUESTS, set the environment variable
`TRIVY_DB_REPOSITORY=public.ecr.aws/aquasecurity/trivy-db:2` for the job.

## 6. Git trigger evidence
Make a small change (e.g. edit the README), then:
    git add . && git commit -m "trigger build" && git push
- With a webhook: expose Jenkins using ngrok (`ngrok http 8080`), then GitHub repo, Settings,
  Webhooks, Add webhook, URL `https://<ngrok-id>.ngrok-free.app/github-webhook/`, content type
  `application/json`, event "Just the push event".
- Without a webhook: Poll SCM picks up the commit within a few minutes.
Screenshot: webhook "Recent deliveries" (green tick) or the polling log, and the build it started.

## 7. Persistent storage demo
    bash scripts/demo_order.sh                 # creates an order
    docker compose restart
    curl localhost/api/orders                  # the order is still there
    docker volume ls | grep grocery            # grocery_product-data, grocery_order-data
Run another Jenkins build (a full redeploy) and list the orders again: the data survives.

## 8. Rollback demo (the key one)
1. **Build with Parameters**, tick **SIMULATE_BAD_RELEASE**, Build.
2. Expected: the new release's product-service reports unhealthy, the pipeline goes **red at
   Deploy or Health Check**, then the console shows `ROLLING BACK to tag <previous good>` and `HEALTHY`.
3. Verify the site is still up on the previous version:
       docker compose ps
       curl localhost/api/products
4. Build again with the box unticked: green, and a new good release is recorded.
Screenshots: the red build, the rollback console output, `docker compose ps` afterwards.

## 9. Image cleanup demo
Run 5 or more builds (Build Now repeatedly). The last stage prunes old images:
    docker images | grep grocery-hub           # only the newest 3 tags per service (plus the last good tag)
Screenshot before (many tags) and after cleanup.

## 10. Troubleshooting
| Symptom | Fix |
|---|---|
| `port is already allocated` on 80 | Set `GATEWAY_PORT=8081` in `.env` |
| Jenkins: `permission denied ... docker.sock` | Jenkins container must run as root (default here) and mount `/var/run/docker.sock` |
| `docker compose: command not found` inside Jenkins | Rebuild the image: `cd jenkins && docker compose build --no-cache` |
| `bash\r: No such file` / `\r` errors on Windows | Line endings: `.gitattributes` forces LF; re-clone or run `git add --renormalize .` |
| Trivy stage very slow first time | It is downloading its database once; later runs reuse the `trivy-cache` volume |
| Health check never goes healthy | `docker compose logs <service>`; check `.env` and port mappings |
| Webhook shows 403/404 | Use the `/github-webhook/` path with the trailing slash, or just use Poll SCM |
| Old Trivy tag not found | Use `aquasec/trivy:0.69.3` (pinned in scripts/trivy_scan.sh); never `:latest` |

## 11. Stop and clean up when finished
    docker compose down                         # app (keeps data)
    cd jenkins && docker compose down           # Jenkins (keeps jenkins_home)
    # only when you really want to wipe everything, including data:
    # docker compose down -v
