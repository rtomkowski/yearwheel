# Year Wheel. Copyright (c) 2026 Robert Tomkowski <rtom@kth.se>
# MIT License (see the LICENSE file). Developed with the assistance of Claude Code (Anthropic).

"""Build the static website in website/ (published with GitHub Pages).

Usage: python tools/build_site.py      (run tools/build_release.py first for fresh screenshots)

Needs pandoc for the online guide. Output:
  website/index.html          landing page (from docs/site/index.html)
  website/guide.html          the user guide as a web page (from docs/user-guide.md)
  website/app/yearwheel.html  the app with the site menu added at the top
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

# Added to the website copies of the app (not the download): the site menu above the app's own
# toolbar, so Home, Guide and Download stay one click away. Hidden when printing.
SITE_BAR_STYLE = """
<style>
.sitebar { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; flex: none;
  padding: 4px 16px; background: #102a43; color: #fff; font-size: 13.5px; }
.sitebar .sb-brand { display: flex; align-items: center; gap: 8px; color: #fff; text-decoration: none; font-weight: 700; }
.sitebar nav { margin-left: auto; display: flex; gap: 2px; flex-wrap: wrap; }
.sitebar nav a { color: #d6e4f2; text-decoration: none; padding: 3px 9px; border-radius: 6px; }
.sitebar nav a:hover, .sitebar nav a[aria-current] { background: rgba(255,255,255,.12); color: #fff; }
.sitebar a:focus-visible { outline: 2px solid #8ab4f8; outline-offset: 1px; }
#wheel { max-height: calc(100vh - 104px); }
@media print { .sitebar { display: none !important; } }
</style>
"""

SITE_BAR = """
<div class="sitebar"><a class="sb-brand" href="../"><svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="10" fill="none" stroke="#56B4E9" stroke-width="2"/><circle cx="12" cy="12" r="5" fill="none" stroke="#E69F00" stroke-width="2"/><path d="M12 2v5M12 17v5M2 12h5M17 12h5" stroke="#fff" stroke-width="2"/></svg>Year Wheel</a>
  <nav aria-label="Site">
    <a href="../">Home</a>
    <a href="../guide.html">Guide</a>
    <a href="yearwheel.html"%s>App</a>
    <a href="demo.html"%s>Demo</a>
    <a href="https://github.com/rtomkowski/yearwheel/releases/latest">Download</a>
    <a href="https://github.com/rtomkowski/yearwheel">GitHub</a>
  </nav>
</div>
"""


def with_site_bar(app, page):
    """The app with the site menu added at the top of the page; page is 'app' or 'demo'."""
    cur = ' aria-current="page"'
    bar = SITE_BAR % (cur if page == "app" else "", cur if page == "demo" else "")
    app = app.replace("</head>", SITE_BAR_STYLE + "</head>", 1)
    return app.replace("<body>", "<body>" + bar, 1)


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
        f.write(with_site_bar(app, "app"))
    with open(DEMO, encoding="utf-8") as f:
        demo = json.load(f)
    with open(os.path.join(OUT, "app", "demo.html"), "w", encoding="utf-8") as f:
        f.write(with_site_bar(app, "demo").replace("</body>", DEMO_SCRIPT % json.dumps(demo, ensure_ascii=False) + "</body>"))

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
