# Deploy at https://brollysolutions.in/skillforge/

For the existing Docker server, follow [Docker deployment](docker-deployment.md),
which uses host port **3830**. The instructions below are the alternative systemd
installation; do not combine its port 8010 proxy template with the Docker stack.

## Status and hosting requirement

The app now supports this subpath: frontend routes/assets, API calls, student sign-in links, report redirects, editor assets, Django pagination, and password/invitation links. The local production-path build is in `frontend/dist-brolly`. Nothing has been uploaded to brollysolutions.in.

Publishing requires access to the existing domain's hosting and routing configuration. The supplied templates target a Linux VPS with Nginx and systemd. They must be adapted after identifying your actual host; do not replace your existing site's configuration with these snippets. If the site is on shared/static hosting, ask the provider whether it supports Python WSGI apps and reverse-proxy rules for this path. A separate backend server may be needed. DNS records alone cannot route `/skillforge`.

Piston is a separate dependency. Deploying Django and React does not install the runner. Follow [Piston setup](piston-setup.md) before accepting coding assessments.

## URL layout

| Public URL | Destination |
| --- | --- |
| `/skillforge` | Redirect to `/skillforge/` |
| `/skillforge/login` and other app routes | React SPA with `/skillforge/` base |
| `/skillforge/assets/*`, `/skillforge/monaco/*` | Built frontend assets; missing files return 404 |
| `/skillforge/api/*` | Django `/api/*`, with external script prefix `/skillforge` |
| `/skillforge/django-admin/*` | Django administration |
| `/skillforge/static/*` | Collected Django static files |
| `/skillforge/media/*` | Denied; documents use authenticated API downloads |

## Build

From `frontend` in a normal development/build environment:

```sh
npm install
npm run build:brolly
```

The `brolly` mode loads the non-secret `frontend/.env.brolly`. It produces `dist-brolly` while retaining the usual root-path build in `dist`. No API key belongs in these frontend files. In this restricted workspace, `npm run build:brolly:portable` produces the same paths without minification. Monaco is absent locally; install dependencies and rebuild on the deployment/build machine to include it.

## Linux VPS installation template

Use these steps only after the existing server has been inspected. Reserve `/srv/skillforge`, service account `skillforge`, and port 8010 for this app; adapt them if they conflict with something already installed.

1. Install Python with venv support, Node/npm for building, and Nginx if not already present. Keep the existing site's web server/TLS setup.
2. Create a dedicated unprivileged service account and place application source at `/srv/skillforge`. Keep backend code and secrets outside the existing website's public directory.
3. Create `/srv/skillforge/.venv` and install `backend/requirements.txt` there. Use a clean environment and pin/audit resolved dependencies for production.
4. Copy `infra/brolly/backend.env.example` to `/etc/skillforge/skillforge.env`. Replace the placeholder secret with a fresh random value, set your AI keys, runner URL, and any SMTP configuration. Restrict this file to root and the `skillforge` service account. Existing shell environment variables take precedence over dotenv files.
5. Create `/var/lib/skillforge/media` and `/srv/skillforge/staticfiles`, owned by `skillforge`. The database and uploads stay under `/var/lib/skillforge` and require backups.

To generate a secret locally on the server:

```sh
/srv/skillforge/.venv/bin/python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Do not reuse the development trainer password. The release archive excludes all local users, passwords, databases, uploaded materials, and `.env` secrets. If existing classroom data must be migrated, transfer the database and matching media privately as a consistent backup during downtime; do not upload them into the web root.

## Database, static files, and first trainer

Run Django management commands as the service user with `/etc/skillforge/skillforge.env` loaded into the process environment. One option is the included helper, which reads that exact dotenv file without printing secrets:

```sh
sudo -u skillforge /srv/skillforge/.venv/bin/python /srv/skillforge/scripts/manage-production.py migrate
sudo -u skillforge /srv/skillforge/.venv/bin/python /srv/skillforge/scripts/manage-production.py collectstatic --noinput
sudo -u skillforge /srv/skillforge/.venv/bin/python /srv/skillforge/scripts/manage-production.py createsuperuser
sudo -u skillforge /srv/skillforge/.venv/bin/python /srv/skillforge/scripts/manage-production.py check --deploy
```

Review deployment-check output. HSTS is deliberately not enabled by this app because it affects the entire parent domain; coordinate that policy with the main website administrator. The systemd service has a private temporary directory, read-only application code, and write access only to its state directory.

## Start the API

Copy `infra/brolly/skillforge.service` to `/etc/systemd/system/skillforge.service`. After reviewing the account, paths, and port:

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now skillforge
sudo systemctl status skillforge
```

Waitress listens only on `127.0.0.1:8010` and sets the request scheme to HTTPS. Public traffic must arrive through the existing HTTPS web server. The proxy removes `/skillforge` before forwarding; `DJANGO_SCRIPT_NAME=/skillforge` restores the public prefix for URL generation. Avoid stripping or adding the prefix twice.

## Attach the app to the existing website

1. Copy the contents of `frontend/dist-brolly/` into `/srv/skillforge/www/skillforge/`. Only frontend files belong here. Give Nginx read/traverse access.
2. Copy `infra/brolly/nginx-proxy.conf` to `/etc/nginx/snippets/skillforge-proxy.conf`.
3. Copy `infra/brolly/nginx-locations.conf` to `/etc/nginx/snippets/skillforge-locations.conf`.
4. In the **existing HTTPS `server` block for `brollysolutions.in`**, add:

```nginx
include /etc/nginx/snippets/skillforge-locations.conf;
```

5. Test before reloading:

```sh
sudo nginx -t
sudo systemctl reload nginx
```

The snippet defines only `/skillforge` routes. Keep the main website's locations, redirects, certificate, and any existing security/proxy configuration. If the server uses Apache, LiteSpeed, a hosting panel, or a CDN gateway, adapt routing there instead of installing a competing Nginx listener.

## Verify before inviting students

- Main website still loads at `/`, and existing product routes still work.
- `/skillforge` redirects once to `/skillforge/`.
- `/skillforge/login` loads directly and after refreshing; all script/style requests stay under `/skillforge/`.
- `/skillforge/api/health/` returns JSON; an unknown API URL returns an API 404 rather than HTML.
- Trainer login, adding a student, copied sign-in links, student login, uploads, downloads, and PDF reports work.
- Invitation/password-reset URLs include `/skillforge` if email workflows are enabled.
- Cookie names are SkillForge-specific, with the `/skillforge/` path; original site cookies are not overwritten.
- Piston's input/output and limit probes pass through `manage-production.py check_code_runner --check-limits`.
- Test student isolation, sample execution, final grading, score release, and a backup/restore procedure.

For rollback, retain the previous frontend directory and server configuration before deployment. Remove only the SkillForge include or restore its prior version, test Nginx configuration, and reload. Stop only the `skillforge` service if needed. Keep the private database/media backup; do not overwrite unrelated website files.

## References

- [Vite base paths](https://vite.dev/config/shared-options.html#base)
- [React Router BrowserRouter](https://reactrouter.com/api/declarative-routers/BrowserRouter)
- [Django FORCE_SCRIPT_NAME](https://docs.djangoproject.com/en/5.2/ref/settings/#force-script-name)
- [Nginx proxy_pass](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_pass)
- [Waitress production runner](https://docs.pylonsproject.org/projects/waitress/en/stable/runner.html)
