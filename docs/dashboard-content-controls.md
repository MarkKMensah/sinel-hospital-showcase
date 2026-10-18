# Dashboard content controls

## Scope

This guide describes the typed content controls available in the public
showcase. Use fictional records in a local demonstration; operational release
records and production datasets are not part of this repository.

This is a typed extension of the existing Django dashboard, not a page-builder
or an authentication/role-policy redesign. The existing content-manager,
read-only auditor and denied front-desk boundaries remain in force.

## Editor guide and content inventory

| Task | Dashboard location | Public consumers / rule |
| --- | --- | --- |
| Edit named page and section introductions | Website → Page text (`/dashboard/page-content`) | Homepage; About highlights/introductions; Contact; Gallery; Team; Partners; Services/detail; News; booking introduction/guidance; shared testimonial introductions |
| Edit the About hero, overview, mission, vision and values | Website → About | About; homepage story uses the same overview; years/availability values and labels also appear beside the homepage video and on Contact |
| Change location/contact details | Website → Contact | Header, footer, persistent actions, Contact and encoded Maps destinations; coordinates take priority over the address |
| Change availability statement, social destinations or WhatsApp | Website → Shared details | Contact and footer; social links and persistent WhatsApp actions; blank WhatsApp uses the Contact telephone |
| Choose featured portraits, partner logos and gallery cover | Website → Featured content & links | Up to three Team hero portraits, six Partners hero logos, one Gallery cover; hidden records never become eligible |
| Set gallery image descriptions and credits | Featured content & links → Gallery cover and descriptions | Cover, gallery cards and lightbox; blank alternative text falls back to the editable image name |
| Choose custom-page menu placement | Featured content & links → Page links | Explicit header/footer flags, label and numeric order; no alphabetical five-link cap; direct visible pages may have no menu link |
| Set search/sharing descriptions | Website → Search descriptions | Fixed-route title/description overrides; blank uses derived defaults; visible service/post/custom-page details derive from their editable title/body |
| Change banners, shortcuts, ribbons and video | Website → Homepage | Existing ordered/visible collections; video now also has poster description, optional duration and link label |
| Edit partners/testimonials/articles | Existing respective menus | Complete bound forms; partner description/destination/category retained; testimonial associations optional; existing hidden relationships marked but remain hidden publicly; original author retained |

Page copy uses a fixed registry of named sections with per-field limits, not
arbitrary markup. Standard maximums are 60 characters for a small section label,
110 for a heading and 420 for supporting text; smaller contexts have tighter
limits. The editor shows its actual limits. Counts use Unicode code points,
not grapheme clusters; combined emoji may count more than once. Copy whitespace
is normalized to single spaces and never silently truncated. Required copy
rejects blanks. Search overrides are optional, with 70/160-character limits.
Homepage story media permits decoded JPG/PNG/WebP/GIF up to 5 MB, 6000 pixels
per edge and 24 megapixels. Other pre-existing upload policies remain distinct.

Featured positions are bounded 0–9999; ties use stable record IDs. Collections
are not limited to the number of hero display slots. With no visible featured
selection, existing automatic selection is retained (including the historical
McCarthy preference for Team). Partner directory/home strip still include all
visible partners. Gallery collection remains newest-first independently of cover.

## Save, failure and withdrawal contract

- Public content is read at request time: an accepted save appears on the next
  origin request. No separate publish/build queue or private-draft preview is
  introduced. Existing visible/hidden publication semantics remain unchanged.
- New settings/copy rows are not seeded by GET or startup. Defaults are read-only
  fallbacks. Migrations add fields/tables without replacing business content.
- Field-scoped signed revisions reject stale dashboard forms with HTTP 409 and
  retain safe input. Open the latest saved version in another tab, compare and
  deliberately reapply the intended changes; do not blindly resubmit old tokens.
- Independent About sections and separate copy sections do not overwrite one
  another. Ordinary profile/page edits do not clear separate placement settings.
- Invalid input returns bound errors and no success notice. Upload storage
  failures return HTTP 503 after database rollback, retain safe draft text and
  keep the working asset reference. Re-select new files before retrying. File
  storage is not transactional; an orphan new upload can remain after a later
  failure. No automated deletion of old/shared assets is introduced.
- A lost response is still an unknown outcome: inspect the saved record before
  retrying. This is not a durable idempotent-create/receipt subsystem.
- Hiding/removing source records excludes them from controlled public placements;
  visible service/detail, post and custom-page routes preserve eligibility gates.
  Direct media files, third-party caches and downloaded copies are not erased.
- Legacy stored destinations are checked before public rendering. Rich text is
  sanitized on model saves and rendered through the same allowlist, including
  legacy rows; reads never rewrite saved history. Headings, lists, tables,
  figures, links and approved styles remain supported. Scripts, arbitrary embeds,
  executable links, unsafe CSS and unsupported fonts are not editorial controls.
  Raw SQL/bulk updates bypass model signals and are not editorial write paths.

## Deliberate fixed boundaries and optional future work

Fixed: approved layouts, logo assets, primary service/booking actions, form
field semantics, booking confirmation and emergency consequences, authorization,
security/session limits, derived service counts, integration code and
deployment authority. CMS controls do not grant access to arbitrary HTML/CSS,
scripts, secrets or permission settings. Clinical/factual claims and imagery
still require the hospital's editorial/consent authority; no legal certification
or rights metadata/expiry workflow is invented here.

Not introduced: arbitrary sections/layout composition, approval queues, private
prepublication preview, revision-history/restore UI, localization or content
export/import. Legacy Contact/About/Video rows are not destructively deduplicated:
the dashboard coordinates singleton writes, but generic admin/API paths can
still create extra legacy rows. New settings and keyed copy enforce identity.
Manager APIs do not acquire the dashboard's revision protocol. These boundaries
remain explicit rather than claiming universal content editability/concurrency.

## Verification and release gates

Run with isolated settings (never workstation/live settings):

```powershell
python manage.py test --settings=sinel_web.settings.testing --noinput
node --test tests/*.test.cjs
```

The suite covers bound failures, field limits/Unicode, escaping, unsafe legacy
URLs and HTML, optional/hidden relationships, original authors, visibility,
featured/menu placement, stale/forged revisions, storage rollback, denied roles,
CSRF, and populated-schema upgrades preserving fictional IDs, timestamps, files
and relationships. SQLite skips three PostgreSQL-specific concurrent-request
tests; GitHub runs the full suite separately on PostgreSQL 17. Request-start
barriers give concurrent-request regression evidence, not exhaustive lock-wait
fault injection. Local browser checks use a separate fictional database.

CI also checks migration drift, dependencies, security scanning, Node behaviour
and demo-container startup/failure handling. All required jobs must match
the exact pushed candidate before any future promotion. Native Safari/device
and nontechnical-editor acceptance remain separate from engine/test evidence.

Security-scan review: the single `mark_safe(sanitize_rich_html(value))` statement
has a documented B308/B703 exception after independent allowlist/attack-test
review. No raw value reaches that boundary; the full scanner remains enabled
elsewhere. Dependency: [nh3 0.3.7](https://pypi.org/project/nh3/0.3.7/), with
its maintained HTML parser/sanitizer rather than a custom HTML tokenizer.

Live chat is disabled in this demonstration; configure your own integration
separately if needed. This public snapshot is not a deployment package.
Use fictional content and isolated test settings. Operational backups, live
media, infrastructure configuration and private release records are excluded.
