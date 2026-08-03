#!/usr/bin/env python3
"""Normalize prose sources into per-source UTF-8 text plus a manifest."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

SUPPORTED = {".txt", ".md", ".markdown", ".rst", ".adoc", ".html", ".htm", ".rtf", ".epub", ".docx"}
CHAPTER_RE = re.compile(
    r"(?im)^\s*(?:#{1,6}\s*)?(?:chapter\s+(?:\d+|[ivxlcdm]+)|第[零〇一二三四五六七八九十百千万两\d]+[章节回卷部篇]|序章|楔子|尾声|终章)(?:\b|\s*)[^\n]*"
)


def read_text(path: Path) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "big5", "utf-16"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def strip_markup(value: str) -> str:
    value = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", value)
    value = re.sub(r"(?s)<[^>]+>", "\n", value)
    return html.unescape(value)


def extract_docx(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    paragraphs = []
    for paragraph in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
        paragraphs.append("".join(node.text or "" for node in paragraph.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")))
    return "\n".join(paragraphs)


def extract_epub(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        names = sorted(name for name in archive.namelist() if name.lower().endswith((".xhtml", ".html", ".htm")))
        return "\n\n".join(strip_markup(archive.read(name).decode("utf-8", errors="replace")) for name in names)


def extract(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return extract_docx(path)
    if suffix == ".epub":
        return extract_epub(path)
    value = read_text(path)
    if suffix in {".html", ".htm"}:
        value = strip_markup(value)
    if suffix == ".rtf":
        value = re.sub(r"\\'[0-9a-fA-F]{2}|\\[a-zA-Z]+-?\d* ?|[{}]", "", value)
    return value.replace("\r\n", "\n").replace("\r", "\n")


def discover(inputs: list[str]) -> list[Path]:
    found = []
    for raw in inputs:
        path = Path(raw)
        candidates = path.rglob("*") if path.is_dir() else [path]
        found.extend(candidate.resolve() for candidate in candidates if candidate.is_file() and candidate.suffix.lower() in SUPPORTED)
    return sorted(set(found))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest = {"sources": [], "warnings": []}
    for index, path in enumerate(discover(args.inputs), 1):
        text = extract(path)
        digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]
        source_id = f"book-{index:02d}-{digest}"
        target = output / f"{source_id}.txt"
        target.write_text(text, encoding="utf-8")
        headings = [match.group(0).strip() for match in CHAPTER_RE.finditer(text)]
        manifest["sources"].append({
            "source_id": source_id,
            "filename": path.name,
            "format": path.suffix.lower(),
            "normalized_path": str(target),
            "characters": len(text),
            "chapter_headings": headings,
            "chapter_detection_confidence": "high" if len(headings) >= 3 else "low",
        })
        if len(headings) < 3:
            manifest["warnings"].append(f"{source_id}: fewer than three recognizable chapter headings")
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"sources": len(manifest["sources"]), "manifest": str(output / "manifest.json")}, ensure_ascii=False))
    return 0 if manifest["sources"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
