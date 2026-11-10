# Year Wheel. Copyright (c) 2026 Robert Tomkowski <rtom@kth.se>
# MIT License (see the LICENSE file). Developed with the assistance of Claude Code (Anthropic).

"""Build the static website in website/ (published with GitHub Pages).

Usage: python tools/build_site.py      (run tools/build_release.py first for fresh screenshots)

Needs pandoc for the online guide. Output:
  website/index.html          landing page (from docs/site/index.html)
  website/guide.html          the user guide as a web page (from docs/user-guide.md)
  website/app/yearwheel.html  the app, unchanged
  website/app/demo.html       the app with the fictional demo wheel loaded on start
  website/images/             screenshots
  website/downloads/          demo wheel and CSV import template
Large files (ZIP, guide PDF, poster PDF) are attached to GitHub Releases instead.
"""

import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wheellib import ROOT  # noqa: E402

SITE_SRC = os.path.join(ROOT, "docs", "site")
OUT = os.path.join(ROOT, "website")
DEMO = os.path.join(ROOT, "examples", "demo-department-2026-27.json")
TEMPLATE_CSV = os.path.join(ROOT, "examples", "year-wheel-import-template.csv")

# Appended to the app for demo.html: open the demo wheel when the page loads (no network request).
DEMO_SCRIPT = """
<script>
(function () {
  try {
    loadText(JSON.stringify(%s), 'demo-department-2026-27.json', null);
    state.dirty = false; updateHeader();
    flash(t('demoNote'));
  } catch (e) { /* the empty app still works */ }
})();
</script>
"""


def main():
    if not shutil.which("pandoc"):
        raise SystemExit("pandoc is needed to build the online guide.")
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    for sub in ("app", "images", "downloads"):
        os.makedirs(os.path.join(OUT, sub))

    shutil.copy(os.path.join(SITE_SRC, "index.html"), OUT)
    shutil.copy(os.path.join(SITE_SRC, "site.css"), OUT)
    open(os.path.join(OUT, ".nojekyll"), "w").close()  # serve files as they are

    for name in sorted(os.listdir(os.path.join(ROOT, "docs", "images"))):
        if name.endswith(".png"):
            shutil.copy(os.path.join(ROOT, "docs", "images", name), os.path.join(OUT, "images"))

    with open(os.path.join(ROOT, "yearwheel.html"), encoding="utf-8") as f:
        app = f.read()
    with open(os.path.join(OUT, "app", "yearwheel.html"), "w", encoding="utf-8") as f:
        f.write(app)
    with open(DEMO, encoding="utf-8") as f:
        demo = json.load(f)
    with open(os.path.join(OUT, "app", "demo.html"), "w", encoding="utf-8") as f:
        f.write(app.replace("</body>", DEMO_SCRIPT % json.dumps(demo, ensure_ascii=False) + "</body>"))

    shutil.copy(DEMO, os.path.join(OUT, "downloads"))
    shutil.copy(TEMPLATE_CSV, os.path.join(OUT, "downloads"))

    subprocess.run([
        "pandoc", os.path.join(ROOT, "docs", "user-guide.md"), "-s", "-o", os.path.join(OUT, "guide.html"),
        "--css=site.css",  # with --css pandoc leaves out its own page styling
        "--include-in-header=" + os.path.join(SITE_SRC, "guide-head.html"),
        "--include-before-body=" + os.path.join(SITE_SRC, "guide-header.html"),
        "--include-after-body=" + os.path.join(SITE_SRC, "guide-footer.html"),
        "--metadata=pagetitle:Year Wheel: user guide", "--metadata=lang:en",
    ], check=True)

    total = sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(OUT) for f in fs)
    print("built website/ (%.1f MB)" % (total / 1e6))
    return 0


if __name__ == "__main__":
    sys.exit(main())
