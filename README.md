# Sinel Hospital Digital Platform

![Sinel Hospital](website/static/img/sinel_logo2.png)

A portfolio-safe snapshot of the digital hospital platform developed for
[Sinel Specialist Hospital](https://sinelhospital.com/). The project combines
a responsive public website with a secure content and operations dashboard,
allowing the hospital team to manage evolving services without routine code
changes.

> This showcase has its own public Git history, separate from the private
> production repository. It excludes production credentials, patient records,
> database backups, live media uploads, server access information, and production
> deployment configuration. Public branding and application source are included
> for portfolio review.

## Portfolio context

This repository showcases product and engineering work spearheaded by
Mark K. Mensah across platform recovery, security hardening, dependency
modernisation, content-management flexibility, administrative workflows,
responsive experience design, testing, and release governance. It is a
technical portfolio artifact rather than a production mirror.

## Project highlights

- Responsive public website for services, clinicians, partners, media,
  testimonials, awards, news, and appointment booking
- Dashboard-managed homepage banners, featured service shortcuts, promotional
  ribbons, hospital video, and recognition content
- Bounded editing for 34 established page sections and search/sharing metadata
  on nine fixed routes, alongside shared contact, availability and social details
- Curated team portraits, partner logos, gallery cover and image descriptions,
  with explicit custom-page menu placement and ordering
- Rotating homepage banners with editable headings and links, responsive image
  presentation, playback controls, and reduced-motion support
- Consistent team visibility controls across the dashboard and public website
- Service directory and navigation that automatically follow published
  dashboard records
- Appointment workflow with compact operational views and CSV/Excel-friendly
  export
- Role-based staff access, administrator status management, access auditing,
  and token invalidation
- Secure CKEditor 5 content authoring and restricted image uploads
- Allowlisted rich-text sanitization on saves and public rendering, including
  legacy stored content, with signed stale-form rejection in dashboard editors
- Responsive galleries, testimonial navigation, partner presentation, and
  persistent appointment, telephone, and WhatsApp actions
- Regression coverage across public pages, dashboard permissions, publishing
  controls, and appointment workflows

## Engineering focus

The platform was modernised around four priorities:

1. **Business agility** — hospital staff can create, update, feature, hide, or
   remove public content from the dashboard.
2. **Operational clarity** — appointments and administrative records are
   compact, searchable, ordered, and exportable.
3. **Security and maintainability** — supported dependencies, explicit
   permissions, safer uploads, deployment-aware settings, and audit records.
4. **Patient experience** — responsive pages, accessible interactions, clear
   service discovery, and persistent contact options.

## Technology

- Python 3.12 and Django 5.2 LTS
- PostgreSQL 17
- Django REST Framework and Knox authentication
- CKEditor 5
- HTML, CSS, Bootstrap Icons, and native JavaScript
- Docker for a reproducible local development environment

## Local demonstration

1. Copy `.env.example` to `.env.dev`.
2. Replace the example-only local values if desired.
3. Run:

   ```bash
   docker compose up --build
   ```

4. Open `http://127.0.0.1:8000/`.

The repository intentionally ships without real hospital records. Add sample
content through Django administration or the project dashboard when running a
local demonstration. Create a local administrator with:

```bash
docker compose exec web python manage.py createsuperuser
```

Use fictional identities and records only. No working account or password is
bundled, and the example environment values are for local development only.
Live hospital chat is disabled. Configure your own integration separately.
The demo binds only to loopback; rebuild the image after source changes. Its
database uses a named local volume, while uploaded demo media is not persisted
when the web container is replaced.

## Checks and engineering notes

GitHub Actions runs isolated Django regression tests on SQLite and PostgreSQL 17,
JavaScript behavior tests, migration-drift checks, dependency auditing, Python
security scanning, a public-snapshot boundary check, and demo-container startup
and startup-failure checks. The workflow uses SHA-pinned Node 24 actions and a
fixed Ubuntu 24.04 runner; it has no deployment job and only read permission.

To run the application checks without reading a workstation database:

```bash
python -m pip install -r requirements-dev.txt
python manage.py check --settings=sinel_web.settings.testing
python manage.py makemigrations --check --dry-run --settings=sinel_web.settings.testing
python manage.py test --noinput --settings=sinel_web.settings.testing
node --test tests/*.test.cjs
python tools/check_public_snapshot.py --tree HEAD
```

See [the engineering overview](docs/showcase-engineering.md) for the content
architecture, unhappy paths, and deliberate limits. A workflow definition is not
a claim that a particular revision passed; use its exact GitHub Actions results.

## Repository boundary

This public repository is not the production deployment source. Production
history, infrastructure, environment files, backups, live media, credentials,
and operational data are maintained separately and privately.

Production Nginx/TLS configuration, deployment automation, and infrastructure
tests are deliberately excluded. Their omission is a publication boundary, not
an instruction to use the local demo as a production deployment template. Source
updates arrive as reviewed, sanitized snapshots rather than private-history
merges; public history contains only showcase work.

Source is presented for portfolio review. Copyright remains with the respective
owners; no licence is granted unless explicitly stated.
