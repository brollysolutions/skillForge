# Piston without a paid execution API

For the explicitly requested installation on the existing Brolly server, see
[single-server Piston setup](piston-same-server.md). It documents the privileged
container tradeoff and the additional Docker network. The instructions below
remain the recommended dedicated-runner deployment.

SkillForge supports self-hosted Piston for both sample runs and final grading. There is no Piston API subscription or per-run provider fee when you host it yourself. You still need a computer/VM with sufficient resources; rented infrastructure may cost money. The public EMKC service requires authorization and is not configured by this project. [Upstream installation and API reference](https://github.com/engineer-man/piston).

## What is ready here

The backend adapter, Piston configuration, student workflow, deterministic scoring, hidden-test redaction, setup utility, and verification command are implemented. This workspace's `.env` selects `piston` with `http://127.0.0.1:2000/api/v2`. That address is for a local SSH tunnel to your runner. **It does not mean a runner is installed or running.**

This Windows workspace has a broken Docker executable shim, and the coding session cannot access WSL. No Piston container or Python runtime could be started or verified here. Do not expect Run Code to work until the following installation and checks complete.

## 1. Prepare a dedicated Linux runner

Use an existing spare Linux computer or a dedicated Linux VM. Install Docker Engine and Docker Compose there and enable cgroup v2. The upstream Piston container requires privileged mode, so keep it on a separate machine/VM from Django, the database, and application secrets. Do not mount the SkillForge workspace, `.env`, Docker socket, or student database into the container.

Copy `infra/piston/compose.yaml` and `scripts/setup-piston.py` from this repository to that host. From the directory containing the compose file:

```sh
docker compose -f compose.yaml up -d
python3 setup-piston.py --install-python
```

The utility installs the latest available Python 3 runtime only if none is installed. A package download may take several minutes. It does not execute student submissions or send any material to an external execution API. The container needs package-download access during installation.

The provided compose file binds the API to the runner host's loopback interface. It uses a dedicated packages volume and sets job networking off, two concurrent jobs, 2-second CPU/5-second wall limits, 128 MB job memory, 16 processes, 64 KB file size, and 16,000-character stdout/stderr limits. Piston's package-management endpoints must remain private. After verification, set `PISTON_IMAGE` to the tested image digest to make upgrades deliberate.

## 2. Connect Windows to the runner

In a normal Windows terminal, open an SSH tunnel (replace `runner-user` and `runner-host`):

```powershell
ssh -N -L 127.0.0.1:2000:127.0.0.1:2000 runner-user@runner-host
```

Keep this terminal open. In `backend/.env`:

```env
CODE_EXECUTION_PROVIDER=piston
PISTON_URL=http://127.0.0.1:2000/api/v2
PISTON_PYTHON_VERSION=3.x
PISTON_API_TOKEN=
```

No Judge0 account or RapidAPI key is needed. `PISTON_API_TOKEN` is optional and only applies if you operate an authenticated reverse proxy instead of this tunnel. Never expose an unauthenticated runner or its package APIs publicly.

## 3. Verify and restart the backend

In another normal PowerShell terminal, at the SkillForge project root:

```powershell
.\.venv\Scripts\python.exe backend\manage.py check_code_runner --check-limits
```

This sends fixed Python probes through the configured runner to check input/output, timeouts, and output limits. It never executes code in Django or modifies student marks. These smoke checks do not replace a host-isolation review.

After they pass, stop the existing Django server with Ctrl+C and restart:

```powershell
.\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000 --noreload
```

Refresh the app and run an assessment sample. Settings shows the selected provider and whether its URL is configured; that badge is not a live health check. Saved code and grading continue through the existing workflow. Execution infrastructure failures preserve the attempt for retry.

## Troubleshooting

- **Cannot connect:** start the runner and SSH tunnel; confirm the URL. Restarting Django cannot install Piston.
- **Run rejected:** verify Python exists with `GET /api/v2/runtimes`; match `PISTON_PYTHON_VERSION` to the installed runtime and verify resource limits.
- **Access denied:** check your optional reverse-proxy authentication. No token is needed for the private tunnel setup.
- **Invalid result/internal failure:** inspect runner logs locally. The application does not show infrastructure response bodies or award marks for infrastructure failures.

For multiple students, monitor CPU, memory, disk, queue time, and concurrency. The starter limits target small workloads. Maintain the runner, review image updates, and restrict outbound traffic at the host as well as within execution jobs.
