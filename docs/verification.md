# Verification record

## Completed in this workspace

- Docker deployment files added for the `/skillforge/` subpath: non-root API and
  gateway images, loopback-only port 3830, named persistent volumes, health-gated
  startup, and host proxy instructions. YAML parsing and configuration invariants
  passed. Environment initialization generated a strong secret and preserved an
  existing file on a second run. The new npm lockfile matches the manifest and
  includes Monaco and the Linux native build dependencies. The 68 backend tests,
  4 frontend component tests, and subpath portable build passed again after these
  additions. The opt-in live integration test was not repeated for this deployment
  configuration change. Docker builds/Compose startup and Nginx runtime checks
  remain unexecuted because the local Docker installation is missing; the server
  validation commands are in [Docker deployment](docker-deployment.md).

- Django migrations generated and applied to the initial SQLite database, including the custom user model and batch reports.
- `manage.py check`: passed with no issues.
- `manage.py makemigrations --check --dry-run`: passed; no missing migrations.
- Backend automated suite: **68 tests passed**. Covers JWT login/logout and deactivation, invitation lifecycle, direct student access without email delivery, unique-email enforcement, trainer password reset and password changes with token revocation, trainer/student isolation, private uploads, scanned-PDF handling, DOCX/PPTX extraction, Python source and Jupyter notebook uploads (indentation, encoding, source-only extraction, invalid content, limits, and private downloads), AI response validation/retries, specific connection/timeout/authentication/quota/model errors without sensitive response leakage, publication, identity-based assignment access, deadline/attempt rules, deterministic and manual grading, execution limits, Piston HTTP status and result validation, timeout/output-limit mapping, response-size bounds, hidden-test redaction, report publication and evidence validation, CSV/PDF export, analytics, and best-result leaderboard points, subpath pagination/admin redirects, and prefixed invitation/reset links.
- Frontend component suite: **4 tests passed**. Covers request deduplication, error display, pagination controls, and safe error formatting.
- Live full-stack DOM integration: **1 test passed**, using the real React app, Axios requests, Django API, and a separate SQLite database. The test logs in as trainer; adds a student without sending email; retrieves the generated password; creates a course and educational notes; authors, publishes and assigns an assessment; signs in as the newly added student; starts, saves and submits; verifies marks remain hidden; closes/releases as trainer; confirms the correct score; changes the student's password in Profile; and signs in again with the new password. Async waits allow for real HTTP and password-hashing latency. The same full workflow also passed using /skillforge/ with a real API on a separate port/database, including the trainer-generated student sign-in link.
- Frontend production bundle generated with `npm run build:portable`. This uses Vite/Rollup and the same application sources with an in-process JSX transformer. It avoids helper-process spawning and produces an unminified build. Normal `npm run build` remains the recommended minified deployment build outside this restricted environment.
- Official Groq and Google Gen AI SDKs import successfully in the local verification environment. AI, Judge0, and Piston service contracts are exercised with explicit test doubles; they do not fabricate production data.

The /skillforge/ build also passed direct HTTP checks for HTML routes, prefixed JS/CSS assets, API health, and the actual Django admin redirect. Production proxy/service templates and a release archive are prepared; no live deployment or Nginx/systemd validation has occurred because hosting access is not connected.

## Environment limitations

The session blocks package-network access and denies permission escalation. Missing dependencies were restored from existing local caches where available. The local Python verification environment inherits some preinstalled system packages; create a clean environment and install the complete requirements for deployment.

Monaco was not present in the cache. Its package dependency, local asset serving/copying, and loading integration are implemented, but the currently built application uses the working plain-text Python editor fallback. Run `npm install` with registry access to enable Monaco, then rebuild and test its browser behavior.

The normal Vite/esbuild command encountered Windows `spawn EPERM`; the portable build and test commands run successfully without those child processes. Native Chromium launch also failed with Windows IPC access denied, so screenshots, visual layout, real-browser accessibility, and Monaco rendering were **not** verified here. Playwright checks are supplied for an unrestricted environment. JSDOM does not perform layout; chart-size warnings in the DOM test are expected and do not constitute a visual test.

The coding session supplies an unreachable proxy at 127.0.0.1:9, so provider requests from session-launched processes fail. The user has subsequently generated a draft through a separately launched backend; this does not remove the coding-session network restriction. Live provider output quality, execution-host isolation, external quotas, latency, Gemini/runner configuration, and SMTP delivery still need validation. Provider failure paths are explicit; no live calls are silently substituted with mock content.

This is a production-minded initial implementation, not a deployment or a penetration-test certification. Optional conversational hints, coding streaks, persisted badge/snapshot tables, and background workers are not implemented. Badges and leaderboards are derived from verified results. Before a larger deployment, use PostgreSQL, a shared throttle cache, queued grading/AI jobs, infrastructure isolation, backups, and dependency pinning/auditing as described in the setup guide.

The Piston adapter is selected locally, but no live Piston container is running: the Docker executable points to a missing installation and WSL enumeration is denied. Container isolation, runtime installation, and real execution probes remain unverified. The supplied setup files require a dedicated Linux host/VM; see [Piston setup](piston-setup.md). The configured-service badge indicates a URL is present, not that a runner is online.

## Repeat the tests

From the repository root:

```powershell
.\.venv\Scripts\python.exe backend\manage.py test tests
cd frontend
npm test
npm run build
```

For environments that restrict helper processes:

```powershell
cd frontend
npm run test:portable
npm run build:portable
```

The integration test is skipped by default to prevent unintended writes to a developer's running application. To run it against the separate disposable database:

```powershell
# Terminal 1, repository root
.\.venv\Scripts\python.exe scripts\prepare-e2e.py
$env:DJANGO_DB_PATH=(Join-Path (Get-Location) '.task-temp\browser.sqlite3')
.\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000 --noreload

# Terminal 2, repository root
cd frontend
npm run build:portable
npm run preview:portable

# Terminal 3, repository root
cd frontend
npm run test:integration
```

Test accounts have random passwords saved only in the ignored `.task-temp` directory. The normal `backend/db.sqlite3` is not seeded or changed by this workflow. Re-running the integration test adds uniquely named test courses and assessments to the disposable database. Stop the test API before starting the normal application.

For a real browser, keep the same isolated API and frontend running, install Playwright Chromium (`npx playwright install chromium`), and run `npm run test:e2e`. Those browser checks are supplied but could not execute under this session's Windows IPC restrictions.
