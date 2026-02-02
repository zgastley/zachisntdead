#!/usr/bin/env python3
"""Instagram → site import (Phase 1).

This is intentionally a small, repo-local tool.

Phase 1 goals:
- Sync recent IG media metadata into instagram/cache.json
- Maintain a repo-tracked curation file instagram/curation.yaml
- For approved posts:
  - download images locally (assets/instagram/...)
  - generate markdown stubs routed into art/music/projects/etc
  - for videos: default to IG embed

Auth model:
- Use IG Graph API (Creator/Business linked to FB page)
- Read token + IG user id from env vars:
  - IG_GRAPH_ACCESS_TOKEN
  - IG_GRAPH_IG_USER_ID

(We'll wire 1Password later.)
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent
INSTAGRAM_DIR = ROOT / "instagram"
CACHE_PATH = INSTAGRAM_DIR / "cache.json"
CURATION_PATH = INSTAGRAM_DIR / "curation.yaml"
ASSETS_DIR = ROOT / "assets" / "instagram"
MARKDOWN_DIR = ROOT / "markdown"

GRAPH_BASE = "https://graph.facebook.com/v19.0"


def sh(*args: str, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        check=check,
        text=True,
        capture_output=capture,
    )


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required env var: {name}")
    return value


def safe_slug(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "post"


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "posts": []}
    return yaml.safe_load(path.read_text()) or {"version": 1, "posts": []}


def save_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))


def graph_get(endpoint: str, params: dict[str, str]) -> dict[str, Any]:
    # Use curl to keep dependencies minimal and debugging easy.
    import urllib.parse

    qs = urllib.parse.urlencode(params)
    url = f"{GRAPH_BASE}{endpoint}?{qs}"
    out = sh("curl", "-sS", url, capture=True).stdout
    data = json.loads(out)
    if isinstance(data, dict) and data.get("error"):
        raise SystemExit(f"Graph API error: {data['error']}")
    return data


@dataclass
class CuratedPost:
    id: str
    publish: bool
    section: str
    title: str | None = None
    summary: str | None = None
    media_mode: str = "download"  # download|embed|link


def load_curation() -> list[CuratedPost]:
    raw = load_yaml(CURATION_PATH)
    posts = raw.get("posts", []) or []
    out: list[CuratedPost] = []
    for p in posts:
        out.append(
            CuratedPost(
                id=str(p.get("id")),
                publish=bool(p.get("publish", False)),
                section=str(p.get("section", "art")),
                title=p.get("title"),
                summary=p.get("summary"),
                media_mode=str((p.get("media") or {}).get("mode", "download")),
            )
        )
    return out


def write_curation(posts: list[CuratedPost]) -> None:
    save_yaml(
        CURATION_PATH,
        {
            "version": 1,
            "posts": [
                {
                    "id": p.id,
                    "publish": p.publish,
                    "section": p.section,
                    **({"title": p.title} if p.title else {}),
                    **({"summary": p.summary} if p.summary else {}),
                    "media": {"mode": p.media_mode},
                }
                for p in posts
            ],
        },
    )


def cmd_sync(_: argparse.Namespace) -> None:
    token = require_env("IG_GRAPH_ACCESS_TOKEN")
    ig_user_id = require_env("IG_GRAPH_IG_USER_ID")

    fields = "id,caption,media_type,media_url,permalink,timestamp,thumbnail_url,children{media_type,media_url,thumbnail_url}"
    data: dict[str, Any] = graph_get(
        f"/{ig_user_id}/media",
        {"access_token": token, "fields": fields, "limit": "50"},
    )

    INSTAGRAM_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {CACHE_PATH}")


def cmd_curate(args: argparse.Namespace) -> None:
    if not CACHE_PATH.exists():
        raise SystemExit("Missing instagram/cache.json. Run: python instagram_sync.py sync")

    cache = json.loads(CACHE_PATH.read_text())
    items: list[dict[str, Any]] = cache.get("data", []) or []

    existing = {p.id: p for p in load_curation()}

    print("Recent Instagram posts:\n")
    curated: list[CuratedPost] = []

    for idx, item in enumerate(items, start=1):
        media_id = str(item.get("id", ""))
        caption = (item.get("caption") or "").strip().replace("\n", " ")
        caption_preview = (caption[:100] + "…") if len(caption) > 100 else caption
        media_type = item.get("media_type")
        permalink = item.get("permalink")

        prev = existing.get(media_id)
        default_publish = prev.publish if prev else False
        default_section = prev.section if prev else "art"

        print(f"{idx}. {media_type} {media_id}")
        print(f"   {caption_preview}")
        print(f"   {permalink}")

        if args.non_interactive:
            # Keep existing decisions only.
            if prev:
                curated.append(prev)
            continue

        yn = input(f"   Publish? [{'Y' if default_publish else 'n'}] ").strip().lower()
        publish = default_publish if yn == "" else yn in {"y", "yes"}

        section = default_section
        if publish:
            sec = input("   Section (art/music/projects/field-notes) [art]: ").strip().lower() or default_section
            if sec not in {"art", "music", "projects", "field-notes"}:
                print("   (invalid section; using art)")
                sec = "art"
            section = sec

        media_mode = prev.media_mode if prev else ("embed" if media_type in {"VIDEO"} else "download")
        if publish:
            mm = input(f"   Media mode (download/embed/link) [{media_mode}]: ").strip().lower() or media_mode
            if mm not in {"download", "embed", "link"}:
                mm = media_mode
            media_mode = mm

        curated.append(
            CuratedPost(
                id=media_id,
                publish=publish,
                section=section,
                title=prev.title if prev else None,
                summary=prev.summary if prev else None,
                media_mode=media_mode,
            )
        )
        print("")

    write_curation(curated)
    print(f"Updated {CURATION_PATH}")

    if args.auto_commit:
        sh("git", "add", str(CURATION_PATH))
        # Commit may fail if nothing changed.
        sh("git", "commit", "-m", "Update Instagram curation", check=False)
        print("Committed curation (if changed).")


def markdown_front_matter(*, title: str, date: str, section: str, summary: str) -> str:
    return "\n".join(
        [
            f"title: {title}",
            f"date: {date}",
            f"section: {section}",
            "type: single",
            "label: Field Notes" if section == "field-notes" else section.title(),
            f"summary: {summary}",
            "post-to-site: true",
            "",
        ]
    )


def cmd_build(_: argparse.Namespace) -> None:
    if not CACHE_PATH.exists():
        raise SystemExit("Missing instagram/cache.json. Run: python instagram_sync.py sync")

    cache = json.loads(CACHE_PATH.read_text())
    by_id = {str(item.get("id")): item for item in (cache.get("data", []) or [])}

    curated = [p for p in load_curation() if p.publish]
    if not curated:
        print("No curated posts marked publish:true")
        return

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    MARKDOWN_DIR.mkdir(parents=True, exist_ok=True)

    today = dt.date.today().isoformat()

    written = 0
    for p in curated:
        item = by_id.get(p.id)
        if not item:
            print(f"Skipping {p.id}: not found in cache")
            continue

        caption = (item.get("caption") or "").strip()
        media_type = item.get("media_type")
        permalink = item.get("permalink")

        title = p.title or (caption.split("\n", 1)[0][:60] if caption else f"Instagram Post {p.id}")
        summary = p.summary or (caption.split("\n", 1)[0][:120] if caption else "Imported from Instagram.")

        slug = safe_slug(f"ig-{p.id}-{title}")
        md_path = MARKDOWN_DIR / f"ig-{slug}.md"

        body_lines: list[str] = []
        body_lines.append(f"# {title}")
        body_lines.append("")

        if caption:
            body_lines.append(caption)
            body_lines.append("")

        if p.media_mode == "link":
            body_lines.append(f"Permalink: {permalink}")
            body_lines.append("")
        elif p.media_mode == "embed":
            # Raw HTML block; build_markdown.py will pass it through.
            body_lines.append(f'<blockquote class="instagram-media" data-instgrm-permalink="{permalink}" data-instgrm-version="14"></blockquote>')
            body_lines.append("")
        else:
            # download
            if media_type == "CAROUSEL_ALBUM" and item.get("children") and item["children"].get("data"):
                for idx, child in enumerate(item["children"]["data"], start=1):
                    url = child.get("media_url") or child.get("thumbnail_url")
                    if not url:
                        continue
                    out = ASSETS_DIR / f"{p.id}-{idx}.jpg"
                    sh("curl", "-L", "-sS", "-o", str(out), str(url))
                    body_lines.append(f"![]({out.relative_to(ROOT).as_posix()})")
                body_lines.append("")
            elif media_type == "VIDEO":
                # phase 1: embed for videos even in download mode
                body_lines.append(f'<blockquote class="instagram-media" data-instgrm-permalink="{permalink}" data-instgrm-version="14"></blockquote>')
                body_lines.append("")
            else:
                url = item.get("media_url")
                if url:
                    out = ASSETS_DIR / f"{p.id}.jpg"
                    sh("curl", "-L", "-sS", "-o", str(out), str(url))
                    body_lines.append(f"![]({out.relative_to(ROOT).as_posix()})")
                    body_lines.append("")

        fm = markdown_front_matter(title=title, date=today, section=p.section, summary=summary)
        md_path.write_text(fm + "\n".join(body_lines) + "\n")
        print(f"Wrote {md_path}")
        written += 1

    if written:
        sh("python", "build_markdown.py")
        sh("git", "add", "markdown", "posts", "assets/instagram")
        sh("git", "commit", "-m", f"Import curated Instagram posts ({today})", check=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_sync = sub.add_parser("sync", help="Fetch recent IG media into instagram/cache.json")
    p_sync.set_defaults(func=cmd_sync)

    p_curate = sub.add_parser("curate", help="Interactively update instagram/curation.yaml")
    p_curate.add_argument("--auto-commit", action="store_true", default=True)
    p_curate.add_argument("--non-interactive", action="store_true")
    p_curate.set_defaults(func=cmd_curate)

    p_build = sub.add_parser("build", help="Generate markdown + download media for curated posts")
    p_build.set_defaults(func=cmd_build)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
