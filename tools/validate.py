# Year Wheel. Copyright (c) 2026 Robert Tomkowski <rtom@kth.se>
# MIT License (see the LICENSE file). Developed with the assistance of Claude Code (Anthropic).

"""Validate one or more Year Wheel JSON files.

Usage: python tools/validate.py templates/*.json my-wheel.json
Exit code 0 when all files are valid, 1 otherwise.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wheellib import full_check, load_wheel  # noqa: E402


def main(argv):
    if not argv:
        print(__doc__.strip())
        return 2
    bad = 0
    for path in argv:
        try:
            errors = full_check(load_wheel(path))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors = [str(exc)]
        if errors:
            bad += 1
            print("FAIL %s" % path)
            for e in errors:
                print("  - %s" % e)
        else:
            print("ok   %s" % path)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
