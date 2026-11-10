# Year Wheel. Copyright (c) 2026 Robert Tomkowski <rtom@kth.se>
# MIT License (see the LICENSE file). Developed with the assistance of Claude Code (Anthropic).

"""ICS parsing and the ics_to_wheel.py command line tool."""

import datetime
import json
import os

import ics_to_wheel
import wheellib
from conftest import FIXTURES, fixture_text


def by_title(items):
    return {i["title"]: i for i in items}


def test_outlook_export():
    items = by_title(wheellib.parse_ics(fixture_text("outlook.ics")))
    assert len(items) == 3
    m = items["Steering group meeting, project A"]  # escaped comma, LANGUAGE parameter
    assert (m["start"], m["end"]) == ("2027-02-03", "2027-02-03")  # TZID date-time: date only
    assert m["notes"].startswith("Agenda: budget; milestones\nRoom: M2")  # escapes and newline
    assert m["notes"].endswith("that Outlook folds onto the next line")  # folded line joined
    assert "Reminder" not in m["notes"]  # VALARM description ignored
    assert (items["Lab week"]["start"], items["Lab week"]["end"]) == ("2027-03-15", "2027-03-19")  # exclusive DTEND
    assert items["Cancelled: Workshop"]["status"] == "cancelled"


def test_google_export():
    items = by_title(wheellib.parse_ics(fixture_text("google.ics")))
    assert "Broken entry without start" not in items
    assert items["Conference abstract deadline"]["end"] == "2027-01-20"  # one all-day day = milestone
    assert items["Conference abstract deadline"]["categories"] == ["Research"]
    conf = items["Main conference"]
    assert (conf["start"], conf["end"], conf["recurrence"]) == ("2027-06-07", "2027-06-11", "yearly")
    assert items["Kick-off"]["start"] == items["Kick-off"]["end"] == "2027-09-01"  # UTC time
    assert items["Overnight run"]["end"] == "2027-10-12"  # timed event ending at midnight
    assert items["Review days"]["end"] == "2027-12-03"  # DURATION:P3D on an all-day event


def test_raw_times_are_reported():
    items = by_title(wheellib.parse_ics(fixture_text("outlook.ics")) + wheellib.parse_ics(fixture_text("google.ics")))
    m = items["Steering group meeting, project A"]
    assert (m["startAt"], m["endAt"], m["tz"]) == ("2027-02-03T13:00", "2027-02-03T15:00", "W. Europe Standard Time")
    k = items["Kick-off"]
    assert (k["startAt"], k["endAt"], k["tz"]) == ("2027-09-01T08:00", "2027-09-01T10:00", "UTC")
    assert items["Lab week"]["startAt"] == items["Lab week"]["tz"] == ""  # all-day: no times


def test_timed_events_keep_their_times():
    cest = datetime.timezone(datetime.timedelta(hours=2))  # Stockholm in summer
    items = wheellib.parse_ics(fixture_text("outlook.ics")) + wheellib.parse_ics(fixture_text("google.ics"))
    evs = {e["title"]: e for e in wheellib.ics_events_to_wheel_events(items, "r", cest)}
    # Windows zone name (cannot be resolved): wall time kept as written.
    assert (evs["Steering group meeting, project A"]["startTime"], evs["Steering group meeting, project A"]["endTime"]) == ("13:00", "15:00")
    # UTC converted to the wheel's zone.
    assert (evs["Kick-off"]["start"], evs["Kick-off"]["startTime"], evs["Kick-off"]["endTime"]) == ("2027-09-01", "10:00", "12:00")
    # Timed over several days: a continuous span with its times (00:00 on 12 Oct to 02:00 on 13 Oct locally).
    run = evs["Overnight run"]
    assert (run["kind"], run["start"], run["end"], run["startTime"], run["endTime"], run["timing"]) == \
        ("span", "2027-10-12", "2027-10-13", "00:00", "02:00", "continuous")
    assert "startTime" not in evs["Lab week"]  # all-day: no times
    for e in evs.values():
        assert ("startTime" in e) == ("endTime" in e)
        assert ("timing" in e) == (e["kind"] == "span" and "startTime" in e)


def item(start_at, end_at, tz="UTC", repeat=0):
    return {"uid": "x", "title": "T", "start": start_at[:10], "end": end_at[:10], "startAt": start_at, "endAt": end_at,
            "tz": tz, "repeatDays": repeat, "recurrence": "none", "status": "planned", "notes": "", "categories": []}


def test_event_crossing_midnight_locally_becomes_continuous():
    plus1 = datetime.timezone(datetime.timedelta(hours=1))
    got = wheellib.event_times(item("2027-03-01T22:30", "2027-03-01T23:30"), plus1)  # 23:30 to 00:30 locally
    assert got == {"start": "2027-03-01", "end": "2027-03-02", "startTime": "23:30", "endTime": "00:30", "timing": "continuous"}
    got = wheellib.event_times(item("2027-03-01T22:30", "2027-03-01T23:30"), datetime.timezone.utc)
    assert (got["start"], got["startTime"], got["endTime"], got["timing"]) == ("2027-03-01", "22:30", "23:30", "")


def test_lunch_to_lunch_and_midnight_end():
    utc = datetime.timezone.utc
    got = wheellib.event_times(item("2027-05-10T12:00", "2027-05-12T12:00"), utc)
    assert got == {"start": "2027-05-10", "end": "2027-05-12", "startTime": "12:00", "endTime": "12:00", "timing": "continuous"}
    assert wheellib.event_times(item("2027-05-10T09:00", "2027-05-12T00:00"), utc) is None  # ends at midnight: whole days


def test_daily_repeat_becomes_span_with_daily_hours():
    ics = "\n".join(["BEGIN:VCALENDAR", "BEGIN:VEVENT", "UID:w1", "SUMMARY:Workshop",
                     "DTSTART:20270302T080000Z", "DTEND:20270302T150000Z", "RRULE:FREQ=DAILY;COUNT=3", "END:VEVENT",
                     "BEGIN:VEVENT", "UID:w2", "SUMMARY:Until", "DTSTART;TZID=Europe/Stockholm:20270302T090000",
                     "DTEND;TZID=Europe/Stockholm:20270302T160000", "RRULE:FREQ=DAILY;UNTIL=20270305T235959Z", "END:VEVENT",
                     "BEGIN:VEVENT", "UID:w3", "SUMMARY:Every other day", "DTSTART:20270302T080000Z",
                     "DTEND:20270302T090000Z", "RRULE:FREQ=DAILY;INTERVAL=2;COUNT=3", "END:VEVENT",
                     "BEGIN:VEVENT", "UID:w4", "SUMMARY:All-day daily", "DTSTART;VALUE=DATE:20270601",
                     "DTEND;VALUE=DATE:20270602", "RRULE:FREQ=DAILY;COUNT=3", "END:VEVENT", "END:VCALENDAR", ""])
    items = by_title(wheellib.parse_ics(ics))
    assert [items[k]["repeatDays"] for k in ("Workshop", "Until", "Every other day")] == [3, 4, 0]
    assert (items["All-day daily"]["start"], items["All-day daily"]["end"]) == ("2027-06-01", "2027-06-03")
    cet = datetime.timezone(datetime.timedelta(hours=1))
    evs = {e["title"]: e for e in wheellib.ics_events_to_wheel_events(list(items.values()), "r", cet)}
    w = evs["Workshop"]
    assert (w["kind"], w["start"], w["end"], w["startTime"], w["endTime"], w["timing"]) == \
        ("span", "2027-03-02", "2027-03-04", "09:00", "16:00", "daily")
    assert (evs["Until"]["start"], evs["Until"]["end"], evs["Until"]["timing"]) == ("2027-03-02", "2027-03-05", "daily")
    assert evs["Every other day"]["kind"] == "milestone"  # an interval is not supported: just the first day
    assert evs["All-day daily"]["kind"] == "span" and "timing" not in evs["All-day daily"]


def test_cli_keeps_times_and_validates(tmp_path):
    out = tmp_path / "o.json"
    assert ics_to_wheel.main([os.path.join(FIXTURES, "outlook.ics"), "--ring", "Meetings", "-o", str(out)]) == 0
    w = wheellib.load_wheel(str(out))
    assert wheellib.full_check(w) == []
    steering = next(e for e in w["events"] if e["title"].startswith("Steering"))
    assert (steering["startTime"], steering["endTime"]) == ("13:00", "15:00")
    created = next(c for c in w["changelog"] if c["eventId"] == steering["id"])
    assert created["after"]["startTime"] == "13:00"


def test_events_become_spans_and_milestones():
    evs = wheellib.ics_events_to_wheel_events(wheellib.parse_ics(fixture_text("google.ics")), "research")
    kinds = {e["title"]: e["kind"] for e in evs}
    assert kinds["Main conference"] == "span"
    assert kinds["Kick-off"] == "milestone"
    assert all("end" in e for e in evs if e["kind"] == "span")
    assert all("end" not in e for e in evs if e["kind"] == "milestone")
    assert len({e["id"] for e in evs}) == len(evs)


def test_ids_are_stable_and_app_exports_keep_their_id():
    a = wheellib.ics_events_to_wheel_events(wheellib.parse_ics(fixture_text("google.ics")), "r")
    b = wheellib.ics_events_to_wheel_events(wheellib.parse_ics(fixture_text("google.ics")), "r")
    assert [e["id"] for e in a] == [e["id"] for e in b]
    item = {"uid": "call-eu@yearwheel", "title": "x", "start": "2027-01-01", "end": "2027-01-01",
            "recurrence": "none", "status": "planned", "notes": "", "categories": []}
    assert wheellib.ics_events_to_wheel_events([item], "r")[0]["id"] == "call-eu"
    assert wheellib.stable_id("ics", "x").startswith("ics-") and len(wheellib.stable_id("ics", "x")) == 12


def test_cli_new_wheel(tmp_path):
    out = tmp_path / "g.json"
    assert ics_to_wheel.main([os.path.join(FIXTURES, "google.ics"), "--ring", "Research", "-o", str(out)]) == 0
    w = wheellib.load_wheel(str(out))
    assert wheellib.full_check(w) == []
    assert w["yearStart"] == "2027-01-01"
    assert [r["name"] for r in w["rings"]] == ["Research"]
    assert len(w["events"]) == 5
    assert [c["action"] for c in w["changelog"]] == ["created"] * 5


def test_cli_merge_creates_ring_and_skips_duplicates(tmp_path, research_wheel):
    path = tmp_path / "wheel.json"
    wheellib.dump_wheel(research_wheel, str(path))
    n0 = len(research_wheel["events"])
    assert ics_to_wheel.main([os.path.join(FIXTURES, "outlook.ics"), "--ring", "Möten och lab", "--merge", str(path)]) == 0
    assert ics_to_wheel.main([os.path.join(FIXTURES, "outlook.ics"), "--ring", "möten och lab", "--merge", str(path)]) == 0
    w = wheellib.load_wheel(str(path))
    assert wheellib.full_check(w) == []
    assert len(w["events"]) == n0 + 3
    assert w["rings"][-1]["id"] == "moten-och-lab"
    assert len(w["rings"]) == 5


def test_cli_date_filter(tmp_path):
    out = tmp_path / "f.json"
    ics_to_wheel.main([os.path.join(FIXTURES, "google.ics"), "--ring", "R", "-o", str(out),
                       "--from", "2027-06-01", "--to", "2027-09-30"])
    titles = sorted(e["title"] for e in json.loads(out.read_text("utf-8"))["events"])
    assert titles == ["Kick-off", "Main conference"]


def test_cli_refuses_seventh_ring(tmp_path, research_wheel):
    for i in range(2):
        research_wheel["rings"].append({"id": "x%d" % i, "name": "X%d" % i, "color": "#000000", "order": 4 + i})
    path = tmp_path / "full.json"
    wheellib.dump_wheel(research_wheel, str(path))
    try:
        ics_to_wheel.main([os.path.join(FIXTURES, "google.ics"), "--ring", "New", "--merge", str(path)])
        raised = False
    except SystemExit:
        raised = True
    assert raised
