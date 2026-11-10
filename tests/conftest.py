# Year Wheel. Copyright (c) 2026 Robert Tomkowski <rtom@kth.se>
# MIT License (see the LICENSE file). Developed with the assistance of Claude Code (Anthropic).

import copy
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

FIXTURES = os.path.join(ROOT, "tests", "fixtures")
TEMPLATE_DIR = os.path.join(ROOT, "templates")
HTML_PATH = os.path.join(ROOT, "yearwheel.html")


def template_paths():
    return sorted(os.path.join(TEMPLATE_DIR, f) for f in os.listdir(TEMPLATE_DIR) if f.endswith(".json"))


@pytest.fixture
def research_wheel():
    with open(os.path.join(TEMPLATE_DIR, "research-team.json"), encoding="utf-8") as f:
        return copy.deepcopy(json.load(f))


def fixture_text(name):
    with open(os.path.join(FIXTURES, name), encoding="utf-8", newline="") as f:
        return f.read()
