# SkillForge AI

A Django + React application for trainer-managed assessments, secure Python coding challenges, AI assignment generation, and evidence-based student reports.

## Deploy with Docker

For **https://brollysolutions.in/skillforge/**, use [the Docker deployment guide](docs/docker-deployment.md).
The root `docker-compose.yml` builds the frontend/gateway and Django API, preserves
SQLite and uploads in named volumes, and publishes only **127.0.0.1:3830**. Your
existing HTTPS proxy forwards `/skillforge/` to that port. Configure the root
`.env` with `python3 scripts/init-docker-env.py` before starting the stack.

## Start locally

Requirements: Python 3.11–3.13, Node.js 22 LTS or newer, npm, and access to package registries for the initial install. No AI key is required for manual assessments, email access, grading, dashboards, or result review.

From this directory in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
.\.venv\Scripts\python.exe backend\manage.py migrate
.\.venv\Scripts\python.exe backend\manage.py bootstrap_admin admin@example.com --name "Platform Admin"
.\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** and sign in with your admin email (replace the example email in the command above). The database starts empty; dashboard values always come from stored records. No default admin account or fabricated performance data is included. See [roles, batches, and email-only access](docs/team-batches.md) for setup and the access model.

On macOS/Linux use `.venv/bin/python` instead of `.venv\Scripts\python.exe` and `cp` instead of `Copy-Item`.

## First classroom workflow

1. Admin adds sales/trainer access under **Team access**. Admin or sales creates courses and batches, assigns their trainers, and enrolls students.
2. Open **Students ? Add student**, enter their name and personal email, and click **Grant access**. The student signs in by typing that email. No password or email is sent. Email-only access does not verify ownership: anyone who knows an approved email can enter that account.
3. Upload a PDF, DOCX, TXT, PPTX, Python script (`.py`), or Jupyter notebook (`.ipynb`), or enter notes. Python indentation is preserved; notebooks contribute code, Markdown, and raw cell sources in order, without outputs or attachments. Uploaded code is never executed. Analyze with Groq, review and edit the summary and extracted concepts, then approve them.
4. Open a batch and create an assignment with up to 10 individual questions, entered manually, uploaded one at a time, or generated with AI. Set its deadline and duration. Each coding question has its own visible input and expected output; written questions use a review rubric.
5. Review and publish the draft. Current batch members receive access automatically. For older or unbatched work, assign students explicitly.
6. Students start timed attempts, save answers, and run sample tests through the selected isolated runner. Students use **Check question** to save and check each Python answer independently, or **Check & complete** for a single-question assignment. Matched questions retain their completion status; all questions passing completes the assignment. See the [salary assignment walkthrough](docs/coding-assignments.md). Use [self-hosted Piston](docs/piston-setup.md) without a paid execution API subscription.
7. Review written answers. AI feedback is advisory; only backend grading and trainer-reviewed marks are official.
8. Close the assessment or wait for its deadline, finish pending evaluations, and release results.
9. Generate a Gemini performance report, review it, and publish it. Students see their own published reports and approved learning recommendations.
10. Use **Analyze learning gaps** in classroom analytics for a trainer-private Gemini batch report and PDF.

## Integrations

For `https://brollysolutions.in/skillforge/`, use [Docker deployment](docs/docker-deployment.md), or the alternative [systemd deployment guide](docs/brolly-deployment.md). The Docker build runs `npm run build:brolly` automatically. The release package excludes environment secrets, local databases, and uploaded materials. Publishing requires access to the existing domain's hosting.

Configure in `backend/.env` for local development, or the root `.env` for Docker:

| Setting | Purpose |
| --- | --- |
| `GROQ_API_KEY`, `GROQ_MODEL` | Material analysis, validated question generation, rubric feedback |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | Personalized performance narratives and learning paths |
| `CODE_EXECUTION_PROVIDER` | `piston` for self-hosted execution, or `judge0` for the existing adapter |
| `PISTON_URL`, `PISTON_PYTHON_VERSION` | Piston API base URL (ending `/api/v2`) and Python version selector |
| `PISTON_API_TOKEN` | Optional bearer token for your own runner reverse proxy |
| `JUDGE0_URL`, `JUDGE0_API_KEY` | External isolated Python execution |
| `JUDGE0_AUTH_HEADER` | `X-Auth-Token` for self-hosted Judge0; `X-RapidAPI-Key` for RapidAPI |
| `JUDGE0_RAPIDAPI_HOST` | Optional RapidAPI host header |
| `JUDGE0_PYTHON_LANGUAGE_ID` | Python language identifier supported by your Judge0 deployment |
| `EMAIL_*` | Legacy settings; sign-in and access provisioning do not send email |

Provider models are configurable; select a model currently available to your account. The Groq integration uses its official Python SDK and JSON mode with Pydantic validation. Gemini uses the official `google-genai` SDK and structured JSON. Piston uses its isolated execution API; Judge0 remains available through its submission/polling API. Missing or failing services return actionable errors; the application never invents AI output or executes student code in Django. The local configuration selects Piston, but a separate runner must be installed and verified before Run Code works; see [Piston setup](docs/piston-setup.md).

## Verification

```powershell
.\.venv\Scripts\python.exe backend\manage.py check
.\.venv\Scripts\python.exe backend\manage.py test tests
.\.venv\Scripts\python.exe backend\manage.py makemigrations --check --dry-run
cd frontend
npm test
npm run build
```

See [verification notes](docs/verification.md) for the actual checks completed in this workspace and environment limitations. Provider tests use explicit mocks, not live credentials.

## Documentation

- [Setup and deployment](docs/setup-guide.md)
- [Architecture and security decisions](docs/architecture.md)
- [Database and scoring rules](docs/database.md)
- [API reference](docs/api-documentation.md)
- [Ten individual Python practice questions](docs/python-practice-10-questions.md)
- [Verification and remaining operational work](docs/verification.md)

Core pages are connected to the API. Optional conversational coding hints, persisted leaderboard snapshots, and coding streaks are not enabled in this initial version. The leaderboard derives badges and best-result points without a separate claim endpoint.
