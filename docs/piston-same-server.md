# Piston on the existing SkillForge Linux server

This is the explicitly requested single-server option. Upstream Piston uses a
privileged container, so a runner compromise could affect the other applications
on this host. The separate Docker network and per-job limits do not provide a
separate VM's security boundary. Prefer a dedicated runner VM when available.

No untrusted student program runs inside Django. The runner receives code via
its HTTP API and does not mount the application, its secrets, database or Docker
socket. Its API is published only on host loopback for runtime installation.
Only the Django API joins its additional Docker network; the web gateway stays
on the application's default network. No Nginx change is needed.

From the deployed project root, first check the host requirements:

```bash
cd ~/skillforge-ai/skillForge
docker info --format 'Cgroup version: {{.CgroupVersion}}'
free -h
df -h /var/lib/docker
```

Piston requires cgroup v2. If this reports version 1, stop here: do not change
kernel boot settings or restart Docker on the busy host without planning the
impact on its existing applications. The provided runner limit is 768 MiB and
one CPU; package installation also needs free disk and memory.

Copy `infra/piston/same-host.override.yaml` to `docker-compose.override.yml` in
the project root. If an override already exists, merge the entries instead of
overwriting it. Compose automatically loads this override alongside the root
`docker-compose.yml`. Relative paths in `extends` resolve against that root.

```bash
docker compose config --quiet
docker compose pull piston
docker compose up -d --no-deps piston
curl --fail --show-error --silent --retry 12 --retry-connrefused --retry-delay 5 --max-time 5 http://127.0.0.1:2000/api/v2/runtimes
python3 scripts/setup-piston.py --install-python
curl --fail --show-error --silent http://127.0.0.1:2000/api/v2/runtimes
docker compose up -d --no-deps --force-recreate api
docker compose exec api python manage.py check_code_runner --check-limits
```

Run each command only after the previous command succeeds. An empty array from
the first runtimes check is expected on a new installation. After installation,
the array must contain Python. The setup helper selects an available Python 3
runtime from Piston's package list instead of guessing a version. It uses only
the local runner API. Package downloads need outbound connectivity.

The override sets `PISTON_URL=http://piston:2000/api/v2` for Django and selects
Piston/Python 3, overriding the old `runner_private_ip` placeholder in `.env`.
It also clears any unrelated runner-proxy token. Never use the public website
URL or localhost as this container-to-container URL. You can update the root
`.env` to match, but the override takes precedence while installed.

The final command must report both Python input/output and timeout/output-limit
checks passed. Then refresh the student page and run the sample assessment.
These probes test behavior, not resistance to sandbox escapes. For failures:

```bash
docker compose ps piston api
docker compose logs --tail=80 piston
```

Do not disable job sandboxing or lift execution limits to make a probe pass.
Do not restart the Docker daemon, prune volumes, or change the existing Nginx
site as part of runner setup. Once verified, pin `PISTON_IMAGE` in the root `.env`
to the tested image digest and review upgrades deliberately. Compose always
needs the override for this arrangement; using only `-f docker-compose.yml`
omits it. The packages volume survives container recreation.

The configuration was checked locally by parsing and resolving the Compose
service inheritance and network/volume references. Linux Docker execution is
not verified here because the local Docker installation is unavailable.

References: [Piston installation](https://github.com/engineer-man/piston#readme),
[Docker Compose extends](https://docs.docker.com/compose/how-tos/multiple-compose-files/extends/).
