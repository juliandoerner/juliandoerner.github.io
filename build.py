#!/usr/bin/env python3
"""
Build script: reads src/pages/*.html, injects them into src/template.html,
writes finished pages to docs/.

To build locally:
    python build.py

Each page in src/pages/ starts with a front matter block:
    ---
    title: Page Title
    ---
    <p>Content goes here...</p>
"""

import tomllib
import shutil
from datetime import date
from pathlib import Path

# ── Site-wide settings (edit config.toml, not here) ──────────────────────────
with open("config.toml", "rb") as _f:
    _cfg = tomllib.load(_f)

SITE_NAME     = _cfg["site_name"]
SITE_SUBTITLE = _cfg["site_subtitle"]
NAV_ITEMS     = [( item["href"], item["label"] ) for item in _cfg["nav"]]

# ── Paths ─────────────────────────────────────────────────────────────────────
SRC_DIR    = Path("src")
PAGES_DIR  = SRC_DIR / "pages"
TEMPLATE   = SRC_DIR / "template.html"
OUTPUT_DIR = Path("docs")

# ── Helpers ───────────────────────────────────────────────────────────────────

def parse_front_matter(text):
    """Split '---\\ntitle: X\\n---\\n<content>' into (meta dict, content str)."""
    if not text.startswith("---"):
        return {}, text
    end = text.index("---", 3)
    front = text[3:end].strip()
    content = text[end + 3:].strip()
    meta = {}
    for line in front.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, content


def build_nav(current_file):
    parts = []
    for href, label in NAV_ITEMS:
        if href == current_file:
            parts.append(f'<a href="{href}" aria-current="page">{label}</a>')
        else:
            parts.append(f'<a href="{href}">{label}</a>')
    return "\n  ".join(parts)


# ── Build ─────────────────────────────────────────────────────────────────────

def build():
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Copy everything in src/ that is not the template or the pages/ directory.
    for asset in SRC_DIR.iterdir():
        if asset.name in ("template.html", "pages"):
            continue
        if asset.is_dir():
            shutil.copytree(asset, OUTPUT_DIR / asset.name, dirs_exist_ok=True)
        else:
            shutil.copy(asset, OUTPUT_DIR / asset.name)

    template = TEMPLATE.read_text(encoding="utf-8")
    today    = date.today().strftime("%B %Y")

    for page_file in sorted(PAGES_DIR.glob("*.html")):
        meta, content = parse_front_matter(page_file.read_text(encoding="utf-8"))

        page_title = meta.get("title", "")
        full_title = (SITE_NAME if page_file.name == "index.html"
                      else f"{page_title} — {SITE_NAME}")

        html = (template
                .replace("{{title}}",       full_title)
                .replace("{{site_name}}",   SITE_NAME)
                .replace("{{site_subtitle}}", SITE_SUBTITLE)
                .replace("{{nav}}",         build_nav(page_file.name))
                .replace("{{content}}",     content)
                .replace("{{date}}",        today))

        out = OUTPUT_DIR / page_file.name
        out.write_text(html, encoding="utf-8")
        print(f"  {page_file.name}")

    print(f"Done → {OUTPUT_DIR}/")


if __name__ == "__main__":
    print("Building…")
    build()
