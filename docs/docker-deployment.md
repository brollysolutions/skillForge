# Docker deployment: brollysolutions.in/skillforge

This stack runs the React site and gateway in `web`, and Django/Waitress in `api`.
Only `127.0.0.1:3830` is published. Port 3830 does not appear in the supplied
`docker ps` list; check host listeners as well before starting. Existing services,
including `brolly_frontend_prod` on port 3002, keep their ports and configuration.

The existing HTTPS proxy must forward `/skillforge/` to port 3830. DNS does not
route URL paths. This release prepares the files; it has not been deployed to
your server. Run the commands below on the Linux server, in its own directory.

## 1. Copy and configure

Upload/extract `artifacts/skillforge-brolly.zip` into `/root/skillforge-ai` (or copy
the repository without local secrets, `.venv`, `node_modules`, databases or uploads).
Do not put these files in the current `kundli` project directory. For example:

```bash
mkdir -p /root/skillforge-ai
unzip /path/to/skillforge-brolly.zip -d /root/skillforge-ai
cd /root/skillforge-ai
docker compose version
ss -ltnp '( sport = :3830 )'
python3 scripts/init-docker-env.py
nano .env
```

The initializer creates a random Django secret and will never overwrite an
existing `.env`. Keep that file private and backed up. Set `GROQ_API_KEY` and
`GEMINI_API_KEY` in this **root `.env`** for Docker. Local development continues to
use `backend/.env`; that file is excluded from both images and the release.
Compose passes environment settings only to Django. No provider key goes into
the frontend. Single-quote values containing `$` or `#` to avoid interpolation.

If port 3830 is already occupied, change `SKILLFORGE_HTTP_PORT` and the host proxy
upstream to the same free port. The Compose project name is `skillforge` and its
network and volumes are separate from your other applications. The base images
use maintained tags; record/pin tested digests for repeatable production releases.

## 2. Build and start

```bash
docker compose config --quiet
docker compose up -d --build --wait --wait-timeout 180
docker compose ps
docker compose exec api python manage.py createsuperuser
curl -fsS -H 'Host: brollysolutions.in' http://127.0.0.1:3830/skillforge/api/health/
curl -I -H 'Host: brollysolutions.in' http://127.0.0.1:3830/skillforge/login
```

The API applies migrations and collects static files before starting Waitress.
The gateway waits for the API health check. `createsuperuser` asks for the trainer
email, name and password; there is no default password. With this configuration,
the containers expect an HTTPS public edge. Use the loopback URL for health
checks only and sign in through the HTTPS domain after configuring its proxy.

The server build requires access to Docker registries, PyPI and npm. It installs
Monaco as well as the application dependencies. Builds can temporarily use more
memory than running containers. Runtime limits are 1 GiB/1 CPU for the API and
128 MiB/0.5 CPU for the gateway; review available capacity on this busy server.

## 3. Connect the existing domain proxy

Identify which proxy currently terminates HTTPS for `brollysolutions.in`.
The container listing alone does not establish whether this is host Nginx,
Caddy, or another gateway. Do not replace the main website configuration.
Do not install the older systemd proxy template alongside this Docker template.

**Host Nginx:** merge `infra/docker/host-nginx-locations.conf` inside the existing
HTTPS `server` block for `brollysolutions.in`, alongside its current routes.
It contains these two locations and the required upload limits and timeouts:

```nginx
location = /skillforge { return 308 /skillforge/; }
location ^~ /skillforge/ {
    proxy_pass http://127.0.0.1:3830;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_http_version 1.1;
    proxy_set_header Connection "";
    client_max_body_size 12m;
    proxy_read_timeout 300s;
    proxy_send_timeout 300s;
    proxy_redirect off;
}
```

Keep `proxy_pass` without a trailing slash. The container gateway strips the
prefix once; Django sets its script prefix so generated links retain it.
Back up the existing proxy configuration, then validate and reload **if host
Nginx is the active proxy**:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

**Host Caddy:** add a path-specific `handle /skillforge/*` with
`reverse_proxy 127.0.0.1:3830` and an exact `/skillforge` redirect inside the
existing domain block. Preserve the site's existing catch-all route. Use
`handle`, not `handle_path`, because the full prefix must reach the container.
Validate the complete Caddyfile before reloading that existing service.

**Containerized public proxy:** its `127.0.0.1` refers to that proxy container,
not the host. Attach that proxy to the `skillforge_default` Docker network and
persist the external-network attachment in its own Compose configuration; use
`http://skillforge-gateway:8080`, the gateway's unique network alias. Keep the
proxy's other networks attached. Do not publish the API or
change this stack to expose port 3830 publicly just to work around routing.

## 4. Verify public routing and the classroom flow

```bash
curl -I https://brollysolutions.in/skillforge
curl -fsS https://brollysolutions.in/skillforge/api/health/
curl -I https://brollysolutions.in/skillforge/login
curl -I https://brollysolutions.in/skillforge/django-admin/
curl -I https://brollysolutions.in/skillforge/assets/missing.js
curl -I https://brollysolutions.in/skillforge/media/private.txt
```

Expect a redirect to `/skillforge/`, health JSON, successful login-page delivery,
an admin redirect whose Location retains `/skillforge/`, and 404 for both missing
assets and private media. Refresh a nested frontend route in a browser. Confirm
the main site and its existing routes still work. Then log in as trainer, create
a student, assign a manual assessment, submit as that student, and release the
result. Test material analysis/report generation after entering real keys.

Students receive access through the existing **Add student** workflow. It does
not send mail; share the generated initial password directly. They sign in at
`https://brollysolutions.in/skillforge/login` with email and password.

## Code execution

Piston remains a separately isolated runner. The main application stack does
not mount the Docker socket or start a privileged execution container on this
multi-application server. Follow [Piston setup](piston-setup.md) on a dedicated
Linux host/VM, and set `PISTON_URL` to its reachable private address ending in
`/api/v2`. Restrict runner access to the application server. A loopback runner
URL from local development will not work inside the API container.

```bash
docker compose up -d --force-recreate api
docker compose exec api python manage.py check_code_runner --check-limits
```

Until that passes, manual assessments work but Run Code is unavailable. Piston
does not require a paid Judge0 subscription; hosting resources are still needed.

## Persistence, updates and backups

The `skillforge_data` volume holds `/data/db.sqlite3` and private `/data/media`.
`skillforge_static` holds generated Django assets and is read-only in the gateway.
Neither contains files from other applications. Images and the release archive
exclude local accounts, materials and submissions, so the first deployment
starts with an empty database. Existing local classroom records require a
separate controlled database/media transfer before opening student access.

Use one API container with SQLite. PostgreSQL and shared caching should precede
horizontal scaling. The stack does not create PostgreSQL or Redis containers.
Restarting/rebuilding keeps both volumes. **Do not run `docker compose down -v`
or prune these volumes** unless you intend to delete classroom data.

For a consistent backup during a short maintenance window, stop writes, then
archive the data volume using the API image. No extra image or host database
tool is needed:

```bash
umask 077
mkdir -p backups
docker compose stop web api
docker compose run --rm --no-deps -T --entrypoint tar api -C /data -czf - . > "backups/data-$(date +%Y%m%d-%H%M%S).tar.gz"
docker compose start api web
```

Check the command exit status, verify the archive and store encrypted off-server
copies along with `.env`. Test restores in a separate environment. Restore only
while the services are stopped and retain UID/GID 10001 ownership for API data.
Backups are excluded from Docker build contexts, Git and release packaging.

After backing up, update the source and run:

```bash
docker compose up -d --build --wait --wait-timeout 180
docker compose ps
docker compose logs --tail=100 api web
```

An image rollback may require restoring its matching pre-migration database.
Do not run a global `docker compose down` from another project's directory.
Recreate the API after changing `.env`; a simple restart does not reload Compose
environment values. Console email is suitable for direct student access; if you
enable invitation/password-reset emails, configure SMTP and protect logs which
can contain console email links. Rotate logs and expire old JWT blacklist entries
periodically with `docker compose exec api python manage.py flushexpiredtokens`.

## Validation limits

The Docker executable on the development machine points to a missing installation.
Container builds, Linux volume ownership, Nginx syntax/runtime and live server
routing must therefore be validated on your server using the commands above.
YAML parsing, environment generation, source packaging, backend tests and the
frontend subpath build are checked locally; these do not replace a container run.

References: [Compose startup order](https://docs.docker.com/compose/how-tos/startup-order/),
[Nginx proxy URI handling](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_pass),
[NGINX unprivileged image](https://github.com/nginx/docker-nginx-unprivileged).
