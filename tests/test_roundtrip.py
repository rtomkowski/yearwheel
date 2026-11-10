# Year Wheel. Copyright (c) 2026 Robert Tomkowski <rtom@kth.se>
# MIT License (see the LICENSE file). Developed with the assistance of Claude Code (Anthropic).

"""Save and load keep every byte, and the app file stays offline and self-contained."""

import json
import re

import pytest

import wheellib
from conftest import HTML_PATH, template_paths


@pytest.mark.parametrize("path", template_paths())
def test_dump_load_is_byte_identical(path, tmp_path):
    with open(path, encoding="utf-8") as f:
        original = f.read()
    out = tmp_path / "copy.json"
    wheellib.dump_wheel(wheellib.load_wheel(path), str(out))
    assert out.read_text("utf-8") == original


def test_unknown_fields_survive(tmp_path, research_wheel):
    research_wheel["events"][0]["owner"] = "Åsa Öberg"
    research_wheel["changelog"].append({"timestamp": "2027-01-01T00:00:00Z", "eventId": "x", "action": "moved",
                                        "before": {"start": "2027-01-01"}, "after": {"start": "2027-01-02"},
                                        "reason": "Krock med konferens"})
    out = tmp_path / "w.json"
    wheellib.dump_wheel(research_wheel, str(out))
    assert json.loads(out.read_text("utf-8")) == research_wheel
    assert "Åsa" in out.read_text("utf-8")  # written as UTF-8, not escaped


@pytest.fixture(scope="module")
def html():
    with open(HTML_PATH, encoding="utf-8") as f:
        return f.read()


def test_html_has_no_external_resources(html):
    assert not re.search(r"<(script|link|img|iframe)[^>]+(src|href)\s*=\s*[\"']?(https?:)?//", html, re.I)
    assert "@import" not in html
    assert not re.search(r"\bfetch\s*\(|XMLHttpRequest|WebSocket|navigator\.sendBeacon", html)


def test_html_is_single_file(html):
    assert html.lstrip().lower().startswith("<!doctype html>")
    assert not re.search(r"<script[^>]+src=", html, re.I)
    assert not re.search(r"<link[^>]+stylesheet", html, re.I)


def test_no_em_dashes_in_ui_and_docs():
    import pathlib
    root = pathlib.Path(HTML_PATH).parent
    files = [root / "yearwheel.html", root / "README.md", root / "CLAUDE.md"] + list((root / "templates").glob("*.json"))
    offenders = [str(p) for p in files if chr(0x2014) in p.read_text("utf-8")]
    assert offenders == []
