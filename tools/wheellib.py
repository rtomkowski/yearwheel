# Year Wheel. Copyright (c) 2026 Robert Tomkowski <rtom@kth.se>
# MIT License (see the LICENSE file). Developed with the assistance of Claude Code (Anthropic).

"""Shared helpers for the Year Wheel Python tools.

Stdlib only. Python 3.8 compatible.
- A small JSON Schema validator covering the keywords used in schema/wheel.schema.json.
  If the `jsonschema` package is installed it is used instead (see validate()).
- Schema migration hook.
- Changelog rules that the schema cannot express on its own.
"""

import datetime
import json
import os
import re
from typing import Any, Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_PATH = os.path.join(ROOT, "schema", "wheel.schema.json")
CURRENT_SCHEMA_VERSION = 1


def load_schema() -> Dict[str, Any]:
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_wheel(path: str) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return migrate(json.load(f))


def dump_wheel(wheel: Dict[str, Any], path: str) -> None:
    """Write a wheel as pretty JSON with a trailing newline (stable, diff friendly)."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(wheel, f, indent=2, ensure_ascii=False)
        f.write("\n")


def quarter_start_month(year_start: str) -> int:
    """Q1 starts in the year's first month, or the next month if the year starts after the 15th
    (an academic year starting 31 August has quarters from September). Mirrors quarterStartFor() in the app."""
    m, d = int(year_start[5:7]), int(year_start[8:10])
    return m if d <= 15 else m % 12 + 1


# ---------------------------------------------------------------- migration

# Each entry upgrades a wheel from version N to N+1. Version 0 means "no schemaVersion field".
def _migrate_0_to_1(w: Dict[str, Any]) -> Dict[str, Any]:
    w.setdefault("settings", {})
    for key in ("rings", "events", "reviews", "changelog"):
        w.setdefault(key, [])
    w["schemaVersion"] = 1
    return w


MIGRATIONS = {0: _migrate_0_to_1}


def migrate(wheel: Dict[str, Any]) -> Dict[str, Any]:
    version = wheel.get("schemaVersion", 0)
    while version < CURRENT_SCHEMA_VERSION:
        wheel = MIGRATIONS[version](wheel)
        version = wheel["schemaVersion"]
    if version > CURRENT_SCHEMA_VERSION:
        raise ValueError("File uses schemaVersion %s, newer than this tool (%s)" % (version, CURRENT_SCHEMA_VERSION))
    return wheel


# ---------------------------------------------------------------- validator

_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "null": type(None),
}


def _is_type(value: Any, name: str) -> bool:
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, _TYPES[name])


def _resolve(ref: str, root: Dict[str, Any]) -> Dict[str, Any]:
    if not ref.startswith("#/"):
        raise ValueError("Only local $ref supported: %s" % ref)
    node = root
    for part in ref[2:].split("/"):
        node = node[part]
    return node


def _valid_date(s: str) -> bool:
    try:
        datetime.date.fromisoformat(s)
        return True
    except ValueError:
        return False


def _check(value: Any, schema: Dict[str, Any], root: Dict[str, Any], path: str, errors: List[str]) -> None:
    if "$ref" in schema:
        _check(value, _resolve(schema["$ref"], root), root, path, errors)
    if "const" in schema and value != schema["const"]:
        errors.append("%s: expected %r" % (path, schema["const"]))
    if "enum" in schema and value not in schema["enum"]:
        errors.append("%s: %r is not one of %s" % (path, value, schema["enum"]))
    if "type" in schema and not _is_type(value, schema["type"]):
        errors.append("%s: expected %s" % (path, schema["type"]))
        return
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append("%s: must not be empty" % path)
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append("%s: %r does not match %s" % (path, value, schema["pattern"]))
        if schema.get("format") == "date" and not _valid_date(value):
            errors.append("%s: %r is not a valid date" % (path, value))
    if _is_type(value, "number"):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append("%s: below minimum %s" % (path, schema["minimum"]))
        if "maximum" in schema and value > schema["maximum"]:
            errors.append("%s: above maximum %s" % (path, schema["maximum"]))
    if isinstance(value, list):
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append("%s: at most %d items allowed" % (path, schema["maxItems"]))
        if "items" in schema:
            for i, item in enumerate(value):
                _check(item, schema["items"], root, "%s[%d]" % (path, i), errors)
    for sub in schema.get("allOf", []):
        _check(value, sub, root, path, errors)
    if "anyOf" in schema:
        if not any(not _probe(value, sub, root, path) for sub in schema["anyOf"]):
            errors.append("%s: does not match any allowed form" % path)
    if "not" in schema and not _probe(value, schema["not"], root, path):
        errors.append("%s: has a combination of fields that is not allowed" % path)
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                errors.append("%s: missing required field '%s'" % (path, key))
        for key, needs in schema.get("dependentRequired", {}).items():
            if key in value:
                for other in needs:
                    if other not in value:
                        errors.append("%s: '%s' requires '%s'" % (path, key, other))
        for key, sub in value.items():
            if key in props:
                _check(sub, props[key], root, "%s.%s" % (path, key), errors)
            elif schema.get("additionalProperties") is False:
                errors.append("%s: unknown field '%s'" % (path, key))
    if "if" in schema:
        if not _probe(value, schema["if"], root, path) and "then" in schema:
            _check(value, schema["then"], root, path, errors)


def _probe(value: Any, schema: Dict[str, Any], root: Dict[str, Any], path: str) -> List[str]:
    """Errors of a subschema, without reporting them (for if, not and anyOf)."""
    errs = []  # type: List[str]
    _check(value, schema, root, path, errs)
    return errs


def validate(instance: Any, schema: Optional[Dict[str, Any]] = None, use_jsonschema: bool = True) -> List[str]:
    """Return a list of human readable errors (empty when valid)."""
    schema = schema or load_schema()
    if use_jsonschema:
        try:
            import jsonschema  # type: ignore
            cls = jsonschema.validators.validator_for(schema)
            v = cls(schema, format_checker=jsonschema.FormatChecker())
            return ["%s: %s" % ("$" + "".join("[%r]" % p for p in e.absolute_path), e.message)
                    for e in v.iter_errors(instance)]
        except ImportError:
            pass
        except Exception:  # unsupported draft in an old jsonschema: fall back
            pass
    errors = []  # type: List[str]
    _check(instance, schema, schema, "$", errors)
    return errors


# ---------------------------------------------------------------- semantic rules

def check_rules(wheel: Dict[str, Any]) -> List[str]:
    """Rules beyond the schema: unique ids, ring references, date order, changelog reasons."""
    errors = []  # type: List[str]
    ring_ids = [r["id"] for r in wheel.get("rings", [])]
    if len(set(ring_ids)) != len(ring_ids):
        errors.append("rings: duplicate ring id")
    ev_ids = [e["id"] for e in wheel.get("events", [])]
    if len(set(ev_ids)) != len(ev_ids):
        errors.append("events: duplicate event id")
    for e in wheel.get("events", []):
        if e.get("ringId") not in ring_ids:
            errors.append("event %s: unknown ringId %r" % (e.get("id"), e.get("ringId")))
        if e.get("kind") == "span" and e.get("end", "") < e.get("start", ""):
            errors.append("event %s: end is before start" % e.get("id"))
        # The end time must be after the start time on the same day: milestones, spans with the same
        # hours each day, and continuous spans that start and end on one date.
        same_day = e.get("kind") != "span" or e.get("timing") == "daily" or e.get("end") == e.get("start")
        if "startTime" in e and "endTime" in e and same_day and e["endTime"] <= e["startTime"]:
            errors.append("event %s: end time must be after start time" % e.get("id"))
    errors.extend(check_changelog_rules(wheel))
    return errors


def check_changelog_rules(wheel: Dict[str, Any]) -> List[str]:
    errors = []  # type: List[str]
    for i, c in enumerate(wheel.get("changelog", [])):
        if c.get("action") in ("moved", "cancelled") and not str(c.get("reason", "")).strip():
            errors.append("changelog[%d]: '%s' needs a reason" % (i, c.get("action")))
    return errors


def full_check(wheel: Dict[str, Any]) -> List[str]:
    return validate(wheel) + check_rules(wheel)


# ---------------------------------------------------------------- ICS (iCalendar) parsing
# Mirrors parseIcs() in yearwheel.html. Handles Outlook and Google exports:
# CRLF or LF, folded lines, VALUE=DATE all-day events, TZID and UTC date-times,
# escaped text, RRULE FREQ=YEARLY and STATUS:CANCELLED. Times are dropped: the wheel works in days.

def _unfold(text: str) -> List[str]:
    lines = []  # type: List[str]
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if raw[:1] in (" ", "\t") and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    return lines


def _unescape(s: str) -> str:
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            n = s[i + 1]
            out.append("\n" if n in "nN" else n)
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out).strip()


def _ics_dt(value: str):
    """'20270203T130000Z' -> (date, '13:00', True). Time is '' for a plain date. None if unreadable."""
    m = re.match(r"^(\d{4})(\d{2})(\d{2})(?:T(\d{2})(\d{2})(\d{2})?(Z?))?$", value.strip())
    if not m:
        return None
    try:
        d = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None
    if m.group(4) and int(m.group(4)) > 23:
        return None
    return d, ("%s:%s" % (m.group(4), m.group(5)) if m.group(4) else ""), bool(m.group(7))


def _ics_duration(value: str) -> Optional[datetime.timedelta]:
    m = re.match(r"^P(?:(\d+)W)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?$", value.strip())
    if not m or not any(m.groups()):
        return None
    w, d, h, mi, s = (int(g or 0) for g in m.groups())
    return datetime.timedelta(weeks=w, days=d, hours=h, minutes=mi, seconds=s)


def parse_ics(text: str) -> List[Dict[str, Any]]:
    """Return a list of {uid, title, start, end, startAt, endAt, tz, recurrence, status, notes, categories}.

    start/end are ISO dates (end inclusive, equal to start for single-day items).
    For timed events startAt/endAt are the raw wall times 'YYYY-MM-DDTHH:MM' as written in the file
    and tz is 'UTC', the TZID, or '' (floating). They are '' for all-day events.
    Use event_times() to turn them into times in the wheel's zone.
    """
    events = []  # type: List[Dict[str, Any]]
    cur = None  # type: Optional[Dict[str, Any]]
    depth = 0  # nesting inside VEVENT (VALARM blocks are skipped)
    for line in _unfold(text):
        if not line.strip():
            continue
        name_params, _, value = line.partition(":")
        parts = name_params.split(";")
        name = parts[0].upper()
        params = {}
        for p in parts[1:]:
            k, _, v = p.partition("=")
            params[k.upper()] = v.strip('"')
        if name == "BEGIN":
            if value.upper() == "VEVENT" and cur is None:
                cur = {"props": {}}
            elif cur is not None:
                depth += 1
            continue
        if name == "END":
            if cur is not None and depth:
                depth -= 1
            elif cur is not None and value.upper() == "VEVENT":
                ev = _finish_event(cur["props"])
                if ev:
                    events.append(ev)
                cur = None
            continue
        if cur is not None and not depth and name not in cur["props"]:
            cur["props"][name] = (value, params)
    return events


def _daily_count(rrule: str, start: datetime.date) -> int:
    """Number of days for RRULE FREQ=DAILY with COUNT or UNTIL (interval 1); 0 otherwise."""
    parts = dict(p.split("=", 1) for p in rrule.split(";") if "=" in p)
    if parts.get("FREQ") != "DAILY" or parts.get("INTERVAL", "1") != "1":
        return 0
    if parts.get("COUNT", "").isdigit():
        return int(parts["COUNT"])
    until = _ics_dt(parts.get("UNTIL", ""))
    return max(0, (until[0] - start).days + 1) if until else 0


def _finish_event(props: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if "DTSTART" not in props:
        return None
    sval, sparams = props["DTSTART"]
    s = _ics_dt(sval)
    if s is None:
        return None
    start, stime, sutc = s
    all_day = sparams.get("VALUE", "").upper() == "DATE" or not stime
    end = start
    start_at = end_at = tz = ""
    if all_day:
        if "DTEND" in props:
            e = _ics_dt(props["DTEND"][0])
            if e is not None:
                # All-day DTEND is exclusive.
                end = max(e[0] - datetime.timedelta(days=1), start)
        elif "DURATION" in props:
            dur = _ics_duration(props["DURATION"][0])
            if dur is not None:
                end = start + datetime.timedelta(days=max(0, dur.days - 1))
    else:
        start_at = "%sT%s" % (start.isoformat(), stime)
        tz = "UTC" if sutc else sparams.get("TZID", "")
        begin = datetime.datetime.combine(start, datetime.time(int(stime[:2]), int(stime[3:])))
        end_dt = None
        if "DTEND" in props:
            e = _ics_dt(props["DTEND"][0])
            if e is not None:
                et = e[1] or "00:00"
                end_dt = datetime.datetime.combine(e[0], datetime.time(int(et[:2]), int(et[3:])))
        elif "DURATION" in props:
            dur = _ics_duration(props["DURATION"][0])
            if dur is not None:
                end_dt = begin + dur
        if end_dt is not None and end_dt > begin:
            end_at = end_dt.strftime("%Y-%m-%dT%H:%M")
            last = end_dt.date()
            # An event ending exactly at midnight ends on the day before.
            if end_dt.time() == datetime.time(0, 0) and last > start:
                last -= datetime.timedelta(days=1)
            end = max(last, start)
    rrule = props.get("RRULE", ("", {}))[0].upper()
    repeat_days = _daily_count(rrule, start)
    if all_day and repeat_days > 1 and end == start:
        end = start + datetime.timedelta(days=repeat_days - 1)  # an all-day event repeated n days = n days
    status = props.get("STATUS", ("", {}))[0].strip().upper()
    cats = props.get("CATEGORIES", ("", {}))[0]
    return {
        "uid": props.get("UID", ("", {}))[0].strip(),
        "title": _unescape(props.get("SUMMARY", ("", {}))[0]) or "(no title)",
        "start": start.isoformat(),
        "end": end.isoformat(),
        "startAt": start_at,
        "endAt": end_at,
        "tz": tz,
        "repeatDays": repeat_days,
        "recurrence": "yearly" if "FREQ=YEARLY" in rrule else "none",
        "status": "cancelled" if status == "CANCELLED" else "planned",
        "notes": _unescape(props.get("DESCRIPTION", ("", {}))[0]),
        "categories": [c.strip() for c in _unescape(cats).split(",") if c.strip()],
    }


def stable_id(prefix: str, key: str) -> str:
    """Deterministic id from a key (ICS UID), so importing the same file twice finds duplicates."""
    h = 2166136261
    for ch in key.encode("utf-8"):
        h = ((h ^ ch) * 16777619) & 0xFFFFFFFF
    return "%s-%08x" % (prefix, h)


def zone(name: str) -> Optional[datetime.tzinfo]:
    """tzinfo for 'UTC' or an IANA name (needs Python 3.9+ zoneinfo); None if unknown."""
    if name == "UTC":
        return datetime.timezone.utc
    try:
        from zoneinfo import ZoneInfo  # type: ignore  # Python 3.9+
        return ZoneInfo(name)
    except Exception:
        return None


def event_times(item: Dict[str, Any], target: Optional[datetime.tzinfo] = None) -> Optional[Dict[str, str]]:
    """Times of a timed ICS item in the target zone (None means this computer's zone), as
    {start, end, startTime, endTime, timing}:
      - one day:                          timing ''           (a milestone with times)
      - one day repeated daily n days:    timing 'daily'      (same hours each day)
      - from one day to a later day:      timing 'continuous' (for example lunch to lunch)
    Returns None when it should be whole days (no times, or it ends exactly at midnight).
    Times in a zone Python cannot resolve (Outlook's Windows zone names, floating times) are taken
    as written, which is right when the calendar and the wheel are in the same place."""
    if not item.get("startAt") or not item.get("endAt"):
        return None
    a = datetime.datetime.strptime(item["startAt"], "%Y-%m-%dT%H:%M")
    b = datetime.datetime.strptime(item["endAt"], "%Y-%m-%dT%H:%M")
    src = zone(item["tz"]) if item.get("tz") else None
    if src is not None:
        a = a.replace(tzinfo=src).astimezone(target)
        b = b.replace(tzinfo=src).astimezone(target)
    out = {"start": a.date().isoformat(), "end": b.date().isoformat(),
           "startTime": a.strftime("%H:%M"), "endTime": b.strftime("%H:%M"), "timing": ""}
    if a.date() == b.date():
        if b.time() <= a.time():
            return None
        days = item.get("repeatDays", 0)
        if days > 1:
            out["end"] = (a.date() + datetime.timedelta(days=days - 1)).isoformat()
            out["timing"] = "daily"
        return out
    if b.time() == datetime.time(0, 0):
        return None
    out["timing"] = "continuous"
    return out


def ics_events_to_wheel_events(items: List[Dict[str, Any]], ring_id: str,
                               target: Optional[datetime.tzinfo] = None) -> List[Dict[str, Any]]:
    out = []
    for it in items:
        times = event_times(it, target)
        if times:
            it = dict(it, start=times["start"], end=times["end"])
        key = it["uid"] or (it["title"] + "|" + it["start"])
        own = key[:-len("@yearwheel")] if key.endswith("@yearwheel") else ""
        # Events exported by the app keep their original id, so a round trip finds duplicates.
        eid = own if re.match(r"^[a-z0-9][a-z0-9-]*$", own) else stable_id("ics", key)
        ev = {"id": eid, "ringId": ring_id, "title": it["title"],
              "kind": "span" if it["end"] != it["start"] else "milestone", "start": it["start"]}
        if ev["kind"] == "span":
            ev["end"] = it["end"]
        if times:
            ev["startTime"], ev["endTime"] = times["startTime"], times["endTime"]
            if ev["kind"] == "span":
                ev["timing"] = times["timing"]
        ev["status"] = it["status"]
        ev["recurrence"] = it["recurrence"]
        if it["notes"]:
            ev["notes"] = it["notes"]
        out.append(ev)
    return out
