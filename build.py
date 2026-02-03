#!/usr/bin/env python3
from pathlib import Path
import re

root = Path(__file__).resolve().parent
sections_dir = root / "sections"
template_path = root / "index.template.html"
output_path = root / "index.html"
build_log_source = sections_dir / "build-log.html"
build_log_output = root / "build-log.html"

html = template_path.read_text()

pattern = re.compile(r"\{\{section:([a-zA-Z0-9_-]+)\}\}")

def replace(match):
    section_id = match.group(1)
    section_file = sections_dir / f"{section_id}.html"
    if not section_file.exists():
        raise SystemExit(f"Missing section file: {section_file}")
    return section_file.read_text().rstrip()

html = pattern.sub(replace, html)
output_path.write_text(html)
if build_log_source.exists():
    build_log_output.write_text(build_log_source.read_text())
print(f"Wrote {output_path}")
