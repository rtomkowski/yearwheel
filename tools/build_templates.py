# Year Wheel. Copyright (c) 2026 Robert Tomkowski <rtom@kth.se>
# MIT License (see the LICENSE file). Developed with the assistance of Claude Code (Anthropic).

"""Generate the template wheels in templates/ and embed them in yearwheel.html.

Usage: python tools/build_templates.py

All dates are PLACEHOLDERS. They are not institution calendar facts. Users set
their own year start, study periods and dates in the app. The app shifts template
dates to the year start the user picks when creating a new wheel.

The embedded copy in yearwheel.html lives between the markers
/*TEMPLATES-BEGIN*/ and /*TEMPLATES-END*/ and is rewritten on every run.
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wheellib import ROOT, dump_wheel, full_check, quarter_start_month  # noqa: E402

# Colour-blind safe ring palette (Okabe-Ito subset, yellow left out for contrast).
PALETTE = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#D55E00"]

EDIT_ME = "Placeholder date. Edit me."


def ring(i, rid, name):
    return {"id": rid, "name": name, "color": PALETTE[i], "order": i}


# Key order matches the app's canonical order so files round-trip byte for byte.
def ms(eid, ring_id, title, start, recurrence="none"):
    return {"id": eid, "ringId": ring_id, "title": title + " (edit me)", "kind": "milestone",
            "start": start, "status": "planned", "recurrence": recurrence,
            "notes": EDIT_ME, "placeholder": True}


def span(eid, ring_id, title, start, end, recurrence="none"):
    return {"id": eid, "ringId": ring_id, "title": title + " (edit me)", "kind": "span",
            "start": start, "end": end, "status": "planned", "recurrence": recurrence,
            "notes": EDIT_ME, "placeholder": True}


def academic_periods(y):
    """Four study periods for an academic year starting in autumn of year y. Placeholders."""
    return [
        {"id": "p1", "label": "P1", "start": "%d-08-31" % y, "end": "%d-10-30" % y, "placeholder": True},
        {"id": "p2", "label": "P2", "start": "%d-11-02" % y, "end": "%d-01-15" % (y + 1), "placeholder": True},
        {"id": "p3", "label": "P3", "start": "%d-01-18" % (y + 1), "end": "%d-03-19" % (y + 1), "placeholder": True},
        {"id": "p4", "label": "P4", "start": "%d-03-22" % (y + 1), "end": "%d-06-04" % (y + 1), "placeholder": True},
    ]


def base(tid, title, year_start, rings, events, show_periods=False, periods=None, years=1):
    return {
        "schemaVersion": 1,
        "id": tid,
        "title": title,
        "owner": "",
        "template": tid,
        "yearStart": year_start,
        "years": years,
        "settings": {
            "language": "en",
            "weekTicks": False,
            "showPeriods": show_periods,
            "showQuarters": True,
            "quarterStartMonth": quarter_start_month(year_start),
            "periods": periods or [],
        },
        "rings": rings,
        "events": events,
        "reviews": [],
        "changelog": [],
    }


def blank():
    rings = [ring(0, "research", "Research"), ring(1, "education", "Education"), ring(2, "admin", "Admin")]
    return base("blank", "My year wheel", "2027-01-01", rings, [], periods=academic_periods(2026))


def research_team():
    rings = [
        ring(0, "projects", "Projects"),
        ring(1, "funding", "Funding calls"),
        ring(2, "dissemination", "Conferences and papers"),
        ring(3, "team", "Team"),
    ]
    events = [
        span("proj-a-wp2", "projects", "Project A, work package 2", "2027-02-01", "2027-06-30"),
        ms("proj-a-deliv", "projects", "Project A deliverable D2.1", "2027-06-30"),
        span("proj-b-campaign", "projects", "Project B measurement campaign", "2027-09-06", "2027-11-26"),
        ms("proj-b-report", "projects", "Project B annual report", "2027-12-15", "yearly"),
        ms("call-national", "funding", "National research council call", "2027-03-15", "yearly"),
        ms("call-eu", "funding", "EU call deadline", "2027-09-20"),
        span("call-prep", "funding", "Proposal writing", "2027-08-16", "2027-09-20"),
        ms("conf-abstract", "dissemination", "Conference abstract deadline", "2027-01-20"),
        span("conf-main", "dissemination", "Main conference", "2027-06-07", "2027-06-11", "yearly"),
        ms("paper-submit", "dissemination", "Journal paper submission", "2027-04-30"),
        span("team-summer", "team", "Summer break", "2027-07-01", "2027-08-06", "yearly"),
        ms("team-kickoff", "team", "Group kick-off day", "2027-08-23", "yearly"),
        ms("team-dev-talks", "team", "Development talks", "2027-11-10", "yearly"),
    ]
    return base("research-team", "Research team year wheel", "2027-01-01", rings, events,
                periods=academic_periods(2026))


def department_admin():
    rings = [
        ring(0, "board", "Board and meetings"),
        ring(1, "budget", "Budget and finance"),
        ring(2, "reporting", "Reporting"),
        ring(3, "staff", "Staff and HR"),
    ]
    events = [
        ms("board-feb", "board", "Board meeting", "2027-02-10", "yearly"),
        ms("board-apr", "board", "Board meeting", "2027-04-21", "yearly"),
        ms("board-sep", "board", "Board meeting", "2027-09-15", "yearly"),
        ms("board-nov", "board", "Board meeting", "2027-11-24", "yearly"),
        span("budget-draft", "budget", "Budget draft for next year", "2027-08-23", "2027-10-08", "yearly"),
        ms("budget-decision", "budget", "Budget decision", "2027-11-24", "yearly"),
        ms("tertial-1", "budget", "Financial follow-up 1", "2027-05-12", "yearly"),
        ms("tertial-2", "budget", "Financial follow-up 2", "2027-09-08", "yearly"),
        span("annual-report", "reporting", "Annual report writing", "2027-01-11", "2027-02-19", "yearly"),
        ms("annual-report-due", "reporting", "Annual report due", "2027-02-26", "yearly"),
        ms("ops-plan", "reporting", "Operational plan due", "2027-12-10", "yearly"),
        span("appraisals", "staff", "Performance reviews", "2027-03-01", "2027-04-16", "yearly"),
        ms("salary-review", "staff", "Salary review", "2027-10-01", "yearly"),
        ms("staff-day", "staff", "Staff day", "2027-08-26", "yearly"),
    ]
    return base("department-admin", "Department admin year", "2027-01-01", rings, events,
                periods=academic_periods(2026))


def lab_maintenance():
    rings = [
        ring(0, "calibration", "Calibration"),
        ring(1, "maintenance", "Maintenance"),
        ring(2, "service", "Service visits"),
        ring(3, "safety", "Safety"),
    ]
    events = [
        ms("cal-cmm", "calibration", "CMM calibration", "2027-02-15", "yearly"),
        ms("cal-interferometer", "calibration", "Interferometer calibration", "2027-04-12", "yearly"),
        ms("cal-roughness-1", "calibration", "Roughness standard check", "2027-03-08", "yearly"),
        ms("cal-roughness-2", "calibration", "Roughness standard check", "2027-09-06", "yearly"),
        ms("cal-gauge-blocks", "calibration", "Gauge block verification", "2027-10-18", "yearly"),
        span("maint-summer", "maintenance", "Preventive maintenance, all instruments", "2027-07-05", "2027-07-23", "yearly"),
        span("maint-winter", "maintenance", "Preventive maintenance, all instruments", "2027-12-13", "2027-12-22", "yearly"),
        ms("maint-filters", "maintenance", "Air filter and climate check", "2027-05-17", "yearly"),
        span("svc-cmm", "service", "CMM vendor service visit", "2027-02-08", "2027-02-10", "yearly"),
        ms("svc-microscope", "service", "Optical profilometer service", "2027-11-08", "yearly"),
        ms("safety-inspection", "safety", "Lab safety inspection", "2027-03-22", "yearly"),
        ms("safety-chemicals", "safety", "Chemical inventory", "2027-09-27", "yearly"),
        ms("safety-training", "safety", "Safety training for new users", "2027-09-02", "yearly"),
    ]
    return base("lab-maintenance", "Lab maintenance and calibration", "2027-01-01", rings, events,
                periods=academic_periods(2026))


def phd_journey():
    """Four-year doctoral plan in one file. Yearly items repeat in every year automatically."""
    rings = [
        ring(0, "milestones", "Milestones"),
        ring(1, "courses", "Courses"),
        ring(2, "papers", "Papers and conferences"),
        ring(3, "teaching", "Teaching"),
    ]
    events = [
        ms("phd-start", "milestones", "Start of doctoral studies", "2026-09-01"),
        ms("isp-update", "milestones", "Individual study plan (ISP) update", "2026-11-16", "yearly"),
        ms("isp-first", "milestones", "First ISP approved", "2026-12-14"),
        ms("lic-seminar", "milestones", "Licentiate seminar (if applicable)", "2028-12-08"),
        ms("final-seminar", "milestones", "Final seminar", "2030-03-15"),
        ms("defence", "milestones", "Thesis defence", "2030-06-05"),
        span("course-methods", "courses", "Research methods course", "2026-09-07", "2026-10-30"),
        span("course-ethics", "courses", "Research ethics course", "2027-01-18", "2027-03-19"),
        span("course-field", "courses", "Advanced course in your field", "2027-09-06", "2027-12-17"),
        span("course-teaching", "courses", "Teaching and learning in higher education", "2028-01-17", "2028-03-17"),
        ms("paper-1", "papers", "Paper 1 submitted", "2027-06-15"),
        ms("paper-2", "papers", "Paper 2 submitted", "2028-05-31"),
        ms("paper-3", "papers", "Paper 3 submitted", "2029-04-30"),
        span("conference", "papers", "Annual conference", "2027-06-07", "2027-06-11", "yearly"),
        span("thesis-writing", "papers", "Thesis writing", "2029-09-01", "2030-02-15"),
        span("teaching-lab", "teaching", "Lab supervision", "2027-01-18", "2027-03-19", "yearly"),
    ]
    return base("phd-journey", "PhD journey", "2026-08-31", rings, events, show_periods=True,
                periods=academic_periods(2026), years=4)


def course_periods():
    rings = [
        ring(0, "teaching", "Courses I teach"),
        ring(1, "taking", "Courses I take"),
        ring(2, "exams", "Exams"),
        ring(3, "planning", "Course planning"),
    ]
    events = [
        span("teach-p1", "teaching", "Course A (teaching)", "2026-08-31", "2026-10-30", "yearly"),
        span("teach-p3", "teaching", "Course B (teaching)", "2027-01-18", "2027-03-19", "yearly"),
        span("take-p2", "taking", "Course C (studying)", "2026-11-02", "2027-01-15"),
        span("take-p4", "taking", "Course D (studying)", "2027-03-22", "2027-06-04"),
        span("exam-p1", "exams", "Exam week", "2026-10-26", "2026-10-30", "yearly"),
        span("exam-p2", "exams", "Exam week", "2027-01-11", "2027-01-15", "yearly"),
        span("exam-p3", "exams", "Exam week", "2027-03-15", "2027-03-19", "yearly"),
        span("exam-p4", "exams", "Exam week", "2027-05-31", "2027-06-04", "yearly"),
        span("reexam", "exams", "Re-exam period", "2027-08-16", "2027-08-27", "yearly"),
        ms("course-eval", "planning", "Course evaluation report", "2026-11-20", "yearly"),
        ms("syllabus", "planning", "Syllabus changes due", "2027-02-15", "yearly"),
        ms("schedule", "planning", "Schedule requests for next year", "2027-04-15", "yearly"),
    ]
    return base("course-periods", "Course periods", "2026-08-31", rings, events, show_periods=True,
                periods=academic_periods(2026))


# ---------------------------------------------------------------- Swedish versions
# Every English text in the templates must have a Swedish entry; build fails otherwise.
SV_LABELS = {
    "Blank": "Tom",
    "Research team": "Forskargrupp",
    "Department or unit admin": "Institution eller enhet, administration",
    "Lab maintenance and calibration": "Labbunderhåll och kalibrering",
    "PhD journey (4 years)": "Doktorandresan (4 år)",
    "Course periods": "Läsperioder och kurser",
}
SV = {
    # wheel titles
    "My year wheel": "Mitt årshjul", "Research team year wheel": "Forskargruppens årshjul",
    "Department admin year": "Institutionens administrativa år",
    "Lab maintenance and calibration": "Labbunderhåll och kalibrering", "PhD journey": "Doktorandresan",
    "Course periods": "Läsperioder och kurser",
    # rings
    "Research": "Forskning", "Education": "Utbildning", "Admin": "Administration", "Projects": "Projekt",
    "Funding calls": "Utlysningar", "Conferences and papers": "Konferenser och artiklar", "Team": "Gruppen",
    "Board and meetings": "Styrelse och möten", "Budget and finance": "Budget och ekonomi",
    "Reporting": "Rapportering", "Staff and HR": "Personal och HR", "Calibration": "Kalibrering",
    "Maintenance": "Underhåll", "Service visits": "Servicebesök", "Safety": "Säkerhet",
    "Milestones": "Milstolpar", "Courses": "Kurser", "Papers and conferences": "Artiklar och konferenser",
    "Teaching": "Undervisning", "Courses I teach": "Kurser jag undervisar i", "Courses I take": "Kurser jag läser",
    "Exams": "Tentor", "Course planning": "Kursplanering",
    # events: research team
    "Project A, work package 2": "Projekt A, arbetspaket 2", "Project A deliverable D2.1": "Projekt A, leverans D2.1",
    "Project B measurement campaign": "Projekt B, mätkampanj", "Project B annual report": "Projekt B, årsrapport",
    "National research council call": "Utlysning från nationellt forskningsråd",
    "EU call deadline": "Sista dag för EU-utlysning", "Proposal writing": "Ansökningsskrivande",
    "Conference abstract deadline": "Sista dag för konferensabstrakt", "Main conference": "Huvudkonferens",
    "Journal paper submission": "Tidskriftsartikel inskickad", "Summer break": "Sommaruppehåll",
    "Group kick-off day": "Gruppens uppstartsdag", "Development talks": "Utvecklingssamtal",
    # department admin
    "Board meeting": "Styrelsemöte", "Budget draft for next year": "Budgetförslag för nästa år",
    "Budget decision": "Budgetbeslut", "Financial follow-up 1": "Ekonomisk uppföljning 1",
    "Financial follow-up 2": "Ekonomisk uppföljning 2", "Annual report writing": "Arbete med årsredovisning",
    "Annual report due": "Årsredovisning klar", "Operational plan due": "Verksamhetsplan klar",
    "Performance reviews": "Medarbetarsamtal", "Salary review": "Lönerevision", "Staff day": "Personaldag",
    # lab
    "CMM calibration": "Kalibrering av koordinatmätmaskin (CMM)",
    "Interferometer calibration": "Kalibrering av interferometer",
    "Roughness standard check": "Kontroll av ytjämnhetsnormal", "Gauge block verification": "Verifiering av passbitar",
    "Preventive maintenance, all instruments": "Förebyggande underhåll, alla instrument",
    "Air filter and climate check": "Kontroll av luftfilter och klimat",
    "CMM vendor service visit": "Servicebesök från CMM-leverantören",
    "Optical profilometer service": "Service av optisk profilometer", "Lab safety inspection": "Säkerhetsrond i labbet",
    "Chemical inventory": "Kemikalieinventering", "Safety training for new users": "Säkerhetsutbildning för nya användare",
    # PhD
    "Start of doctoral studies": "Start av forskarutbildningen",
    "Individual study plan (ISP) update": "Uppdatering av individuell studieplan (ISP)",
    "First ISP approved": "Första ISP fastställd", "Licentiate seminar (if applicable)": "Licentiatseminarium (om aktuellt)",
    "Final seminar": "Slutseminarium", "Thesis defence": "Disputation",
    "Research methods course": "Kurs i forskningsmetodik", "Research ethics course": "Kurs i forskningsetik",
    "Advanced course in your field": "Fördjupningskurs inom ditt område",
    "Teaching and learning in higher education": "Högskolepedagogik",
    "Paper 1 submitted": "Artikel 1 inskickad", "Paper 2 submitted": "Artikel 2 inskickad",
    "Paper 3 submitted": "Artikel 3 inskickad", "Annual conference": "Årlig konferens",
    "Thesis writing": "Avhandlingsskrivande", "Lab supervision": "Labbhandledning",
    # course periods
    "Course A (teaching)": "Kurs A (undervisning)", "Course B (teaching)": "Kurs B (undervisning)",
    "Course C (studying)": "Kurs C (studier)", "Course D (studying)": "Kurs D (studier)",
    "Exam week": "Tentavecka", "Re-exam period": "Omtentaperiod", "Course evaluation report": "Kursvärderingsrapport",
    "Syllabus changes due": "Ändringar i kursplan klara", "Schedule requests for next year": "Schemaönskemål för nästa år",
}
EDIT_ME_SV = "Platshållardatum. Ändra mig."


def sv(text):
    if text not in SV:
        raise SystemExit("Missing Swedish translation for %r in tools/build_templates.py" % text)
    return SV[text]


def to_swedish(wheel):
    """The same template with Swedish texts. Ids and dates are unchanged."""
    w = json.loads(json.dumps(wheel))
    w["title"] = sv(w["title"])
    w["settings"]["language"] = "sv"
    for r in w["rings"]:
        r["name"] = sv(r["name"])
    for e in w["events"]:
        e["title"] = sv(e["title"][:-len(" (edit me)")]) + " (ändra mig)"
        if e.get("notes") == EDIT_ME:
            e["notes"] = EDIT_ME_SV
    return w


TEMPLATES = [
    ("blank", "Blank", blank),
    ("research-team", "Research team", research_team),
    ("department-admin", "Department or unit admin", department_admin),
    ("lab-maintenance", "Lab maintenance and calibration", lab_maintenance),
    ("phd-journey", "PhD journey (4 years)", phd_journey),
    ("course-periods", "Course periods", course_periods),
]


def main():
    out_dir = os.path.join(ROOT, "templates")
    sv_dir = os.path.join(out_dir, "sv")
    os.makedirs(sv_dir, exist_ok=True)
    embedded = []
    failed = False
    for tid, label, fn in TEMPLATES:
        wheel = fn()
        wheel_sv = to_swedish(wheel)
        for name, w in (("", wheel), ("sv/", wheel_sv)):
            errors = full_check(w)
            if errors:
                failed = True
                print("INVALID %s%s: %s" % (name, tid, errors))
        dump_wheel(wheel, os.path.join(out_dir, tid + ".json"))
        dump_wheel(wheel_sv, os.path.join(sv_dir, tid + ".json"))
        embedded.append({"id": tid, "label": {"en": label, "sv": SV_LABELS[label]},
                         "wheel": {"en": wheel, "sv": wheel_sv}})
        print("wrote templates/%s.json and templates/sv/%s.json" % (tid, tid))

    html_path = os.path.join(ROOT, "yearwheel.html")
    if os.path.exists(html_path):
        with open(html_path, encoding="utf-8") as f:
            html = f.read()
        payload = "/*TEMPLATES-BEGIN*/" + json.dumps(embedded, ensure_ascii=False) + "/*TEMPLATES-END*/"
        new_html, n = re.subn(r"/\*TEMPLATES-BEGIN\*/.*?/\*TEMPLATES-END\*/", lambda m: payload, html, flags=re.S)
        if n == 1:
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(new_html)
            print("embedded %d templates in yearwheel.html" % len(embedded))
        else:
            print("WARNING: template markers not found in yearwheel.html")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
