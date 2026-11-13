# Year Wheel: project conventions

## Hard rules
- Licence: MIT, Copyright (c) 2026 Robert Tomkowski <rtom@kth.se>, developed with the
  assistance of Claude Code. New source files start with the two-line notice used in tools/*.py
  (HTML/CSS comment, or `$comment` in JSON Schema); data files (templates, examples) carry none.
- `yearwheel.html` is ONE self-contained file: inline CSS, vanilla JS, inline SVG. No build step,
  no CDN, no external fonts, no network calls of any kind. It must open by double-click (file://)
  in current Chrome, Edge, Firefox and Safari.
- Python tools: stdlib only (pytest for tests). Must run on Python 3.8 (no `match`, no `X | Y`
  type unions, no `dict[str, int]` style generics at runtime).
- Never hardcode institution calendar dates as facts. Study periods, quarter start and year start
  are user settings; template dates are placeholders (`placeholder: true`, titles end "(edit me)").
- No em dashes in UI text or docs.
- Moving or cancelling an event must always record a non-empty reason in the changelog.

## Data
- Schema: `schema/wheel.schema.json` (draft 2020-12). Current `schemaVersion` is 1.
- Changing the data model: bump the version, add a migration in BOTH `MIGRATIONS` in
  `yearwheel.html` and `tools/wheellib.py`, update `KEY_ORDER` in the HTML, and update the schema.
- Canonical key order: the app writes keys in `KEY_ORDER`; `tools/build_templates.py` builds dicts
  in the same order so files round-trip byte for byte. Unknown fields are preserved on save.
- Dates are `YYYY-MM-DD` strings; the app works in whole UTC day numbers (`d2n`/`n2d`).
  Span `end` is inclusive.
- Theme is a per-viewer preference in localStorage, not part of the wheel file.
- Text size: `settings.textScale` (0.7 to 1.5, omitted = 1) via `textScale()`. CSS sizes of wheel text
  use `calc(Npx * var(--ts))` (set on the SVG by renderWheel); JS layout (arc label fit, outer label
  line height and length, centre title wrap, legend widths and two-row wrap) multiplies by it too.
  Outer labels get their size from a `font-size` attribute, so `.ext-lbl` must not set font-size in CSS.
- Rotation: `wheelRotation()` turns the wheel so 1 January is at 12 o'clock (default) or, with
  `settings.wheelTop = 'yearStart'`, the year start. All angles go through `A(n)` (which adds the
  rotation); use `normA()` before comparing angles (label side, text flip) and subtract
  `state.wheelRot` when mapping a click back to a date (`svgDate`).
- CSV: `wheelToCsv()` and `csvTemplate()` (PARSERS block) write the same columns `csvToItems()` reads
  (`CSV_COLUMNS`), semicolon separated, UTF-8 BOM and an Excel `sep=;` line (skipped on import).
  Swedish headings and status words are aliases. `tests/test_js_parsers.py` round-trips the demo wheel.
- `ring.hidden: true` keeps a ring but leaves it out of the drawing, legend, print and image exports
  (renderWheel filters it). Its events stay in the list, change log, reviews and ICS export.
- Colour tints go through `alpha(rel, cap)`: rel x `settings.colorOpacity` (0.1 to 1, omitted =
  `COLOUR_DEFAULT` 0.4). Span fill rel is 1, so 100% is exactly the picker colour. The band behind
  each ring uses its own `settings.ringOpacity` (0 to 1, omitted = `RING_DEFAULT` 0.1). From
  `STRONG_BAND` (0.5) events are outlined in `var(--panel)` so they stand out from a same-coloured
  band. `labelInk(col, a, bandA)` blends event over band over `--panel` and keeps the theme text
  colour at contrast 4.5 or more, else white or near-black; the wheel is redrawn on theme change,
  print and export.
  The older `colorStrength` (0.5 to 1.75) is converted in `withDefaults()`.
- Span times: spans may also have `startTime`/`endTime`, and then need `timing`: `daily` (same hours
  each day; ICS `RRULE:FREQ=DAILY;COUNT=n`, or one yearly VEVENT per day with UID `<id>-dN` when the
  span repeats yearly) or `continuous` (one VEVENT from the first day's start to the last day's end;
  12:00 to 12:00 is valid). Import maps `FREQ=DAILY` (COUNT/UNTIL, interval 1) to daily spans and
  multi-day timed events to continuous spans; an end exactly at midnight stays whole days.
- Times: optional `startTime`/`endTime` ("HH:MM", both or neither, end after start on one day).
  They are wall-clock times in `settings.timeZone` (IANA name; set automatically to the browser's
  zone the first time a time is entered). A change of time is a `moved` change (needs a reason) and
  changelog ranges carry the times. ICS export writes timed milestones in UTC (`...Z`), converted with
  `zonedToUtc` (Intl only, no libraries). Known limit: a yearly timed event uses the UTC time of its
  first date, so a date within days of a DST switch can be an hour off in other years.
- Repeats within the year: `recurrence` `weekly` or `monthly` with optional `interval` (1 to 52),
  `monthlyBy: 'weekday'` (milestones only: same weekday in the same week of the month, 5th week =
  last) and `until` (last allowed start). Dates come from `repeatStarts` (PARSERS block) and
  `wheellib.repeat_starts`, kept identical. Single meetings live in `exceptions`
  (`{date, status: done|cancelled|moved, start, end}`, keyed by original date) and are changed only
  through `setOccurrence()`, which logs like whole events (reason for moved/cancelled). Wheel marks
  carry `data-occ`; `occurrences()` returns `occ`, `st` and `prev` for them. Moving a series' start
  maps exceptions by occurrence number (`keepExceptions`). ICS export: RRULE with INTERVAL, BYDAY
  and UNTIL, timed series in TZID local time with a VTIMEZONE built from Intl (`icsVtimezone`),
  EXDATE for cancelled and RECURRENCE-ID entries for moved meetings; import folds them back.
  Additive fields, so `schemaVersion` stays 1 (as with `timing` and `hidden`).
- ICS import: `parse_ics`/`parseIcs` return raw `startAt`/`endAt`/`tz`; `event_times`/`icsLocalTimes`
  convert to the wheel zone. Zones that cannot be resolved (Outlook's Windows names, floating times)
  are taken as written. Python 3.8 has no zoneinfo, so the CLI converts UTC to the computer's zone.

## Language
- UI text lives in `STR.en` and `STR.sv`; every key must exist in both (`test_every_ui_text_has_english_and_swedish`).
  Use `t('key')` in JS, `data-i18n`, `data-i18n-ph` and `data-i18n-aria` in HTML. No English text in code.
- The UI language is each person's choice (`localStorage` key `yearwheel.lang`, default from
  `navigator.language`), set with the toolbar picker (`setLang`). It is not read from the wheel file;
  `settings.language` only records the language a wheel was created in.
- Templates exist in both languages: `to_swedish()` in `tools/build_templates.py` with the `SV`
  dictionary (the build fails on a missing translation); output in `templates/sv/`. The embedded
  copy is `{id, label: {en, sv}, wheel: {en, sv}}`.

## Templates
- Defined in `tools/build_templates.py`. Run it after any change: it writes `templates/*.json`
  and rewrites the embedded copy between `/*TEMPLATES-BEGIN*/` and `/*TEMPLATES-END*/` in the HTML.
- When a wheel is created from a template, each date keeps its day and month and is moved by
  whole years into the matching year of the new wheel.

## App structure (sections marked in yearwheel.html)
I18N (`STR` dictionaries, `t()`), UTILS, TEMPLATES, MODEL (migrate, canonical, checkWheel),
STATE (`commit()` is the only way to mutate the wheel; it logs, marks dirty, drafts, re-renders),
FILE I/O (File System Access API with download/upload fallback), WHEEL RENDERER, TOOLTIP, DRAWER,
DIALOGS (`ask()`/`settle()` resolve from button handlers, not the async close event), INIT.

Also: EVENT CHANGES (`moveEvent`, `cancelEvent`, `markDone`), QUARTERS (`quarterOf`: labelled by
the year Q1 starts in), QUARTERLY REVIEW MODE, LIST VIEW, CHANGE LOG VIEW, EXPORT. Views are
switched with `setView()`; the wheel SVG is always rendered because export and print read it.
SVG export resolves computed styles inline with the light theme forced, so no CSS variables leak out.

Also IMPORT (ICS/CSV dialog with per-event ring choice).

Saving: with the File System Access API the last file handle is kept in IndexedDB (`yearwheel` db,
`handles` store, key `lastFile`, value `{h, id}`) and reconnected by `restoreHandle()` after
Continue/Restore when name and wheel id match; Save checks permission with `canWrite()`. Without the
API (or when the picker throws), Save downloads under the current name and Save as asks for a
name in `dlgSaveAs` (`askFileName`).

Testing hook: `yearwheel.html?today=2027-04-02` overrides today's date (drives the review banner).

## Parsers shared between browser and Python
- The block between `/*PARSERS-BEGIN*/` and `/*PARSERS-END*/` in the HTML (`parseIcs`, `stableId`,
  `icsItemId`, `csvToItems`, `wheelToIcs`) must stay pure: no DOM, no other app globals.
  `tests/test_js_parsers.py` runs it in Node and asserts it matches `tools/wheellib.py`
  (`parse_ics`, `stable_id`, `ics_events_to_wheel_events`). Change both sides together.
- ICS ids: FNV-1a hash of the UID (`ics-xxxxxxxx`), so re-imports are detected. UIDs exported by
  the app are `<event id>@yearwheel` and map back to the original id.
- Quarter start rule (`quarter_start_month` / `quarterStartFor`): the year's first month, or the
  next month when the year starts after the 15th. Keep the Python and JS versions identical.

## Milestones
1. MVP: wheel view, editor, rings, settings, JSON open/save, Blank and Research team templates. (done)
2. List view, changelog view, quarterly review mode, SVG/PNG export, print CSS (A4/A3 landscape). (done)
3. ICS/CSV import, ICS export, remaining templates, `tools/ics_to_wheel.py`, full pytest suite. (done)

## Release package
- `tools/build_demo.py` writes the fictional demo wheel (`examples/`); keep it free of real names.
- `tools/build_release.py` (needs Chrome and pandoc) takes screenshots of the demo with a fixed
  today (2026-11-10) into `docs/images/`, builds `dist/Year-Wheel-User-Guide.pdf` from
  `docs/user-guide.md` + `docs/guide.css`, the poster from `docs/poster.html` (A4, 794x1123 px), and
  `dist/Year-Wheel.zip`. Rebuild after UI changes so screenshots and the guide stay current.

## Public repository and website
- This repository is the private working copy. The public one is github.com/rtomkowski/yearwheel,
  checked out in `../yearwheel`, with its own history (commits as Robert Tomkowski <rtom@kth.se>,
  set in that repository only). Ask the user which email to use before changing that.
- Publish: `python3 tools/build_release.py`, `python3 tools/build_site.py`, then
  `python3 tools/export_public.py` (copies everything except `dist/` and `.claude/`); review,
  commit and push in `../yearwheel`. A version bump gets a GitHub Release with `dist/Year-Wheel.zip`,
  the guide PDF and the poster PDF attached (the website links to releases/latest/download/...).
- `website/` is the GitHub Pages site (landing page and guide sources in `docs/site/`); the
  `Website` workflow publishes it on pushes that change it. `app/demo.html` is the app with the
  demo wheel injected at build time (no network request).

## Checks before committing
```
python3 tools/build_templates.py && python3 tools/validate.py templates/*.json
python3 -m pytest   # includes: templates valid and embedded copy current, no network code, no em dashes
```
