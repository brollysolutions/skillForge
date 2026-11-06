# Verification record

## UI/UX workflow update - November 6, 2026

- Reorganized dashboards around role-specific next actions, with recent work and deadlines above detailed analytics. Recent activity is limited to five items with a link to the full list. Refined card hierarchy, navigation groups, toolbar styling, and mobile form sizing while retaining light/dark themes.
- Added an Assignments navigation entry for admin and sales. The trainer review shortcut opens the submitted-work filter, which persists through reload. Assignment searches now show a distinct no-match state and a clear-filters action.
- Mobile navigation now includes an internal close button, keyboard focus wrapping, background interaction blocking, scroll locking, Escape dismissal, and focus restoration.
- Portable build and seven component tests pass. Browser coverage includes the new dashboard/filter/mobile-keyboard workflow plus the existing role, account-access, publishing, submission, detail-page, and responsive UI audits. Reviewed updated desktop and mobile-dark screenshots under `artifacts/`.
- All 12 browser scenarios pass across the verification runs. The final focused rerun passed after scoping the mobile close-button assertion to its drawer and allowing the initial login up to 15 seconds on this local environment.

## End-to-end regression and fixes - November 6, 2026

- Reproduced and fixed two defects: malformed course-enrollment IDs returned HTTP 500 instead of validation errors, and the trainer's student-access dialog showed an empty cached roster immediately after publishing a batch assignment. Enrollment now validates integer IDs before querying; opening the access dialog refreshes its roster.
- Added backend regression coverage for invalid enrollment payloads and a Chrome assertion that newly published batch assignments show their enrolled students immediately. Added a browser lifecycle covering sales-created student access, case-insensitive email login, session restoration after reload, deactivation, rejected inactive login, and reactivation.
- Final checks passed: 73 Django tests, seven component tests, all 11 Chrome scenarios, the rendered trainer-to-student lifecycle against the live isolated API, portable production build, and migration consistency. The initial browser login timeout did not recur on either rerun; the final complete browser suite passed without retries.
- Browser testing covers all four roles, desktop/mobile layouts, dark mode, dialogs, assignment publishing, answer submission, output comparison, reports, and student performance. The integration lifecycle covers material creation, saving answers, grading, closing, release, and student result visibility. Database writes used the isolated browser fixture or Django's test database.
- Live Groq assignment-generation and Piston execution probes could not connect from the restricted environment. Automatic approval review rejected the external retry pending explicit user approval to send synthetic instructions/code using configured credentials. These live integrations remain unverified; mocked provider and runner contract/error tests pass. No production deployment was performed.

## UI and tag review - November 6, 2026

- The final portable production build and trainer-to-student lifecycle against the isolated live API pass, including saving answers, submission, closing, releasing, and viewing results.
- Reviewed shared buttons, input labels, status badges, tables, dialogs, navigation, and all 47 role-specific page views at desktop (1440px) and mobile (390px) widths. Additional browser checks cover assignment detail/editing, submissions, reports, individual student performance, and the student answer workspace.
- The UI audit verifies named controls, associated labels, one main heading, valid status tags, no page-level horizontal overflow, no nested interactive elements, and no visible API error states. Keyboard checks cover Escape dismissal, dialog names, restored focus, and mobile navigation. All four roles were checked in dark mode.
- Refined typography, spacing, dashboard cards, role-specific wording, forms, and responsive layouts. Status tags use explicit semantic colors and readable labels; they stay on one line inside horizontally scrollable tables. Output mismatches use failure icons and colors. Repaired punctuation encoding in ten frontend files.
- Seven component tests pass. Ten Chrome scenarios (four workflow checks and six UI audits) pass across the verification runs. Screenshots of role dashboards and the mobile output-comparison view are under `artifacts/ui-*.png`. Production builds use the portable Vite configuration in this environment.
- Browser fixtures remain isolated in `.task-temp/browser.sqlite3`; `scripts/prepare-e2e.py` now also prepares marked report/submission detail fixtures. Live AI generation, delivery, and external code execution are outside this UI review.


## Team, batches, and email-only update — November 6, 2026

- 72 Django tests pass, including sales/admin permissions, trainer batch isolation, student enrollment across trainers, automatic assignment access, deadline validation, single-task generation validation, uploaded question extraction, output comparison, and revoked session refresh.
- Django system checks and `makemigrations --check --dry-run` pass. Local database migrations were applied after creating `.task-temp/before-team-batches.sqlite3` as a backup.
- The portable production build and all four component tests pass. Monaco is absent in this local dependency cache; the existing plain-text code editor fallback is used.
- The rendered trainer-to-student lifecycle passes against a live, isolated Django API: email login, student provisioning, manual assignment, submit, close/release, and student result review.
- Four Chrome browser scenarios pass: desktop/mobile sign-in, trainer routes, sales course/batch enrollment followed by trainer publishing and student access, and admin team/performance pages. Tests used the compiled frontend and `.task-temp/browser.sqlite3`, never the normal database. The Playwright bundled browser was unavailable, so the installed Chrome channel was used. Screenshots are under `artifacts/`.
- Provider behavior was verified with mocks; no live AI request or isolated-code-executor call was made for this update. Production hosting has not been deployed. Email-only login is an explicit requested product decision and does not verify who owns an email; see [access model](team-batches.md).

The sections below record earlier verification history.

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
