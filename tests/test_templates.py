# Year Wheel. Copyright (c) 2026 Robert Tomkowski <rtom@kth.se>
# MIT License (see the LICENSE file). Developed with the assistance of Claude Code (Anthropic).

"""Every template validates against the schema and follows the template conventions."""

import json
import os
import re

import pytest

from conftest import HTML_PATH, template_paths
import build_templates
import wheellib

EXPECTED = {"blank", "research-team", "department-admin", "lab-maintenance", "phd-journey", "course-periods"}


def test_all_templates_present():
    names = {os.path.splitext(os.path.basename(p))[0] for p in template_paths()}
    assert names == EXPECTED


@pytest.mark.parametrize("path", template_paths(), ids=os.path.basename)
def test_template_valid_with_builtin_validator(path):
    wheel = wheellib.load_wheel(path)
    assert wheellib.validate(wheel, use_jsonschema=False) == []
    assert wheellib.check_rules(wheel) == []


@pytest.mark.parametrize("path", template_paths(), ids=os.path.basename)
def test_template_valid_with_jsonschema_if_installed(path):
    pytest.importorskip("jsonschema")
    assert wheellib.validate(wheellib.load_wheel(path)) == []


@pytest.mark.parametrize("path", template_paths(), ids=os.path.basename)
def test_template_conventions(path):
    w = wheellib.load_wheel(path)
    assert 3 <= len(w["rings"]) <= 4, "templates have 3 to 4 rings"
    assert w["changelog"] == [] and w["reviews"] == []
    for e in w["events"]:
        assert e.get("placeholder") is True
        assert e["title"].endswith("(edit me)")
    for p in w["settings"]["periods"]:
        assert p.get("placeholder") is True, "study period dates are placeholders, not facts"
    end = wheellib.datetime.date.fromisoformat(w["yearStart"]).replace(year=int(w["yearStart"][:4]) + w["years"])
    for e in w["events"]:
        assert w["yearStart"] <= e["start"] < end.isoformat(), "%s starts outside the wheel" % e["id"]


@pytest.mark.parametrize("start,month", [("2027-01-01", 1), ("2026-08-31", 9), ("2026-08-15", 8), ("2026-12-20", 1)])
def test_quarter_start_month(start, month):
    assert wheellib.quarter_start_month(start) == month


def test_academic_templates_have_september_quarters():
    for tid in ("phd-journey", "course-periods"):
        w = wheellib.load_wheel(os.path.join(os.path.dirname(HTML_PATH), "templates", tid + ".json"))
        assert w["settings"]["quarterStartMonth"] == 9


def test_phd_template_is_multi_year_with_yearly_items():
    w = wheellib.load_wheel(os.path.join(os.path.dirname(HTML_PATH), "templates", "phd-journey.json"))
    assert w["years"] >= 4
    assert any(e["recurrence"] == "yearly" for e in w["events"])
    years = {e["start"][:4] for e in w["events"]}
    assert len(years) >= 4, "milestones are spread over the whole doctorate"


def test_templates_are_up_to_date_and_embedded():
    """templates/*.json, templates/sv/*.json and the copy inside yearwheel.html match build_templates.py."""
    with open(HTML_PATH, encoding="utf-8") as f:
        html = f.read()
    m = re.search(r"/\*TEMPLATES-BEGIN\*/(.*?)/\*TEMPLATES-END\*/", html, re.S)
    assert m, "template markers missing in yearwheel.html"
    embedded = {t["id"]: t for t in json.loads(m.group(1))}
    root = os.path.dirname(HTML_PATH)
    for tid, label, fn in build_templates.TEMPLATES:
        en = fn()
        sv = build_templates.to_swedish(en)
        assert embedded[tid]["wheel"] == {"en": en, "sv": sv}, "run tools/build_templates.py (%s is stale in the HTML)" % tid
        assert embedded[tid]["label"] == {"en": label, "sv": build_templates.SV_LABELS[label]}
        assert wheellib.load_wheel(os.path.join(root, "templates", tid + ".json")) == en
        assert wheellib.load_wheel(os.path.join(root, "templates", "sv", tid + ".json")) == sv


SV_PATHS = sorted(p for p in (os.path.join(os.path.dirname(HTML_PATH), "templates", "sv", f)
                              for f in os.listdir(os.path.join(os.path.dirname(HTML_PATH), "templates", "sv")))
                  if p.endswith(".json"))


@pytest.mark.parametrize("path", SV_PATHS, ids=os.path.basename)
def test_swedish_templates(path):
    sv = wheellib.load_wheel(path)
    en = wheellib.load_wheel(os.path.join(os.path.dirname(os.path.dirname(path)), os.path.basename(path)))
    assert wheellib.full_check(sv) == []
    assert sv["settings"]["language"] == "sv"
    # Same structure and dates; only texts differ.
    assert [e["id"] for e in sv["events"]] == [e["id"] for e in en["events"]]
    assert [(e["start"], e.get("end")) for e in sv["events"]] == [(e["start"], e.get("end")) for e in en["events"]]
    for e_sv, e_en in zip(sv["events"], en["events"]):
        assert e_sv["title"].endswith("(ändra mig)")
        assert e_sv["title"] != e_en["title"]
    assert all(r["name"] != r_en["name"] for r, r_en in zip(sv["rings"], en["rings"]))
