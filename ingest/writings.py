"""Writings: ``content/writings/index.yaml`` path list plus Markdown files on disk.

``WritingsIndex`` is YAML-only. ``load_writings_articles`` reads files,
renders Markdown to HTML, and builds slugs/titles/hrefs for the site.
"""

import re
from pathlib import Path

import markdown
from pydantic import BaseModel, ConfigDict, Field


class WritingsIndex(BaseModel):
    """Ordered list of Markdown paths (repo-root relative); each file becomes a writings page."""

    model_config = ConfigDict(extra="forbid")

    paths: list[str] = Field(default_factory=list)


def parse_writings_index(data: dict) -> WritingsIndex:
    """Validate writings index YAML dict (default: ``content/writings/index.yaml``)."""

    return WritingsIndex.model_validate(data)


def render_markdown(source: str) -> str:
    """Markdown → HTML fragment (for README embed and writings)."""

    md = markdown.Markdown(
        extensions=[
            "fenced_code",
            "tables",
            "nl2br",
            "sane_lists",
        ]
    )
    return md.convert(source)


_ATX_H1 = re.compile(r"^#\s+(?P<title>.+?)\s*$")


def title_from_markdown(source: str, fallback: str) -> str:
    for line in source.splitlines():
        s = line.strip()
        m = _ATX_H1.match(s)
        if m:
            return m.group("title").strip()
    return fallback


def strip_leading_atx_h1(source: str) -> str:
    """Remove a single top-level # heading so the page masthead can own the title."""

    lines = source.splitlines()
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i < len(lines) and _ATX_H1.match(lines[i].strip()):
        return "\n".join(lines[i + 1 :]).lstrip("\n")
    return source


def load_writings_articles(root: Path, writings_index: WritingsIndex) -> list[dict]:
    """One dict per index path: ``slug``, ``title``, ``href``, ``source_path``, ``body_html``.

    ``slug`` from filename stem; ``title`` from first ATX ``#`` line or a fallback;
    ``body_html`` from Markdown after stripping that leading H1; ``href`` is relative
    to ``writings/index.html``.
    """

    articles: list[dict] = []
    for rel in writings_index.paths:
        src = (root / rel).resolve()
        if not src.is_file():
            raise FileNotFoundError(f"writings path not found: {rel}")
        text = src.read_text()
        slug = src.stem
        fallback_title = slug.replace("-", " ").replace("_", " ").title()
        title = title_from_markdown(text, fallback_title)
        body_md = strip_leading_atx_h1(text)
        body_html = render_markdown(body_md)
        articles.append(
            {
                "slug": slug,
                "title": title,
                "href": f"{slug}/index.html",
                "source_path": rel,
                "body_html": body_html,
            }
        )
    return articles

