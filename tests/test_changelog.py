# Year Wheel. Copyright (c) 2026 Robert Tomkowski <rtom@kth.se>
# MIT License (see the LICENSE file). Developed with the assistance of Claude Code (Anthropic).

"""Changelog rules: moving or cancelling an event always needs a reason. Plus other schema rules."""

import pytest

import wheellib


def entry(action, reason=None):
    e = {"timestamp": "2027-01-10T09:00:00Z", "eventId": "call-eu", "title": "EU call", "action": action,
         "before": {"start": "2027-09-20"}, "after": {"start": "2027-10-05"}}
    if reason is not None:
        e["reason"] = reason
    return e


def errors(w, stdlib):
    return wheellib.validate(w, use_jsonschema=not stdlib) + wheellib.check_changelog_rules(w)


@pytest.fixture(params=[True, False], ids=["stdlib", "jsonschema"])
def stdlib(request):
    if not request.param:
        pytest.importorskip("jsonschema")
    return request.param


@pytest.mark.parametrize("action", ["moved", "cancelled"])
@pytest.mark.parametrize("reason", [None, "", "   "])
def test_move_and_cancel_need_a_reason(research_wheel, stdlib, action, reason):
    research_wheel["changelog"].append(entry(action, reason))
    assert errors(research_wheel, stdlib)


@pytest.mark.parametrize("action", ["moved", "cancelled"])
def test_move_and_cancel_with_reason_ok(research_wheel, stdlib, action):
    research_wheel["changelog"].append(entry(action, "Funder postponed the call"))
    assert errors(research_wheel, stdlib) == []


@pytest.mark.parametrize("action", ["created", "edited", "deleted"])
def test_other_actions_need_no_reason(research_wheel, stdlib, action):
    research_wheel["changelog"].append(entry(action))
    assert errors(research_wheel, stdlib) == []


def test_unknown_action_rejected(research_wheel, stdlib):
    research_wheel["changelog"].append(entry("renamed", "x"))
    assert errors(research_wheel, stdlib)


def test_semantic_rule_also_catches_missing_reason(research_wheel):
    research_wheel["changelog"].append(entry("moved", " "))
    assert wheellib.check_changelog_rules(research_wheel) == ["changelog[0]: 'moved' needs a reason"]


# ---- other schema rules

def test_span_needs_end(research_wheel, stdlib):
    span = next(e for e in research_wheel["events"] if e["kind"] == "span")
    del span["end"]
    assert errors(research_wheel, stdlib)


def test_at_most_six_rings(research_wheel, stdlib):
    for i in range(3):
        research_wheel["rings"].append({"id": "extra-%d" % i, "name": "Extra", "color": "#123456", "order": 4 + i})
    assert len(research_wheel["rings"]) == 7
    assert errors(research_wheel, stdlib)


@pytest.mark.parametrize("bad", ["2027-02-30", "2027-1-5", "next week"])
def test_invalid_dates_rejected(research_wheel, stdlib, bad):
    research_wheel["events"][0]["start"] = bad
    assert errors(research_wheel, stdlib)


# ---- times on milestones

def first(w, kind):
    return next(e for e in w["events"] if e["kind"] == kind)


def test_timed_milestone_valid(research_wheel, stdlib):
    first(research_wheel, "milestone").update(startTime="09:00", endTime="17:00")
    research_wheel["settings"]["timeZone"] = "Europe/Stockholm"
    research_wheel["changelog"].append({"timestamp": "2027-01-01T00:00:00Z", "eventId": "x", "action": "moved",
                                        "before": {"start": "2027-02-03", "startTime": "09:00", "endTime": "17:00"},
                                        "after": {"start": "2027-02-03", "startTime": "09:00", "endTime": "16:00"},
                                        "reason": "Bus leaves earlier"})
    assert errors(research_wheel, stdlib) == []
    assert wheellib.check_rules(research_wheel) == []


@pytest.mark.parametrize("times", [{"startTime": "09:00"}, {"endTime": "17:00"}, {"startTime": "9:00", "endTime": "17:00"},
                                   {"startTime": "24:00", "endTime": "25:00"}])
def test_bad_times_rejected(research_wheel, stdlib, times):
    first(research_wheel, "milestone").update(times)
    assert errors(research_wheel, stdlib)


def test_span_times_need_a_timing(research_wheel, stdlib):
    first(research_wheel, "span").update(startTime="09:00", endTime="17:00")
    assert errors(research_wheel, stdlib)


@pytest.mark.parametrize("timing", ["daily", "continuous"])
def test_span_with_daily_or_continuous_times(research_wheel, stdlib, timing):
    first(research_wheel, "span").update(startTime="12:00", endTime="16:00", timing=timing)
    assert errors(research_wheel, stdlib) == []
    assert wheellib.check_rules(research_wheel) == []


def test_lunch_to_lunch_is_valid_but_daily_needs_end_after_start(research_wheel):
    span = first(research_wheel, "span")
    span.update(startTime="12:00", endTime="12:00", timing="continuous")
    assert wheellib.check_rules(research_wheel) == []  # 12:00 on the first day to 12:00 on the last
    span["timing"] = "daily"
    assert wheellib.check_rules(research_wheel)  # 12:00 to 12:00 each day is empty


def test_timing_not_allowed_on_milestones_or_without_times(research_wheel, stdlib):
    first(research_wheel, "milestone").update(startTime="09:00", endTime="17:00", timing="daily")
    assert errors(research_wheel, stdlib)


def test_timing_needs_times(research_wheel, stdlib):
    first(research_wheel, "span")["timing"] = "daily"
    assert errors(research_wheel, stdlib)


def test_unknown_timing_rejected(research_wheel, stdlib):
    first(research_wheel, "span").update(startTime="09:00", endTime="17:00", timing="weekly")
    assert errors(research_wheel, stdlib)


def test_end_time_after_start_time(research_wheel):
    first(research_wheel, "milestone").update(startTime="17:00", endTime="09:00")
    assert any("end time must be after start time" in e for e in wheellib.check_rules(research_wheel))


@pytest.mark.parametrize("value,ok", [(0.1, True), (0.4, True), (1, True), (0.05, False), (1.2, False), ("solid", False)])
def test_colour_opacity_range(research_wheel, stdlib, value, ok):
    research_wheel["settings"]["colorOpacity"] = value
    assert (errors(research_wheel, stdlib) == []) == ok


@pytest.mark.parametrize("value,ok", [(0, True), (0.1, True), (1, True), (-0.1, False), (1.5, False)])
def test_ring_opacity_range(research_wheel, stdlib, value, ok):
    research_wheel["settings"]["ringOpacity"] = value
    assert (errors(research_wheel, stdlib) == []) == ok


@pytest.mark.parametrize("value,ok", [(0.7, True), (1, True), (1.5, True), (0.5, False), (2, False)])
def test_text_scale_range(research_wheel, stdlib, value, ok):
    research_wheel["settings"]["textScale"] = value
    assert (errors(research_wheel, stdlib) == []) == ok


@pytest.mark.parametrize("value,ok", [("january", True), ("yearStart", True), ("march", False)])
def test_wheel_top(research_wheel, stdlib, value, ok):
    research_wheel["settings"]["wheelTop"] = value
    assert (errors(research_wheel, stdlib) == []) == ok


def test_hidden_ring(research_wheel, stdlib):
    research_wheel["rings"][0]["hidden"] = True
    assert errors(research_wheel, stdlib) == []
    research_wheel["rings"][0]["hidden"] = "yes"
    assert errors(research_wheel, stdlib)


def test_older_colour_strength_still_valid(research_wheel, stdlib):
    research_wheel["settings"]["colorStrength"] = 1.25  # converted by the app on open
    assert errors(research_wheel, stdlib) == []


def test_review_quarter_format(research_wheel, stdlib):
    research_wheel["reviews"].append({"quarter": "2027-Q1", "date": "2027-01-08", "reviewer": "A"})
    assert errors(research_wheel, stdlib) == []
    research_wheel["reviews"].append({"quarter": "2027-Q5", "date": "2027-01-08"})
    assert errors(research_wheel, stdlib)


def test_semantic_rules(research_wheel):
    research_wheel["events"][0]["ringId"] = "nope"
    research_wheel["events"][1]["id"] = research_wheel["events"][2]["id"]
    span = next(e for e in research_wheel["events"] if e["kind"] == "span")
    span["end"] = "2000-01-01"
    errs = wheellib.check_rules(research_wheel)
    assert any("unknown ringId" in e for e in errs)
    assert any("duplicate event id" in e for e in errs)
    assert any("end is before start" in e for e in errs)


def test_migration_from_version_0():
    old = {"id": "w", "title": "Old", "yearStart": "2027-01-01",
           "rings": [{"id": "r", "name": "R", "color": "#000000", "order": 0}], "events": []}
    w = wheellib.migrate(old)
    assert w["schemaVersion"] == wheellib.CURRENT_SCHEMA_VERSION
    assert wheellib.full_check(w) == []


def test_newer_schema_version_refused():
    with pytest.raises(ValueError):
        wheellib.migrate({"schemaVersion": 99})
