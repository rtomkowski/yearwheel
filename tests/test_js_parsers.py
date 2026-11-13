# Year Wheel. Copyright (c) 2026 Robert Tomkowski <rtom@kth.se>
# MIT License (see the LICENSE file). Developed with the assistance of Claude Code (Anthropic).

"""Run the browser's parsers (the PARSERS block in yearwheel.html) in Node and compare with Python.

Skipped when Node is not installed. Covers: ICS parsing parity with wheellib.parse_ics, stable ids,
CSV import rules, and ICS export round trips through both parsers.
"""

import json
import os
import re
import shutil
import subprocess

import pytest

import wheellib
from conftest import HTML_PATH, fixture_text

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="Node.js not installed")


def run_js(expr, payload):
    with open(HTML_PATH, encoding="utf-8") as f:
        html = f.read()
    block = re.search(r"/\*PARSERS-BEGIN\*/(.*?)/\*PARSERS-END\*/", html, re.S).group(1)
    script = block + "\nconst input = JSON.parse(require('fs').readFileSync(0, 'utf8'));\n" + \
        "process.stdout.write(JSON.stringify(" + expr + "));\n"
    res = subprocess.run([NODE, "-e", script], input=json.dumps(payload), capture_output=True, text=True, timeout=30)
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


@pytest.mark.parametrize("name", ["outlook.ics", "google.ics"])
def test_ics_parity_with_python(name):
    text = fixture_text(name)
    assert run_js("parseIcs(input)", text) == wheellib.parse_ics(text)


def test_stable_id_parity():
    keys = ["abc123@google.com", "Lab week|2027-03-15", "Möte på ÅÄÖ", ""]
    js = run_js("input.map(k => stableId('ics', k))", keys)
    assert js == [wheellib.stable_id("ics", k) for k in keys]


def test_csv_import_rules():
    res = run_js("csvToItems(input)", fixture_text("events.csv"))
    items = {i["title"]: i for i in res["items"]}
    assert set(items) == {"Budget draft", "Board meeting; spring", "Calibration of CMM", "Unknown status"}
    assert items["Budget draft"]["end"] == "2027-03-15"
    assert items["Board meeting; spring"]["end"] == "2027-04-12"  # quoted semicolon, no end = milestone
    assert items["Board meeting; spring"]["status"] == "planned"
    assert items["Calibration of CMM"]["status"] == "done"
    assert items["Unknown status"]["status"] == "planned"
    assert {(w["line"], w["msg"]) for w in res["warnings"]} == {(5, "start"), (6, "status")}


def test_csv_comma_delimiter_and_quotes():
    text = 'Title,Start,End,Ring\r\n"Say ""hi"", team",2027/01/05,2027-01-09,Research\r\n'
    res = run_js("csvToItems(input)", text)
    assert res["items"][0]["title"] == 'Say "hi", team'
    assert res["items"][0]["start"] == "2027-01-05"
    assert res["items"][0]["ring"] == "Research"


def test_csv_needs_header():
    assert run_js("csvToItems(input).warnings", "2027-01-01;x\n") == [{"line": 1, "msg": "header"}]


def test_timed_export_uses_utc_across_daylight_saving():
    w = {"title": "T", "rings": [{"id": "r", "name": "Team"}], "events": [
        {"id": "winter", "ringId": "r", "title": "Team day", "kind": "milestone", "start": "2027-02-03",
         "startTime": "09:00", "endTime": "17:00", "status": "planned", "recurrence": "none"},
        {"id": "summer", "ringId": "r", "title": "Team day", "kind": "milestone", "start": "2027-08-26",
         "startTime": "09:00", "endTime": "17:00", "status": "planned", "recurrence": "yearly"},
        {"id": "whole", "ringId": "r", "title": "Deadline", "kind": "milestone", "start": "2027-03-01",
         "status": "planned", "recurrence": "none"}]}
    ics = run_js("wheelToIcs(input, '20270101T000000Z', 'Europe/Stockholm')", w)
    lines = [l for l in ics.split("\r\n") if l.startswith(("DTSTART", "DTEND"))]
    assert lines == ["DTSTART:20270203T080000Z", "DTEND:20270203T160000Z",   # CET, UTC+1
                     "DTSTART:20270826T070000Z", "DTEND:20270826T150000Z",   # CEST, UTC+2
                     "DTSTART;VALUE=DATE:20270301", "DTEND;VALUE=DATE:20270302"]
    # A colleague in New York gets the same moment in their own time.
    ny = run_js("parseIcs(input).map(i => icsLocalTimes(i, 'America/New_York'))", ics)
    assert ny[:2] == [{"start": "2027-02-03", "end": "2027-02-03", "startTime": "03:00", "endTime": "11:00", "timing": ""},
                      {"start": "2027-08-26", "end": "2027-08-26", "startTime": "03:00", "endTime": "11:00", "timing": ""}]
    assert ny[2] is None
    # Python reads the export back to the same times.
    cet = __import__("datetime").timezone(__import__("datetime").timedelta(hours=1))
    got = wheellib.event_times(wheellib.parse_ics(ics)[0], cet)
    assert (got["start"], got["startTime"], got["endTime"], got["timing"]) == ("2027-02-03", "09:00", "17:00", "")


def span_wheel(**extra):
    ev = {"id": "ws", "ringId": "r", "title": "Workshop", "kind": "span", "start": "2027-03-02", "end": "2027-03-04",
          "startTime": "09:00", "endTime": "16:00", "timing": "daily", "status": "planned", "recurrence": "none"}
    ev.update(extra)
    return {"title": "T", "rings": [{"id": "r", "name": "Team"}], "events": [ev]}


def dates(ics):
    return [l for l in ics.split("\r\n") if l.startswith(("UID", "DTSTART", "DTEND", "RRULE"))]


def test_export_daily_span_as_daily_repeat():
    ics = run_js("wheelToIcs(input, 'S', 'Europe/Stockholm')", span_wheel())
    assert dates(ics) == ["UID:ws@yearwheel", "DTSTART:20270302T080000Z", "DTEND:20270302T150000Z", "RRULE:FREQ=DAILY;COUNT=3"]
    # Both parsers read it back as the same daily span.
    for times in (run_js("parseIcs(input).map(i => icsLocalTimes(i, 'Europe/Stockholm'))", ics)[0],
                  wheellib.event_times(wheellib.parse_ics(ics)[0], __import__("datetime").timezone(__import__("datetime").timedelta(hours=1)))):
        assert times == {"start": "2027-03-02", "end": "2027-03-04", "startTime": "09:00", "endTime": "16:00", "timing": "daily"}
    back = wheellib.ics_events_to_wheel_events(wheellib.parse_ics(ics), "r", __import__("datetime").timezone(__import__("datetime").timedelta(hours=1)))
    assert back[0]["id"] == "ws" and back[0]["timing"] == "daily"


def test_export_yearly_daily_span_as_one_entry_per_day():
    ics = run_js("wheelToIcs(input, 'S', 'Europe/Stockholm')", span_wheel(recurrence="yearly"))
    assert dates(ics) == [
        "UID:ws-d1@yearwheel", "DTSTART:20270302T080000Z", "DTEND:20270302T150000Z", "RRULE:FREQ=YEARLY",
        "UID:ws-d2@yearwheel", "DTSTART:20270303T080000Z", "DTEND:20270303T150000Z", "RRULE:FREQ=YEARLY",
        "UID:ws-d3@yearwheel", "DTSTART:20270304T080000Z", "DTEND:20270304T150000Z", "RRULE:FREQ=YEARLY"]


def test_export_lunch_to_lunch_as_one_continuous_event():
    ics = run_js("wheelToIcs(input, 'S', 'Europe/Stockholm')",
                 span_wheel(start="2027-05-10", end="2027-05-12", startTime="12:00", endTime="12:00", timing="continuous"))
    assert dates(ics) == ["UID:ws@yearwheel", "DTSTART:20270510T100000Z", "DTEND:20270512T100000Z"]
    assert run_js("parseIcs(input).map(i => icsLocalTimes(i, 'Europe/Stockholm'))", ics)[0] == \
        {"start": "2027-05-10", "end": "2027-05-12", "startTime": "12:00", "endTime": "12:00", "timing": "continuous"}


def test_csv_timing_column():
    text = ("title;start;end;start time;end time;timing\n"
            "Workshop;2027-03-02;2027-03-04;09:00;16:00;\n"
            "Retreat;2027-05-10;2027-05-12;12:00;12:00;continuous\n"
            "Bad;2027-05-10;2027-05-12;12:00;12:00;weekly\n")
    res = run_js("csvToItems(input)", text)
    got = {i["title"]: (i["startTime"], i["endTime"], i["timing"]) for i in res["items"]}
    assert got == {"Workshop": ("09:00", "16:00", "daily"), "Retreat": ("12:00", "12:00", "continuous"), "Bad": ("", "", "")}
    assert res["warnings"] == [{"line": 4, "msg": "time"}]


def test_every_ui_text_has_english_and_swedish():
    """Every key used in the page exists in English, and the Swedish dictionary is complete."""
    with open(HTML_PATH, encoding="utf-8") as f:
        html = f.read()
    block = re.search(r"const STR = (\{.*?\n\});\n", html, re.S).group(1)
    keys = run_js("(() => { const STR = " + block + "; return { en: Object.keys(STR.en), sv: Object.keys(STR.sv) }; })()", None)
    en, sv = set(keys["en"]), set(keys["sv"])
    assert sorted(en - sv) == [], "missing Swedish translations"
    assert sorted(sv - en) == [], "Swedish keys without an English original"
    # Whole keys only: t('act_' + action) style prefixes are left out.
    used = set(re.findall(r"data-i18n(?:-ph|-aria)?=\"(\w+)\"", html)) | set(re.findall(r"\bt\('(\w+)'\s*[,)]", html))
    assert sorted(k for k in used if k not in en) == [], "keys used in the page but not defined"


def test_import_times_from_named_zone():
    item = {"startAt": "2027-03-10T10:00", "endAt": "2027-03-10T11:00", "tz": "America/New_York"}
    one_day = {"start": "2027-03-10", "end": "2027-03-10", "timing": ""}
    assert run_js("icsLocalTimes(input, 'Europe/Stockholm')", item) == dict(one_day, startTime="16:00", endTime="17:00")
    item["tz"] = "W. Europe Standard Time"  # Outlook's Windows name: taken as written
    assert run_js("icsLocalTimes(input, 'Europe/Stockholm')", item) == dict(one_day, startTime="10:00", endTime="11:00")


def test_csv_time_columns():
    text = "Title;Start;Start time;End time\nA;2027-01-05;9:00;17.30\nB;2027-01-06;17:00;09:00\nC;2027-01-07;;\n"
    res = run_js("csvToItems(input)", text)
    got = {i["title"]: (i["startTime"], i["endTime"]) for i in res["items"]}
    assert got == {"A": ("09:00", "17:30"), "B": ("", ""), "C": ("", "")}
    assert res["warnings"] == [{"line": 3, "msg": "time"}]


def test_ics_export_round_trip(research_wheel):
    w = research_wheel
    w["events"][0]["notes"] = "Long note, with commas; semicolons\nand a second line " + "x" * 120
    w["events"][1]["status"] = "cancelled"
    w["events"][2]["title"] = "Möte om årshjulet"
    ics = run_js("wheelToIcs(input, '20270101T000000Z')", w)
    assert all(len(line.encode("utf-8")) <= 75 for line in ics.split("\r\n")), "lines folded at 75 octets"
    parsed = {p["uid"]: p for p in wheellib.parse_ics(ics)}
    assert len(parsed) == len(w["events"])
    for e in w["events"]:
        p = parsed[e["id"] + "@yearwheel"]
        assert p["title"] == e["title"]
        assert p["start"] == e["start"]
        assert p["end"] == (e["end"] if e["kind"] == "span" else e["start"])
        assert p["recurrence"] == e["recurrence"]
        assert p["status"] == ("cancelled" if e["status"] == "cancelled" else "planned")
    assert parsed[w["events"][0]["id"] + "@yearwheel"]["notes"] == w["events"][0]["notes"]
    # Re-importing the export maps back to the original ids.
    back = wheellib.ics_events_to_wheel_events(wheellib.parse_ics(ics), "r")
    assert sorted(e["id"] for e in back) == sorted(e["id"] for e in w["events"])
    assert run_js("parseIcs(input)", ics) == wheellib.parse_ics(ics)


# ---------------------------------------------------------------- CSV export and template

DEMO = os.path.join(os.path.dirname(HTML_PATH), "examples", "demo-department-2026-27.json")


def test_csv_export_round_trip_of_demo_wheel():
    """Export the demo wheel to CSV and read it back: every event survives with all its fields."""
    with open(DEMO, encoding="utf-8") as f:
        wheel = json.load(f)
    csv = run_js("wheelToCsv(input)", wheel)
    assert csv.startswith("﻿sep=;\r\ntitle;start;end;ring;status;start time;end time;timing;repeats;until;owner;notes\r\n")
    res = run_js("csvToItems(input)", csv)
    assert res["warnings"] == []
    rings = {r["id"]: r["name"] for r in wheel["rings"]}
    got = sorted((i["title"], i["start"], i["end"], i["ring"], i["status"], i["startTime"], i["endTime"], i["timing"],
                  i["recurrence"], i["interval"], i["monthlyBy"], i["until"], i["owner"], i["notes"]) for i in res["items"])
    want = sorted((e["title"], e["start"], e.get("end", e["start"]), rings[e["ringId"]], e["status"], e.get("startTime", ""),
                   e.get("endTime", ""), e.get("timing", ""), e["recurrence"], e.get("interval", 1), e.get("monthlyBy", ""),
                   e.get("until", ""), e.get("owner", ""), e.get("notes", ""))
                  for e in wheel["events"])
    assert any(e["recurrence"] == "monthly" for e in wheel["events"]), "the demo shows monthly meetings"
    assert got == want


def test_csv_quotes_tricky_text():
    w = {"rings": [{"id": "r", "name": "Lab; west"}], "events": [
        {"id": "a", "ringId": "r", "title": 'Say "hi"; then leave', "kind": "milestone", "start": "2027-01-05",
         "status": "planned", "recurrence": "none", "notes": "Line one\nLine two, with comma", "owner": "Åsa Öberg"}]}
    item = run_js("csvToItems(wheelToCsv(input)).items[0]", w)
    assert (item["title"], item["ring"], item["notes"], item["owner"]) == \
        ('Say "hi"; then leave', "Lab; west", "Line one\nLine two, with comma", "Åsa Öberg")


def test_csv_template_shows_every_kind_of_row():
    res = run_js("csvToItems(csvTemplate())", None)
    assert res["warnings"] == []
    rows = {i["title"]: i for i in res["items"]}
    assert rows["Budget draft"]["end"] == "2027-03-15" and rows["Budget draft"]["startTime"] == ""
    assert (rows["Board meeting"]["startTime"], rows["Board meeting"]["endTime"]) == ("13:00", "15:00")
    assert rows["Course week"]["timing"] == "daily"
    assert rows["Writing retreat"]["timing"] == "continuous"
    assert rows["Annual report due"]["recurrence"] == "yearly"


def test_csv_swedish_headings_and_sep_line():
    text = "sep=,\nTitel,Start,Slut,Ring,Status,Starttid,Sluttid,Upprepas,Ansvarig\n" \
           "Styrelsemöte,2027-04-12,,Institution,planerad,13:00,15:00,varje år,Prefekt\n" \
           "Tentavecka,2027-01-11,2027-01-15,Utbildning,inställd,,,,\n"
    res = run_js("csvToItems(input)", text)
    assert res["warnings"] == []
    a, b = res["items"]
    assert (a["title"], a["startTime"], a["recurrence"], a["owner"], a["status"]) == ("Styrelsemöte", "13:00", "yearly", "Prefekt", "planned")
    assert (b["end"], b["status"]) == ("2027-01-15", "cancelled")


def test_csv_unknown_repeats_is_reported():
    res = run_js("csvToItems(input)", "title;start;repeats\nA;2027-01-05;now and then\n")
    assert res["warnings"] == [{"line": 2, "msg": "repeats"}]
    assert res["items"][0]["recurrence"] == "none"
