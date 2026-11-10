# Year Wheel. Copyright (c) 2026 Robert Tomkowski <rtom@kth.se>
# MIT License (see the LICENSE file). Developed with the assistance of Claude Code (Anthropic).

"""Copy the public parts of this (private) repository into the public repository's folder.

Usage: python tools/export_public.py [TARGET]      (default TARGET: ../yearwheel)

Copies every file git knows about (committed or new, not ignored) except the paths in PRIVATE,
and removes files from TARGET that no longer exist here. TARGET's own .git folder is never
touched. Review and commit in TARGET afterwards; nothing is committed or pushed by this script.
"""

import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wheellib import ROOT  # noqa: E402

# Never published: release builds (they go to GitHub Releases), the internal email draft,
# and local editor settings.
PRIVATE = ("dist/", ".claude/")
PUBLIC_GITIGNORE_EXTRA = "\n# Release builds are attached to GitHub Releases, not committed\ndist/\n"


def tracked_files():
    out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
                         cwd=ROOT, capture_output=True, check=True).stdout.decode("utf-8")
    return sorted(f for f in out.split("\0") if f and not f.startswith(PRIVATE) and os.path.isfile(os.path.join(ROOT, f)))


def main(argv):
    target = os.path.abspath(argv[0] if argv else os.path.join(os.path.dirname(ROOT), "yearwheel"))
    os.makedirs(target, exist_ok=True)
    files = tracked_files()
    wanted = set(files)
    for rel in files:
        dst = os.path.join(target, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(os.path.join(ROOT, rel), dst)
    with open(os.path.join(target, ".gitignore"), "a", encoding="utf-8") as f:
        f.write(PUBLIC_GITIGNORE_EXTRA)
    removed = 0
    for d, dirs, fs in os.walk(target):
        if ".git" in dirs:
            dirs.remove(".git")
        for name in fs:
            rel = os.path.relpath(os.path.join(d, name), target).replace(os.sep, "/")
            if rel not in wanted and rel != ".gitignore":
                os.remove(os.path.join(d, name))
                removed += 1
    print("copied %d files to %s (%d old files removed)" % (len(files), target, removed))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
