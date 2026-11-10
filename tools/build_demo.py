# Year Wheel. Copyright (c) 2026 Robert Tomkowski <rtom@kth.se>
# MIT License (see the LICENSE file). Developed with the assistance of Claude Code (Anthropic).

"""Generate the demo wheel examples/demo-department-2026-27.json.

Usage: python tools/build_demo.py

Everything in it is fictional: a made-up department, roles instead of names, invented courses,
projects and dates. It shows most features: five rings, spans and milestones, times (one day,
the same hours each day, and lunch to lunch), yearly items, moved / cancelled / done events with
reasons in the change log, study periods and week numbers.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wheellib import ROOT, dump_wheel, full_check  # noqa: E402


def ev(eid, ring, title, start, end=None, status="planned", rec="none", owner=None, notes=None,
       times=None, timing=None, prev=None):
    e = {"id": eid, "ringId": ring, "title": title, "kind": "span" if end else "milestone", "start": start}
    if end:
        e["end"] = end
    if times:
        e["startTime"], e["endTime"] = times
        if end:
            e["timing"] = timing or "daily"
    e["status"] = status
    e["recurrence"] = rec
    if owner:
        e["owner"] = owner
    if notes:
        e["notes"] = notes
    if prev:
        e["prevStart"] = prev
    return e


def build():
    rings = [
        {"id": "research", "name": "Research", "color": "#0072B2", "order": 0},
        {"id": "education", "name": "Education", "color": "#E69F00", "order": 1},
        {"id": "admin", "name": "Department", "color": "#009E73", "order": 2},
        {"id": "lab", "name": "Lab", "color": "#CC79A7", "order": 3},
        {"id": "breaks", "name": "Breaks", "color": "#56B4E9", "order": 4},
    ]
    events = [
        # Research
        ev("alpha-campaign", "research", "Project ALPHA measurement campaign", "2026-09-14", "2026-11-27",
           owner="Project leader", notes="Fictional project used for the demo."),
        ev("alpha-d32", "research", "ALPHA deliverable D3.2", "2026-12-15", owner="Project leader"),
        ev("paper-submitted", "research", "Journal paper submitted", "2026-10-30", status="done", owner="PhD student 1"),
        ev("eu-proposal", "research", "Proposal writing, EU call", "2027-01-11", "2027-02-19", owner="Research group"),
        ev("eu-deadline", "research", "EU call deadline", "2027-02-24", status="moved", prev="2027-02-17",
           notes="The funder extended the deadline by one week."),
        ev("council-call", "research", "Research council call deadline", "2027-03-16", rec="yearly"),
        ev("writing-retreat", "research", "Writing retreat", "2027-04-12", "2027-04-14",
           times=("12:00", "12:00"), timing="continuous", notes="Lunch to lunch, off site."),
        ev("conference", "research", "International conference", "2027-06-07", "2027-06-10",
           times=("09:00", "17:30"), timing="daily", rec="yearly"),
        # Education
        ev("mg101", "education", "Course MG101 Metrology basics", "2026-08-31", "2026-10-30", rec="yearly",
           owner="Course coordinator"),
        ev("exam-p1", "education", "Exam week P1", "2026-10-26", "2026-10-30", rec="yearly"),
        ev("course-eval", "education", "Course evaluation report", "2026-11-20", owner="Course coordinator"),
        ev("project-presentations", "education", "Student project presentations", "2026-12-10",
           times=("13:00", "17:00")),
        ev("exam-p2", "education", "Exam week P2", "2027-01-11", "2027-01-15", rec="yearly"),
        ev("mg205", "education", "Course MG205 Surface analysis", "2027-01-18", "2027-03-19", owner="Course coordinator"),
        ev("syllabus", "education", "Syllabus changes due", "2027-02-15", rec="yearly", owner="Director of studies"),
        ev("reexam", "education", "Re-exam period", "2027-08-16", "2027-08-27", rec="yearly"),
        # Department
        ev("board-sep", "admin", "Department board meeting", "2026-09-16", times=("13:15", "15:00"), status="done"),
        ev("dept-day", "admin", "Department day", "2026-09-24", times=("09:00", "17:00"), status="done",
           owner="Head of department"),
        ev("budget-decision", "admin", "Budget decision", "2026-11-25", owner="Head of department"),
        ev("board-dec", "admin", "Department board meeting", "2026-12-02", times=("13:15", "15:00"), status="moved",
           notes="Moved to the afternoon slot."),
        ev("christmas-lunch", "admin", "Christmas lunch", "2026-12-17", times=("11:30", "14:00"), status="cancelled"),
        ev("board-feb", "admin", "Department board meeting", "2027-02-17", times=("13:15", "15:00")),
        ev("annual-report", "admin", "Annual report due", "2027-02-26", rec="yearly", owner="Administrator"),
        ev("appraisals", "admin", "Performance reviews", "2027-03-01", "2027-04-16", rec="yearly", owner="Head of department"),
        ev("budget-draft", "admin", "Budget draft for next year", "2027-05-03", "2027-06-11", rec="yearly"),
        ev("board-may", "admin", "Department board meeting", "2027-05-19", times=("13:15", "15:00")),
        # Lab
        ev("safety-training", "lab", "Safety training for new users", "2026-09-03", times=("09:00", "12:00"),
           status="done", rec="yearly", owner="Lab manager"),
        ev("cmm-cal", "lab", "CMM calibration", "2026-10-05", status="done", rec="yearly", owner="Lab manager"),
        ev("cmm-service", "lab", "CMM vendor service visit", "2027-02-08", "2027-02-10",
           times=("08:00", "16:00"), timing="daily", owner="Lab manager"),
        ev("safety-inspection", "lab", "Lab safety inspection", "2027-03-22", rec="yearly"),
        ev("interferometer-cal", "lab", "Interferometer calibration", "2027-04-12", rec="yearly", owner="Lab manager"),
        ev("maintenance", "lab", "Preventive maintenance, all instruments", "2027-07-05", "2027-07-23", rec="yearly"),
        # Breaks
        ev("autumn-break", "breaks", "Autumn break", "2026-10-26", "2026-10-30"),
        ev("christmas-break", "breaks", "Christmas break", "2026-12-23", "2027-01-06"),
        ev("summer-break", "breaks", "Summer break", "2027-07-01", "2027-08-06"),
    ]
    changelog = [
        {"timestamp": "2026-09-16T15:10:00Z", "eventId": "board-sep", "title": "Department board meeting",
         "action": "edited"},
        {"timestamp": "2026-10-12T08:30:00Z", "eventId": "eu-deadline", "title": "EU call deadline", "action": "moved",
         "before": {"start": "2027-02-17"}, "after": {"start": "2027-02-24"},
         "reason": "The funder extended the call deadline by one week."},
        {"timestamp": "2026-10-20T10:05:00Z", "eventId": "board-dec", "title": "Department board meeting",
         "action": "moved", "before": {"start": "2026-12-02", "startTime": "09:15", "endTime": "11:00"},
         "after": {"start": "2026-12-02", "startTime": "13:15", "endTime": "15:00"},
         "reason": "Morning clashes with the exam period; moved to the afternoon slot."},
        {"timestamp": "2026-10-28T14:00:00Z", "eventId": "christmas-lunch", "title": "Christmas lunch",
         "action": "cancelled", "before": {"start": "2026-12-17", "startTime": "11:30", "endTime": "14:00"},
         "after": {"start": "2026-12-17", "startTime": "11:30", "endTime": "14:00"},
         "reason": "Combined with the spring department day instead."},
        {"timestamp": "2026-10-30T16:20:00Z", "eventId": "paper-submitted", "title": "Journal paper submitted",
         "action": "edited"},
    ]
    wheel = {
        "schemaVersion": 1,
        "id": "demo-department-2026-27",
        "title": "Demo department 2026/27",
        "owner": "Demo department (fictional)",
        "yearStart": "2026-08-31",
        "years": 1,
        "settings": {
            "language": "en",
            "weekTicks": True,
            "showPeriods": True,
            "showQuarters": True,
            "quarterStartMonth": 9,
            "timeZone": "Europe/Stockholm",
            "ringOpacity": 0.15,
            "periods": [
                {"id": "p1", "label": "P1", "start": "2026-08-31", "end": "2026-10-30"},
                {"id": "p2", "label": "P2", "start": "2026-11-02", "end": "2027-01-15"},
                {"id": "p3", "label": "P3", "start": "2027-01-18", "end": "2027-03-19"},
                {"id": "p4", "label": "P4", "start": "2027-03-22", "end": "2027-06-04"},
            ],
        },
        "rings": rings,
        "events": events,
        "reviews": [],
        "changelog": changelog,
    }
    return wheel


def main():
    wheel = build()
    errors = full_check(wheel)
    if errors:
        print("INVALID demo wheel:")
        for e in errors:
            print("  - " + e)
        return 1
    out_dir = os.path.join(ROOT, "examples")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "demo-department-2026-27.json")
    dump_wheel(wheel, path)
    print("wrote %s (%d events)" % (os.path.relpath(path, ROOT), len(wheel["events"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
