# Sinel Hospital Digital Platform

![Sinel Hospital](website/static/img/sinel_logo2.png)

A portfolio-safe snapshot of the digital hospital platform developed for
[Sinel Specialist Hospital](https://sinelhospital.com/). The project combines
a responsive public website with a secure content and operations dashboard,
allowing the hospital team to manage evolving services without routine code
changes.

> This is a clean showcase snapshot with a single public history. It contains
> no production credentials, patient records, database backups, uploaded
> content, server access information, or production deployment configuration.

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
local demonstration.

## Repository boundary

This public repository is not the production deployment source. Production
history, infrastructure, environment files, backups, live media, credentials,
and operational data are maintained separately and privately.

Source is presented for portfolio review. Copyright remains with the respective
owners; no licence is granted unless explicitly stated.
