# Showcase engineering overview

This repository demonstrates the application design without distributing the
production environment or its records. It is an independently maintained public
snapshot, not a deployment mirror. All test records should be fictional.

## Business-owned content, bounded by design

Editors manage content through typed dashboard forms rather than routine source
edits. The established layouts remain consistent while business details change.

| Content | Editor-to-public contract |
| --- | --- |
| Named introductions and section copy | 34 registered sections with context-specific limits and normalized plain text |
| Search and sharing text | Nine fixed routes; optional overrides fall back to derived descriptions |
| Shared information | Contact, availability, social and WhatsApp destinations feed their public consumers |
| Featured collections | Team portraits, partner logos and gallery cover select eligible visible records; hiding a record removes it from controlled placements |
| Custom pages | Independent header/footer flags, editable link labels and stable numeric ordering |
| Homepage content | Ordered visible banners, service shortcuts and optional ribbons, plus video labels, duration and poster descriptions |
| Existing editorial records | Services, team, partners, testimonials, awards, galleries, custom pages and articles retain their dashboard workflows |

Standard section bounds are 60 characters for an eyebrow, 110 for a heading and
420 for supporting text, with tighter limits in smaller contexts. The relevant
editor exposes its actual bounds. Limits count Unicode code points, not grapheme
clusters; combined emoji may count more than once. Excess input is rejected,
never silently truncated.

Content is read at request time. A successful save becomes visible on the next
origin request under existing visibility rules. Missing optional settings use
read-only defaults: page GETs and startup do not seed editorial database rows.

## Integrity and unhappy paths

- Signed, field-scoped dashboard revisions reject stale submissions with HTTP
  409 while retaining safe input. Independent About and page-copy sections do not
  overwrite one another. Compare the latest saved version before reapplying an
  intended change.
- Invalid submissions return bound field errors without a success notice.
  Optional and hidden relationships are handled explicitly rather than silently
  clearing existing associations. Existing article authors are preserved.
- Storage failure rolls back the database save and returns HTTP 503, retaining
  safe text and the working asset reference. Re-select a new file before retry.
  File storage is not transactional: an orphan new file can remain after a later
  failure. Automatic deletion of old or shared assets is not implemented.
- Rich text is sanitized by an allowlist on model saves and public rendering,
  including legacy values. Reads do not rewrite stored content. Unsafe legacy
  links are rejected before rendering. Scripts, arbitrary embeds and executable
  URLs are not content-management capabilities.
- Dashboard permissions apply server-side. Being able to edit public copy does
  not grant account, permission, secret or deployment access.
- A lost save response is an unknown outcome, not proof of failure. Inspect the
  stored record before retrying; this is not a durable idempotent-create system.

## Deliberate limits

The design is not an arbitrary page builder. Approved layouts, logo assets,
primary service/booking actions, form semantics, clinical consequences, security
policy and deployment authority remain fixed. Public service counts are derived,
not editable marketing numbers. Clinical claims and imagery still require the
organisation's factual, editorial and consent approval.

Private-draft preview, multi-stage approvals, editorial revision-history restore,
localization, and content import/export are not introduced. Legacy singleton
records are coordinated by dashboard writes rather than destructively cleaned
up; generic administration/API paths can still create extra legacy rows.
Manager APIs do not acquire the dashboard's stale-form protocol. Raw SQL and
bulk updates are not supported editorial write paths and bypass model signals.

Hiding content removes it from controlled public pages and placements; it does
not erase direct media files, third-party caches or downloaded copies. Native
browser/device acceptance and nontechnical-editor usability are separate from
automated server or JavaScript evidence.

## Verification and publication boundary

The test workflow separates in-memory SQLite from an ephemeral PostgreSQL 17
service using dedicated testing settings and fictional data. PostgreSQL exercises
database-specific concurrency and populated migration checks that SQLite cannot
establish. The JavaScript suite checks browser-independent behavior; it is not a
substitute for native Safari or assistive-technology testing.

Dependency auditing and Python scanning remain enabled. One reviewed scanner
exception marks only the output of `sanitize_rich_html` safe for template use;
raw stored or submitted values do not pass that boundary. Passing these checks
is not a penetration test or certification.

The demo-container check verifies real startup and migrations,
and rejects startup if migration fails. The public-snapshot check is an
additional admission guard, not a guarantee that arbitrary future files are safe
to publish. Review the staged file list, secrets/data scan and reachable public
history before each publication.

The public workflow cannot deploy production. Production infrastructure,
Nginx/TLS configuration, operational helpers, backups and real editorial datasets
are intentionally outside this repository. Sanitized source updates are public
commits in this repository only; private commits and Git objects are not merged
or copied into its history.
