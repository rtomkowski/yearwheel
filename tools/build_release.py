# Year Wheel. Copyright (c) 2026 Robert Tomkowski <rtom@kth.se>
# MIT License (see the LICENSE file). Developed with the assistance of Claude Code (Anthropic).

"""Build the package for colleagues: screenshots, user guide PDF, poster and a ZIP file.

Usage: python tools/build_release.py [--skip-shots]

Needs Google Chrome (or Chromium/Edge) for screenshots and PDFs, and pandoc for the guide.
Outputs:
  docs/images/*.png                 screenshots of the demo wheel (used by the guide and poster)
  dist/Year-Wheel-User-Guide.pdf    from docs/user-guide.md
  dist/Year-Wheel-Poster.png/.pdf   from docs/poster.html
  dist/Year-Wheel.zip               yearwheel.html, demo wheel, guide PDF and poster
"""

import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wheellib import ROOT  # noqa: E402

DEMO = os.path.join(ROOT, "examples", "demo-department-2026-27.json")
DOCS = os.path.join(ROOT, "docs")
IMAGES = os.path.join(DOCS, "images")
DIST = os.path.join(ROOT, "dist")
TODAY = "2026-11-10"  # fixed "today" so screenshots are the same on every build

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "google-chrome", "chromium", "chromium-browser", "msedge",
]

# Each screenshot: (file name, mode, window width, window height)
SHOTS = [
    ("wheel.png", "wheel", 1600, 1000),
    ("editor.png", "editor", 1600, 1000),
    ("list.png", "list", 1600, 1000),
    ("review.png", "review", 1600, 1000),
    ("settings.png", "settings", 1600, 1000),
    ("wheel-only.png", "wheelonly", 1400, 1080),
]

# Appended to a temporary copy of the app: loads the demo wheel and opens the view for a screenshot.
SHOT_SCRIPT = """
<style>
  body.wheelonly .bar, body.wheelonly .banner { display: none !important; }
  body.wheelonly, body.wheelonly #wheelView { background: #fff; }
  body.wheelonly #wheelView { padding: 0; }
  body.wheelonly #wheel { max-height: none; height: 100vh; }
  body.noring *:focus, body.noring *:focus-visible { outline: none !important; }
</style>
<script>
(function () {
  const mode = location.hash.slice(1) || 'wheel';
  document.documentElement.setAttribute('data-theme', 'light');
  lang = 'en'; applyI18n();
  loadText(JSON.stringify(%s), 'demo-department-2026-27.json', null);
  state.dirty = false; updateHeader();
  if (mode === 'editor') openEditor('writing-retreat');
  if (mode === 'list') setView('list');
  if (mode === 'review') startReview();
  if (mode === 'settings') openDrawer('settings');
  if (mode === 'wheelonly') { document.body.classList.add('wheelonly'); renderWheel(); }
  if (mode !== 'editor') document.body.classList.add('noring');
})();
</script>
"""


def find_chrome():
    for c in CHROME_CANDIDATES:
        path = c if os.path.isabs(c) else shutil.which(c)
        if path and os.path.exists(path):
            return path
    raise SystemExit("Chrome, Chromium or Edge is needed to build screenshots and PDFs.")


def chrome(chrome_path, args):
    base = [chrome_path, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
            "--no-default-browser-check", "--virtual-time-budget=3000"]
    res = subprocess.run(base + args, capture_output=True, text=True, timeout=120)
    if res.returncode != 0:
        raise SystemExit("Chrome failed: %s" % res.stderr[-500:])


def file_url(path):
    return "file://" + path.replace(" ", "%20")


def build_shots(chrome_path, tmp):
    with open(os.path.join(ROOT, "yearwheel.html"), encoding="utf-8") as f:
        html = f.read()
    with open(DEMO, encoding="utf-8") as f:
        demo = json.load(f)
    page = os.path.join(tmp, "shot.html")
    with open(page, "w", encoding="utf-8") as f:
        f.write(html.replace("</body>", SHOT_SCRIPT % json.dumps(demo) + "</body>"))
    os.makedirs(IMAGES, exist_ok=True)
    for name, mode, w, h in SHOTS:
        out = os.path.join(IMAGES, name)
        chrome(chrome_path, ["--force-device-scale-factor=2", "--window-size=%d,%d" % (w, h),
                             "--screenshot=" + out, file_url(page) + "?today=" + TODAY + "#" + mode])
        print("screenshot docs/images/%s" % name)


def build_guide(chrome_path, tmp):
    if not shutil.which("pandoc"):
        raise SystemExit("pandoc is needed to build the user guide PDF.")
    html = os.path.join(tmp, "guide.html")
    subprocess.run(["pandoc", os.path.join(DOCS, "user-guide.md"), "-s", "--embed-resources",
                    "--resource-path=" + DOCS, "--css=" + os.path.join(DOCS, "guide.css"),
                    "--metadata", "pagetitle=Year Wheel: user guide", "-o", html], check=True)
    out = os.path.join(DIST, "Year-Wheel-User-Guide.pdf")
    chrome(chrome_path, ["--no-pdf-header-footer", "--print-to-pdf=" + out, file_url(html)])
    print("wrote dist/Year-Wheel-User-Guide.pdf")


def build_poster(chrome_path, tmp):
    src = os.path.join(DOCS, "poster.html")
    page = os.path.join(tmp, "poster.html")
    shutil.copy(src, page)
    shutil.copytree(IMAGES, os.path.join(tmp, "images"), dirs_exist_ok=True)
    chrome(chrome_path, ["--force-device-scale-factor=3", "--window-size=794,1123",
                         "--screenshot=" + os.path.join(DIST, "Year-Wheel-Poster.png"), file_url(page)])
    chrome(chrome_path, ["--no-pdf-header-footer", "--print-to-pdf=" + os.path.join(DIST, "Year-Wheel-Poster.pdf"),
                         file_url(page)])
    print("wrote dist/Year-Wheel-Poster.png and .pdf")


def build_csv_template():
    """examples/year-wheel-import-template.csv, made by the app's own csvTemplate() (run in Node)."""
    node = shutil.which("node")
    out = os.path.join(ROOT, "examples", "year-wheel-import-template.csv")
    if not node:
        print("Node.js not found: keeping the existing examples/year-wheel-import-template.csv")
        return
    with open(os.path.join(ROOT, "yearwheel.html"), encoding="utf-8") as f:
        html = f.read()
    block = re.search(r"/\*PARSERS-BEGIN\*/(.*?)/\*PARSERS-END\*/", html, re.S).group(1)
    res = subprocess.run([node, "-e", block + "\nprocess.stdout.write(csvTemplate());"], capture_output=True, timeout=60)
    if res.returncode != 0:
        raise SystemExit("Could not build the CSV template: %s" % res.stderr.decode()[-300:])
    with open(out, "wb") as f:
        f.write(res.stdout)
    print("wrote examples/year-wheel-import-template.csv")


def build_zip():
    out = os.path.join(DIST, "Year-Wheel.zip")
    files = [
        (os.path.join(ROOT, "yearwheel.html"), "yearwheel.html"),
        (DEMO, "demo-department-2026-27.json"),
        (os.path.join(ROOT, "examples", "year-wheel-import-template.csv"), "year-wheel-import-template.csv"),
        (os.path.join(DIST, "Year-Wheel-User-Guide.pdf"), "Year-Wheel-User-Guide.pdf"),
        (os.path.join(DIST, "Year-Wheel-Poster.png"), "Year-Wheel-Poster.png"),
        (os.path.join(DIST, "Year-Wheel-Poster.pdf"), "Year-Wheel-Poster.pdf"),
        (os.path.join(DOCS, "START-HERE.txt"), "START-HERE.txt"),
        (os.path.join(ROOT, "LICENSE"), "LICENSE.txt"),
    ]
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for src, name in files:
            z.write(src, "Year Wheel/" + name)
    print("wrote dist/Year-Wheel.zip (%.1f MB)" % (os.path.getsize(out) / 1e6))


def main(argv):
    chrome_path = find_chrome()
    os.makedirs(DIST, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="yearwheel-")
    try:
        if "--skip-shots" not in argv:
            build_shots(chrome_path, tmp)
        if "--shots-only" in argv:
            return 0
        build_csv_template()
        build_guide(chrome_path, tmp)
        build_poster(chrome_path, tmp)
        build_zip()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
