# Setup and deployment

## Environment

Use the commands in the root README to install dependencies and create the first admin. Copy `backend/.env.example` to `backend/.env`; never commit the real file. Replace the development secret before deploying. The frontend needs only the API base URL; it never receives provider or SMTP credentials.

A fresh database has no seeded accounts or results. Run `python backend/manage.py bootstrap_admin your-email@example.com --name "Your Name"` after migrations to create the single admin. An existing single superuser is promoted to admin; other trainers are preserved. The admin adds sales and trainer access; sales/trainers can add students by name and email. All users sign in by typing their approved email, with no password or email message. This does not verify email ownership. See [the team/batch guide](team-batches.md) for details and the full workflow.

## AI setup

Study materials accept PDF, DOCX, TXT, PPTX, `.py`, and `.ipynb` files. Python files preserve indentation and support UTF-8 (including BOM) or a Python encoding declaration. Notebooks must be UTF-8 JSON in notebook format version 4 with at most 2,000 cells. Extraction keeps code, Markdown, and raw cell sources in their original order; outputs, attachments, and metadata are excluded from AI analysis. Sources are only read, never executed. The original file remains available through the private trainer download endpoint. The configured upload-size and 120,000-character extraction limits apply to both new formats.

Configure Groq and Gemini keys and model names on the backend. The default model names are starting values, not a guarantee of availability for every account. Timeout, a single controlled retry, request throttling, and a daily per-user quota bound AI requests. A long document can incur several chunk-analysis requests. Provider errors log only the exception class and usage metadata.

The Groq default is `openai/gpt-oss-120b`, which supports JSON object output. Groq's current model catalog lists `llama-3.3-70b-versatile` as Enterprise-only; existing installations using it may receive a model-not-found/access error. Set `GROQ_MODEL` to a model enabled for your account and restart the backend after editing `.env`. See the [Groq model catalog](https://console.groq.com/docs/models). Environment variables already set in the terminal take precedence over `.env`.

Large materials are limited to 120,000 extracted characters. Each 10,000-character chunk is analyzed separately, then a final analysis combines the chunks. Materials above 16,000 characters require an approved analysis before assignment generation. Trainer review is always required before publication.

Official references used for the integration interfaces:

- [Groq Python quickstart](https://console.groq.com/docs/quickstart)
- [Groq structured output](https://console.groq.com/docs/structured-outputs)
- [Google Gen AI Python SDK](https://googleapis.github.io/python-genai/)
- [Judge0 submission API](https://ce.judge0.com/)

## Groq connection troubleshooting

The UI distinguishes connection failures, timeouts, invalid API keys, denied model access, missing models, and provider rate/quota errors. Provider response bodies are never exposed or logged. Invalid credentials and quota failures are not immediately retried; transient connectivity failures have one controlled retry.

If the backend was started inside a restricted coding session, it may inherit a non-working network proxy. In this workspace the session supplied `HTTP_PROXY`, `HTTPS_PROXY`, and `ALL_PROXY` pointing to `127.0.0.1:9`, causing connection refusal before Groq could validate the key. Do not disable TLS verification or bypass the session restrictions. Stop that backend and start it in a regular Windows PowerShell terminal opened at the project directory:

```powershell
.\scripts\start-backend.ps1
```

Keep that terminal open and retry **Analyze** in the app. It uses the existing database and `backend/.env`; student accounts and materials are preserved. If your normal terminal also cannot connect, check its legitimate proxy/firewall configuration. Model or key validity cannot be established until Groq is reachable. See [Groq error codes](https://console.groq.com/docs/errors) for provider status meanings.

## Code execution without a paid API

Use **self-hosted Piston** with `CODE_EXECUTION_PROVIDER=piston`. Follow [Piston setup](piston-setup.md) to prepare an isolated Linux runner, install Python, connect it through a private tunnel, and verify its limits. No Judge0 subscription is required. The local `.env` is prepared for a tunnel on port 2000, but the runner could not be started here because Docker is not installed correctly and WSL access is restricted. Do not treat the configured URL as a running service.

## Optional Judge0 adapter

Run a maintained Judge0 deployment on infrastructure isolated from Django, its database, and its secrets, or use a managed Judge0 provider. Set its root URL and authentication settings. Confirm the Python language ID using your deployment's `/languages` endpoint.

The adapter requests a two-second CPU limit, five-second wall limit, 128 MB memory, 64 KB file limit, at most 16 processes/threads, and disabled networking. Configure the execution host to enforce these settings, deny outbound traffic, and disallow client overrides that weaken isolation. API flags do not replace host isolation. Do not co-locate the executor with application secrets or expose its management endpoints publicly.

Sample runs do not consume additional attempts. Starting an assessment consumes an attempt. Final submissions execute all tests and award weighted partial marks. Hidden-test stdout, errors, inputs, expected outputs, and individual timings are never stored in the student-facing result payload. Infrastructure failure preserves saved answers and permits retrying the same attempt.

## Frontend editor

Monaco assets are served locally from the installed `monaco-editor` package at `/monaco/vs/`; production builds copy them into `dist/monaco/vs`. No third-party CDN is required. The editor loads lazily. If its assets are unavailable, a clearly labeled plain-text Python editor still supports saving, running, and submitting code. Install frontend dependencies to enable Monaco.

## Production

1. Use a fresh environment and install the complete requirements, including transitive SDK dependencies. Pin and audit the resolved versions in your deployment pipeline.
2. Set `DJANGO_DEBUG=false`, a random secret of at least 32 characters, explicit allowed hosts and CORS origins, production SMTP, HTTPS frontend URL, and all needed integration settings.
3. Terminate HTTPS at a reverse proxy. Configure secure cookies and HSTS; set `SECURE_SSL_REDIRECT=true` when Django can correctly determine the HTTPS scheme. Only trust forwarded headers from your controlled proxy.
4. Run `python manage.py migrate`, `python manage.py collectstatic --noinput`, and `python manage.py check --deploy`.
5. Serve Django with a production WSGI server. For example, from `backend`: `waitress-serve --listen=127.0.0.1:8000 config.wsgi:application`. Proxy `/api/` to Django and serve `frontend/dist` as static content. Route frontend navigation to `index.html`; preserve `/monaco/` static asset paths.
6. Keep `backend/media` private. Do not configure a public media URL or web-server alias. Documents are available only through authenticated trainer download endpoints.
7. Back up the database and private media together. Establish retention and deletion policies for educational records and provider logs.
8. Configure a shared cache for throttling and reverse-proxy rate/body limits before deploying multiple workers. The development in-memory rate-limit cache is process-local, and DRF throttling is not a distributed abuse-prevention system.
9. For multiple concurrent writers, migrate to PostgreSQL. Row locks serialize attempt creation and review; SQLite is appropriate for initial small workloads but has coarse write locking.
10. Move long-running AI and code grading into a queue before larger classes. A synchronous request may take several minutes for many coding tests. Size proxy timeouts accordingly. Provide job status endpoints when introducing Celery/Redis.

## Recovery and maintenance

`python manage.py flushexpiredtokens` cleans expired refresh-token records. Schedule it periodically.

If a worker crashes during grading, a submission can remain `grading`. First confirm no worker is still executing it, then run `python manage.py recover_grading` for a dry run. `--apply` returns attempts older than thirty minutes to `in_progress`. Saved answers remain available, and no duplicate attempt is created. Review the audit trail after recovery.

The application denies editing published assessments. Create a new draft to change assessment content after publication. Dependent courses/topics cannot be deleted; deactivate courses or archive assessments instead.
