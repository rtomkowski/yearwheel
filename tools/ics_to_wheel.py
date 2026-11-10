# Year Wheel. Copyright (c) 2026 Robert Tomkowski <rtom@kth.se>
# MIT License (see the LICENSE file). Developed with the assistance of Claude Code (Anthropic).

"""Convert an iCalendar (.ics) export from Outlook or Google Calendar into a Year Wheel file.

Examples:
  python tools/ics_to_wheel.py deadlines.ics --ring "Research"
      writes deadlines.json next to the input: a new wheel with one ring "Research"
  python tools/ics_to_wheel.py deadlines.ics --ring "Research" --merge group-2027.json
      adds the events to an existing wheel (ring is created if needed, duplicates skipped)
  python tools/ics_to_wheel.py deadlines.ics --ring Lab --from 2027-01-01 --to 2027-12-31 -o lab.json

Single-day events with a time keep their times (converted to --tz, the wheel's time zone, or this
computer's zone). Other events become whole-day milestones or spans. The result is validated
before it is written.
"""

import argparse
import datetime
import os
import re
import sys
import unicodedata
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wheellib import (dump_wheel, full_check, ics_events_to_wheel_events,  # noqa: E402
                      load_wheel, parse_ics, quarter_start_month, zone)

PALETTE = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#D55E00"]


def ring_slug(name: str, taken: List[str]) -> str:
    """ASCII id from a name: 'Lärande & labb' -> 'larande-labb'."""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    base = "-".join(re.findall(r"[a-z0-9]+", ascii_name)) or "ring"
    rid, n = base, 2
    while rid in taken:
        rid = "%s-%d" % (base, n)
        n += 1
    return rid


def new_wheel(title: str, year_start: str) -> Dict[str, Any]:
    return {
        "schemaVersion": 1, "id": ring_slug(title, []), "title": title, "yearStart": year_start, "years": 1,
        "settings": {"language": "en", "weekTicks": False, "showPeriods": False, "showQuarters": True,
                     "quarterStartMonth": quarter_start_month(year_start), "periods": []},
        "rings": [], "events": [], "reviews": [], "changelog": [],
    }


def convert(ics_text: str, ring_name: str, wheel: Dict[str, Any], date_from: str = "", date_to: str = "",
            target=None) -> Dict[str, int]:
    """Add the calendar's events to `wheel` in place. Returns counts.

    target: tzinfo that event times are converted to (None = this computer's zone)."""
    items = parse_ics(ics_text)
    if date_from:
        items = [i for i in items if i["end"] >= date_from]
    if date_to:
        items = [i for i in items if i["start"] <= date_to]
    ring = next((r for r in wheel["rings"] if r["name"].lower() == ring_name.lower()), None)
    if ring is None:
        if len(wheel["rings"]) >= 6:
            raise SystemExit("The wheel already has 6 rings. Use --ring with an existing ring name.")
        ring = {"id": ring_slug(ring_name, [r["id"] for r in wheel["rings"]]), "name": ring_name,
                "color": PALETTE[len(wheel["rings"]) % len(PALETTE)], "order": len(wheel["rings"])}
        wheel["rings"].append(ring)
    existing = {e["id"] for e in wheel["events"]}
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    added = skipped = 0
    for ev in ics_events_to_wheel_events(items, ring["id"], target):
        if ev["id"] in existing:
            skipped += 1
            continue
        existing.add(ev["id"])
        wheel["events"].append(ev)
        after = {k: ev[k] for k in ("start", "end", "startTime", "endTime", "timing") if k in ev}
        wheel["changelog"].append({"timestamp": now, "eventId": ev["id"], "title": ev["title"],
                                   "action": "created", "after": after})
        added += 1
    return {"found": len(items), "added": added, "skipped": skipped}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ics", help="input .ics file")
    ap.add_argument("--ring", required=True, help="ring name for the imported events")
    ap.add_argument("-o", "--output", help="output .json (default: input name with .json)")
    ap.add_argument("--merge", help="existing wheel .json to add the events to (written back unless -o is given)")
    ap.add_argument("--title", help="title for a new wheel (default: from the file name)")
    ap.add_argument("--year-start", help="first day of a new wheel, YYYY-MM-DD (default: 1 January of the first event)")
    ap.add_argument("--from", dest="date_from", default="", help="only events ending on or after this date")
    ap.add_argument("--to", dest="date_to", default="", help="only events starting on or before this date")
    ap.add_argument("--tz", default="", help="time zone for event times, e.g. Europe/Stockholm "
                    "(default: the wheel's setting, else this computer's zone; needs Python 3.9+)")
    args = ap.parse_args(argv)

    with open(args.ics, encoding="utf-8-sig") as f:
        text = f.read()
    if args.merge:
        wheel = load_wheel(args.merge)
        out = args.output or args.merge
    else:
        items = parse_ics(text)
        first = min((i["start"] for i in items), default=datetime.date.today().isoformat())
        year_start = args.year_start or (first[:4] + "-01-01")
        title = args.title or os.path.splitext(os.path.basename(args.ics))[0].replace("_", " ").replace("-", " ").strip() or "Imported calendar"
        wheel = new_wheel(title, year_start)
        out = args.output or os.path.splitext(args.ics)[0] + ".json"

    # Single-day timed events keep their times, converted to the wheel's time zone.
    tz_name = args.tz or wheel["settings"].get("timeZone", "")
    target = zone(tz_name) if tz_name else None
    if tz_name and target is None:
        print("Note: time zone %r needs Python 3.9 or later; using this computer's time zone." % tz_name)
    elif args.tz:
        wheel["settings"]["timeZone"] = args.tz
    counts = convert(text, args.ring, wheel, args.date_from, args.date_to, target)
    errors = full_check(wheel)
    if errors:
        print("The result is not a valid wheel:")
        for e in errors:
            print("  - " + e)
        return 1
    dump_wheel(wheel, out)
    print("%d events found, %d added, %d already present. Wrote %s" % (counts["found"], counts["added"], counts["skipped"], out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
