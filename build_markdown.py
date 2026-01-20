#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
MARKDOWN_DIR = ROOT / "markdown"
OUTPUT_DIR = ROOT / "posts"

SINGLE_TEMPLATE = (ROOT / "posts" / "art" / "_single-template.html").read_text()
GALLERY_TEMPLATE = (ROOT / "posts" / "art" / "_gallery-template.html").read_text()

IMAGE_RE = re.compile(r"^!\[(.*?)\]\((.*?)\)\s*$")
INLINE_CODE_RE = re.compile(r"`([^`]+)`")
ORDERED_LIST_RE = re.compile(r"^\s*\d+\.\s+(.*)$")
UNORDERED_LIST_RE = re.compile(r"^\s*[-*]\s+(.*)$")


@dataclass
class FrontMatter:
    title: str
    date: str
    section: str
    type: str
    label: str
    summary: str
    post_to_site: bool
    source: Path


def parse_front_matter(lines: list[str], source: Path) -> FrontMatter:
    data: dict[str, str] = {}
    for line in lines:
        if not line.strip() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip().lower()] = value.strip()

    return FrontMatter(
        title=data.get("title", "Untitled"),
        date=data.get("date", "YYYY-MM-DD"),
        section=data.get("section", "art"),
        type=data.get("type", "single"),
        label=data.get("label", ""),
        summary=data.get("summary", ""),
        post_to_site=data.get("post-to-site", "false").lower() in {"true", "yes", "1"},
        source=source,
    )


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", title.strip().lower())
    return slug.strip("-") or "post"


def extract_summary(lines: list[str]) -> str:
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or IMAGE_RE.match(line):
            continue
        return line
    return "New post."


def normalize_image_path(path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if path.startswith("/") or path.startswith("../"):
        return path
    return f"../../assets/{path}"


def thumb_for(path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if path.endswith("-thumb.png") or path.endswith("-thumb.jpg") or path.endswith("-thumb.jpeg"):
        return path
    if "." not in path:
        return path
    base, ext = path.rsplit(".", 1)
    return f"{base}-thumb.{ext}"


def split_gallery_and_body(lines: list[str], use_gallery: bool) -> tuple[list[tuple[str, str]], list[str]]:
    if not use_gallery:
        return [], lines

    cleaned = list(lines)
    index = 0
    # Skip leading blank lines
    while index < len(cleaned) and not cleaned[index].strip():
        index += 1
    # Skip a single leading H1
    if index < len(cleaned) and cleaned[index].strip().startswith("# "):
        index += 1
    # Skip blank lines after H1
    while index < len(cleaned) and not cleaned[index].strip():
        index += 1

    gallery_images: list[tuple[str, str]] = []
    block_start = index
    while index < len(cleaned):
        match = IMAGE_RE.match(cleaned[index].strip())
        if not match:
            break
        alt, path = match.groups()
        gallery_images.append((alt, path))
        index += 1
    if not gallery_images:
        return [], lines

    body = cleaned[:block_start] + cleaned[index:]
    return gallery_images, body


def format_inline_code(text: str) -> str:
    return INLINE_CODE_RE.sub(r"<code>\1</code>", text)


def markdown_to_html(lines: list[str]) -> str:
    html: list[str] = []
    image_run: list[tuple[str, str]] = []
    in_code_block = False
    list_mode: str | None = None

    def flush_images() -> None:
        nonlocal image_run
        if not image_run:
            return
        if len(image_run) >= 2:
            html.append("<div class=\"inline-gallery\">")
            for alt, path in image_run:
                src = normalize_image_path(path)
                html.append(f"  <img class=\"inline-image\" src=\"{src}\" alt=\"{alt}\" />")
            html.append("</div>")
        else:
            alt, path = image_run[0]
            src = normalize_image_path(path)
            html.append(f"<img class=\"inline-image\" src=\"{src}\" alt=\"{alt}\" />")
        image_run = []

    def close_list() -> None:
        nonlocal list_mode
        if list_mode == "ol":
            html.append("</ol>")
        elif list_mode == "ul":
            html.append("</ul>")
        list_mode = None

    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_images()
            close_list()
            if not in_code_block:
                html.append("<pre><code>")
                in_code_block = True
            else:
                html.append("</code></pre>")
                in_code_block = False
            continue

        if in_code_block:
            html.append(line)
            continue

        if not stripped:
            flush_images()
            close_list()
            html.append("")
            continue

        image_match = IMAGE_RE.match(stripped)
        if image_match:
            image_run.append(image_match.groups())
            continue

        flush_images()

        ordered_match = ORDERED_LIST_RE.match(stripped)
        unordered_match = UNORDERED_LIST_RE.match(stripped)
        if ordered_match or unordered_match:
            desired_mode = "ol" if ordered_match else "ul"
            if list_mode != desired_mode:
                close_list()
                html.append(f"<{desired_mode}>")
                list_mode = desired_mode
            item_text = ordered_match.group(1) if ordered_match else unordered_match.group(1)
            html.append(f"  <li>{format_inline_code(item_text.strip())}</li>")
            continue
        else:
            close_list()

        if stripped.startswith("## "):
            html.append(f"<h2>{format_inline_code(stripped[3:].strip())}</h2>")
            continue
        if stripped.startswith("# "):
            html.append(f"<h1>{format_inline_code(stripped[2:].strip())}</h1>")
            continue
        html.append(f"<p>{format_inline_code(stripped)}</p>")

    flush_images()
    close_list()

    output = []
    for line in html:
        output.append(line)
    return "\n".join(output)


def build_gallery_html(fm: FrontMatter, images: list[tuple[str, str]]) -> str:
    if not images:
        raise SystemExit(f"Gallery type requires images in {fm.source}")

    html = GALLERY_TEMPLATE
    html = html.replace("Art Series Title · Zach Isn't Dead", f"{fm.title} · Zach Isn't Dead")
    html = html.replace("Art Series Title", fm.title)
    html = html.replace("YYYY-MM-DD · Art", f"{fm.date} · {fm.section.title()}")

    main_alt, main_path = images[0]
    main_src = normalize_image_path(main_path)
    main_block = f'<img src="{main_src}" alt="{main_alt}" />'
    html = re.sub(
        r"<div class=\"gallery-main\">[\s\S]*?</div>",
        f"<div class=\"gallery-main\">\n            {main_block}\n          </div>",
        html,
    )

    thumbs = []
    for idx, (alt, path) in enumerate(images, start=1):
        full_src = normalize_image_path(path)
        thumb_src = normalize_image_path(thumb_for(path))
        thumbs.append(
            f'            <button class="gallery-thumb" type="button" data-full="{full_src}" '
            f'data-alt="{alt or f"Image {idx}"}" data-caption="">\n'
            f'              <img src="{thumb_src}" alt="Thumbnail {idx}." />\n'
            f'            </button>'
        )
    thumbs_html = "\n".join(thumbs)
    html = re.sub(
        r"<div class=\"gallery-thumbs\">[\s\S]*?</div>",
        f"<div class=\"gallery-thumbs\">\n{thumbs_html}\n          </div>",
        html,
    )

    return html


def build_single_html(fm: FrontMatter, images: list[tuple[str, str]]) -> str:
    html = SINGLE_TEMPLATE
    html = html.replace("Art Title · Zach Isn't Dead", f"{fm.title} · Zach Isn't Dead")
    html = html.replace("Art Title", fm.title)
    html = html.replace("YYYY-MM-DD · Art", f"{fm.date} · {fm.section.title()}")

    image_path = images[0][1] if images else "your-image.jpg"
    html = html.replace("../../assets/your-image.jpg", normalize_image_path(image_path))
    return html


def build_post(fm: FrontMatter, lines: list[str]) -> Path:
    gallery_images, body_lines = split_gallery_and_body(lines, fm.type == "gallery")
    content_html = markdown_to_html(body_lines)

    if fm.type == "gallery":
        html = build_gallery_html(fm, gallery_images)
    else:
        html = build_single_html(fm, gallery_images)

    html = re.sub(
        r"<section class=\"article\">[\s\S]*?</section>",
        f"<section class=\"article\">\n{content_html}\n        <a class=\"back-link\" href=\"../../index.html#{fm.section}\">← Back to {fm.section.title()}</a>\n      </section>",
        html,
        count=1,
    )

    out_dir = OUTPUT_DIR / fm.section
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{slugify(fm.title)}.html"
    out_file.write_text(html)
    print(f"Wrote {out_file}")
    return out_file


def rebuild_section_lists(entries: list[tuple[FrontMatter, Path, str]]) -> None:
    by_section: dict[str, list[tuple[FrontMatter, Path, str]]] = {}
    for fm, out_file, summary in entries:
        if not fm.post_to_site:
            continue
        by_section.setdefault(fm.section, []).append((fm, out_file, summary))

    for section, items in by_section.items():
        section_file = ROOT / "sections" / f"{section}.html"
        if not section_file.exists():
            continue
        html = section_file.read_text()
        if "<!-- md-posts:start -->" not in html or "<!-- md-posts:end -->" not in html:
            continue

        items.sort(key=lambda entry: entry[0].date, reverse=True)
        generated = []
        for fm, out_file, summary in items:
            href = f"posts/{fm.section}/{out_file.name}"
            meta = fm.label or fm.type.title()
            generated.append(
                "\n".join([
                    "    <article class=\"post-item\" data-origin=\"md\">",
                    f"      <div class=\"post-meta\">{meta}</div>",
                    f"      <h3><a class=\"content-link\" href=\"{href}\">{fm.title}</a></h3>",
                    f"      <p>{summary}</p>",
                    "    </article>",
                ])
            )

        generated_block = "\n".join(generated)
        html = re.sub(
            r"<!-- md-posts:start -->[\s\S]*?<!-- md-posts:end -->",
            f"<!-- md-posts:start -->\n{generated_block}\n    <!-- md-posts:end -->",
            html,
            count=1,
        )
        section_file.write_text(html)


def main() -> None:
    if not MARKDOWN_DIR.exists():
        print("No markdown directory found.")
        return

    entries: list[tuple[FrontMatter, Path, str]] = []
    for md_path in MARKDOWN_DIR.glob("*.md"):
        lines = md_path.read_text().split("\n")
        try:
            blank_index = lines.index("")
        except ValueError:
            raise SystemExit(f"Missing blank line after front matter in {md_path}")

        fm = parse_front_matter(lines[:blank_index], md_path)
        body_lines = lines[blank_index + 1 :]
        out_file = build_post(fm, body_lines)
        summary = fm.summary or extract_summary(body_lines)
        entries.append((fm, out_file, summary))

    rebuild_section_lists(entries)


if __name__ == "__main__":
    main()
