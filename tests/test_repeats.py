# Year Wheel. Copyright (c) 2026 Robert Tomkowski <rtom@kth.se>
# MIT License (see the LICENSE file). Developed with the assistance of Claude Code (Anthropic).

"""Weekly and monthly repeats: the date rules (browser and Python agree), single changed meetings,
ICS export and import (RRULE, VTIMEZONE, EXDATE, RECURRENCE-ID), CSV values and the rule checks."""

import copy

import pytest

import wheellib
from test_js_parsers import NODE, run_js

needs_node = pytest.mark.skipif(NODE is None, reason="Node.js not installed")

CASES = [
    ({"start": "2027-01-05", "kind": "milestone", "recurrence": "weekly", "interval": 2}, "2027-02-01", "2027-04-30"),
    ({"start": "2027-01-05", "kind": "milestone", "recurrence": "weekly", "until": "2027-03-01"}, "2026-01-01", "2027-12-31"),
    ({"start": "2027-01-31", "kind": "milestone", "recurrence": "monthly"}, "2027-01-01", "2027-12-31"),
    ({"start": "2026-09-08", "kind": "milestone", "recurrence": "monthly", "monthlyBy": "weekday"}, "2026-09-01", "2027-06-30"),
    ({"start": "2027-01-29", "kind": "milestone", "recurrence": "monthly", "monthlyBy": "weekday"}, "2027-01-01", "2027-12-31"),
    ({"start": "2026-11-15", "kind": "milestone", "recurrence": "monthly", "interval": 3}, "2027-05-01", "2028-06-01"),
    ({"start": "2027-01-12", "end": "2027-01-13", "kind": "span", "recurrence": "monthly", "monthlyBy": "weekday"},
     "2027-01-01", "2027-04-30"),
    ({"start": "2027-01-12", "kind": "milestone", "recurrence": "yearly"}, "2027-01-01", "2027-12-31"),
]


def starts(i):
    ev, a, b = CASES[i]
    return wheellib.repeat_starts(ev, a, b)


def test_weekly_every_second_week_and_until():
    assert starts(0) == ["2027-02-02", "2027-02-16", "2027-03-02", "2027-03-16", "2027-03-30", "2027-04-13", "2027-04-27"]
    assert starts(1)[-1] == "2027-02-23" and len(starts(1)) == 8  # until is a Monday: last Tuesday before it


def test_monthly_on_the_31st_skips_short_months():
    assert starts(2) == ["2027-01-31", "2027-03-31", "2027-05-31", "2027-07-31", "2027-08-31", "2027-10-31", "2027-12-31"]


def test_monthly_on_a_weekday_of_the_month():
    second_tuesdays = starts(3)
    assert second_tuesdays[:5] == ["2026-09-08", "2026-10-13", "2026-11-10", "2026-12-08", "2027-01-12"]
    assert len(second_tuesdays) == 10
    last_fridays = starts(4)
    assert last_fridays[:4] == ["2027-01-29", "2027-02-26", "2027-03-26", "2027-04-30"]


def test_every_three_months_across_years_and_spans_keep_the_date():
    assert starts(5) == ["2027-05-15", "2027-08-15", "2027-11-15", "2028-02-15", "2028-05-15"]
    assert starts(6) == ["2027-01-12", "2027-02-12", "2027-03-12", "2027-04-12"]  # weekday rule is for milestones
    assert starts(7) == []


@needs_node
def test_browser_and_python_give_the_same_dates():
    js = run_js("input.map(c => repeatStarts(c[0], c[1], c[2]))", CASES)
    assert js == [wheellib.repeat_starts(*c) for c in CASES]


MEETING = {"id": "gm", "ringId": "r", "title": "Research group meeting", "kind": "milestone", "start": "2026-09-08",
           "startTime": "10:00", "endTime": "11:00", "status": "planned", "recurrence": "monthly", "monthlyBy": "weekday",
           "until": "2027-06-30", "exceptions": [
               {"date": "2026-10-13", "status": "done"},
               {"date": "2026-12-08", "status": "cancelled"},
               {"date": "2027-03-09", "status": "moved", "start": "2027-03-16"}]}


def wheel(*events):
    return {"title": "T", "rings": [{"id": "r", "name": "Team"}], "events": list(events)}


@needs_node
def test_ics_export_keeps_local_time_and_single_changes():
    ics = run_js("wheelToIcs(input, '20260101T000000Z', 'Europe/Stockholm')", wheel(MEETING))
    lines = ics.split("\r\n")
    for want in ["BEGIN:VTIMEZONE", "TZID:Europe/Stockholm",
                 "DTSTART:19700329T020000", "TZOFFSETFROM:+0100", "TZOFFSETTO:+0200", "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU",
                 "DTSTART:19701025T030000", "RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU",
                 "DTSTART;TZID=Europe/Stockholm:20260908T100000", "DTEND;TZID=Europe/Stockholm:20260908T110000",
                 "RRULE:FREQ=MONTHLY;BYDAY=2TU;UNTIL=20270630T215900Z",
                 "EXDATE;TZID=Europe/Stockholm:20261208T100000",
                 "RECURRENCE-ID;TZID=Europe/Stockholm:20270309T100000", "DTSTART;TZID=Europe/Stockholm:20270316T100000"]:
        assert want in lines, want
    assert lines.index("END:VTIMEZONE") < lines.index("BEGIN:VEVENT")
    assert lines.count("UID:gm@yearwheel") == 2  # the series and the moved meeting

    items = wheellib.parse_ics(ics)
    assert run_js("parseIcs(input)", ics) == items
    assert len(items) == 1
    it = items[0]
    assert (it["recurrence"], it["interval"], it["monthlyBy"], it["until"]) == ("monthly", 1, "weekday", "2027-06-30")
    assert it["exceptions"] == [{"date": "2026-12-08", "status": "cancelled"},
                                {"date": "2027-03-09", "status": "moved", "start": "2027-03-16", "end": "2027-03-16"}]
    back = wheellib.ics_events_to_wheel_events(items, "r")[0]
    assert back["id"] == "gm"
    assert back["exceptions"] == [{"date": "2026-12-08", "status": "cancelled"},
                                  {"date": "2027-03-09", "status": "moved", "start": "2027-03-16"}]
    assert list(back)[list(back).index("recurrence"):list(back).index("exceptions") + 1] == \
        ["recurrence", "monthlyBy", "until", "exceptions"]


@needs_node
def test_ics_vtimezone_for_other_rules():
    ics = run_js("wheelToIcs(input, 'S', 'America/New_York')", wheel(dict(MEETING, exceptions=[])))
    lines = ics.split("\r\n")
    assert "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU" in lines and "DTSTART:19700308T020000" in lines
    assert "RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU" in lines and "DTSTART:19701101T020000" in lines
    utc = run_js("wheelToIcs(input, 'S', 'UTC')", wheel(dict(MEETING, exceptions=[])))
    assert "BEGIN:VTIMEZONE" not in utc and "DTSTART:20260908T100000Z" in utc.split("\r\n")


@needs_node
def test_ics_export_of_whole_day_and_daily_span_repeats():
    weekly = {"id": "wk", "ringId": "r", "title": "Lab cleaning", "kind": "milestone", "start": "2027-01-05",
              "status": "planned", "recurrence": "weekly", "interval": 2, "until": "2027-03-01",
              "exceptions": [{"date": "2027-01-19", "status": "cancelled"}]}
    course = {"id": "cw", "ringId": "r", "title": "Course days", "kind": "span", "start": "2027-01-11", "end": "2027-01-12",
              "startTime": "09:00", "endTime": "16:00", "timing": "daily", "status": "planned", "recurrence": "monthly",
              "exceptions": [{"date": "2027-02-11", "status": "cancelled"}]}
    lines = run_js("wheelToIcs(input, 'S', 'Europe/Stockholm')", wheel(weekly, course)).split("\r\n")
    for want in ["DTSTART;VALUE=DATE:20270105", "RRULE:FREQ=WEEKLY;INTERVAL=2;UNTIL=20270301", "EXDATE;VALUE=DATE:20270119",
                 "UID:cw-d1@yearwheel", "UID:cw-d2@yearwheel", "DTSTART;TZID=Europe/Stockholm:20270112T090000",
                 "EXDATE;TZID=Europe/Stockholm:20270211T090000", "EXDATE;TZID=Europe/Stockholm:20270212T090000"]:
        assert want in lines, want
    assert lines.count("RRULE:FREQ=MONTHLY") == 2


ICS = "\r\n".join([
    "BEGIN:VCALENDAR", "VERSION:2.0",
    "BEGIN:VEVENT", "UID:abc", "SUMMARY:Lab meeting", "DTSTART;VALUE=DATE:20270105", "DTEND;VALUE=DATE:20270106",
    "RRULE:FREQ=WEEKLY;INTERVAL=2;COUNT=3", "EXDATE;VALUE=DATE:20270119,20270202", "END:VEVENT",
    "BEGIN:VEVENT", "UID:def", "SUMMARY:Board", "DTSTART;TZID=Europe/Stockholm:20270104T130000",
    "DTEND;TZID=Europe/Stockholm:20270104T140000", "RRULE:FREQ=MONTHLY;BYDAY=1MO", "END:VEVENT",
    "BEGIN:VEVENT", "UID:def", "SUMMARY:Board", "RECURRENCE-ID;TZID=Europe/Stockholm:20270201T130000",
    "DTSTART;TZID=Europe/Stockholm:20270201T150000", "DTEND;TZID=Europe/Stockholm:20270201T160000", "END:VEVENT",
    "BEGIN:VEVENT", "UID:def", "SUMMARY:Board", "RECURRENCE-ID;TZID=Europe/Stockholm:20270301T130000",
    "DTSTART;TZID=Europe/Stockholm:20270308T130000", "DTEND;TZID=Europe/Stockholm:20270308T140000", "END:VEVENT",
    "END:VCALENDAR", ""])


def test_ics_import_of_count_exdate_and_recurrence_id():
    a, b = wheellib.parse_ics(ICS)
    assert (a["recurrence"], a["interval"], a["until"]) == ("weekly", 2, "2027-02-02")
    assert a["exceptions"] == [{"date": "2027-01-19", "status": "cancelled"}, {"date": "2027-02-02", "status": "cancelled"}]
    assert (b["recurrence"], b["monthlyBy"], b["until"]) == ("monthly", "weekday", "")
    # Only a new time on the same day is not a moved date; a new day is.
    assert b["exceptions"] == [{"date": "2027-03-01", "status": "moved", "start": "2027-03-08", "end": "2027-03-08"}]
    evs = wheellib.ics_events_to_wheel_events([a, b], "r")
    w = {"schemaVersion": 1, "id": "x", "title": "x", "yearStart": "2027-01-01", "settings": {},
         "rings": [{"id": "r", "name": "R", "color": "#000000", "order": 0}], "events": evs, "reviews": [], "changelog": []}
    assert wheellib.full_check(w) == []


@needs_node
def test_ics_import_parity():
    assert run_js("parseIcs(input)", ICS) == wheellib.parse_ics(ICS)


@needs_node
def test_csv_repeat_values():
    values = ["weekly", "Every 2 weeks", "varannan vecka", "monthly", "every 3 months", "var 3:e månad",
              "monthly by weekday", "every 2 months by weekday", "varje månad på veckodag", "yearly", "", "weekly by weekday",
              "every 0 weeks", "sometimes"]
    got = run_js("input.map(csvRepeat)", values)
    rec = lambda r, n=1, by="": {"recurrence": r, "interval": n, "monthlyBy": by}  # noqa: E731
    assert got == [rec("weekly"), rec("weekly", 2), rec("weekly", 2), rec("monthly"), rec("monthly", 3), rec("monthly", 3),
                   rec("monthly", 1, "weekday"), rec("monthly", 2, "weekday"), rec("monthly", 1, "weekday"), rec("yearly"),
                   rec("none"), None, None, None]


@needs_node
def test_csv_template_has_meetings_and_until_is_checked():
    rows = {i["title"]: i for i in run_js("csvToItems(csvTemplate()).items", None)}
    gm = rows["Research group meeting"]
    assert (gm["recurrence"], gm["monthlyBy"], gm["until"]) == ("monthly", "weekday", "2027-06-30")
    assert (rows["Department meeting"]["recurrence"], rows["Department meeting"]["interval"]) == ("monthly", 2)
    res = run_js("csvToItems(input)", "title;start;repeats;until\nA;2027-01-05;weekly;2026-12-01\nB;2027-01-05;;2027-02-01\n")
    assert res["warnings"] == [{"line": 2, "msg": "until"}]
    assert [i["until"] for i in res["items"]] == ["", ""]  # until only applies to weekly and monthly


def test_rule_checks():
    good = {"id": "gm", "ringId": "r", "kind": "milestone", "start": "2026-09-08", "recurrence": "monthly",
            "monthlyBy": "weekday", "exceptions": [{"date": "2026-10-13", "status": "done"}]}
    assert wheellib._repeat_rules(good) == []
    bad = copy.deepcopy(good)
    bad["exceptions"].append({"date": "2026-10-14", "status": "cancelled"})
    assert wheellib._repeat_rules(bad) == ["event gm: exception 2026-10-14 is not one of its dates"]
    assert wheellib._repeat_rules(dict(good, until="2026-01-01"))[0] == "event gm: until is before start"
    assert wheellib._repeat_rules({"id": "y", "recurrence": "yearly", "interval": 2}) != []
    assert wheellib.validate({"x": 1}) != []  # sanity
