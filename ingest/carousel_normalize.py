"""View dicts for résumé **web-only** carousels: thin Jinja, branching in Python.

**Boundary with ``frontends.jinja.sections.resume``:** that module calls
``web_with_normalized_slides`` while assembling the Jinja root context (dates on
experience figure slides, ``section`` wrappers, etc.). This module only shapes
each slide into ``slides_normalized`` (table/deflist bodies, figure tweaks).
Print and non-web views ignore ``web`` / ``slides_normalized`` entirely (CSS
hides ``.resume-section-web``); ownership of “what is print” stays in templates
+ ``04_writings_print.css``, not here.

``slides_normalized`` is added beside YAML ``slides`` on each ``web`` block
(skills, education: list-intro slides; experience: figure+prose slides).
"""

from __future__ import annotations

from typing import Any, Literal

# Optional figure tweaks (was inline ``{% if slide.id == ... %}`` in Jinja).
FIGURE_STYLE_OVERRIDES: dict[str, str] = {
    "pendo": "--logo-scale: 1.08",
    "ncsu-overview": "--figure-width: 9rem",
}


def _figure_style(slide_id: str) -> str | None:
    return FIGURE_STYLE_OVERRIDES.get(slide_id)


def _list_body(slide: dict) -> dict[str, Any]:
    """Table or deflist body for ``SlideListIntro`` (after model_dump)."""

    items: list[dict] = list(slide.get("items") or [])
    if not items:
        return {"mode": "none"}

    first = items[0]
    if first.get("experience") is not None or first.get("favorite_feature") is not None:
        rows = [
            [
                str(it.get("name", "")),
                str(it.get("experience", "")),
                str(it.get("favorite_feature", "")),
            ]
            for it in items
        ]
        return {
            "mode": "table",
            "headers": ["Name", "Experience", "Favorite feature"],
            "rows": rows,
        }

    layout: Literal["deflist", "table"] = slide.get("items_layout") or "deflist"
    if layout == "table":
        cols: list[str] = list(slide.get("table_columns") or [])
        first_h = slide.get("table_first_column_header") or "Name"
        headers = [first_h, *cols]
        rows: list[list[str]] = []
        for it in items:
            name = str(it.get("name", ""))
            cells = [str(c) for c in (it.get("table_cells") or [])]
            rows.append([name, *cells])
        return {"mode": "table", "headers": headers, "rows": rows}

    pairs = [
        {"name": str(it.get("name", "")), "description": str(it.get("description") or "")}
        for it in items
    ]
    return {"mode": "deflist", "pairs": pairs}


def normalize_list_intro_slide(slide: dict) -> dict[str, Any]:
    sid = str(slide["id"])
    has_image = bool(slide.get("image"))
    return {
        "id": sid,
        "title": slide.get("title"),
        "intro": slide.get("intro"),
        "has_image": has_image,
        "image": slide.get("image"),
        "image_alt": slide.get("image_alt"),
        "figure_style": _figure_style(sid),
        "body": _list_body(slide),
    }


def normalize_figure_prose_slide(slide: dict) -> dict[str, Any]:
    sid = str(slide["id"])
    return {
        "id": sid,
        "title": slide.get("title"),
        "date_range": slide.get("date_range"),
        "image": slide["image"],
        "image_alt": slide["image_alt"],
        "paragraphs": list(slide.get("paragraphs") or []),
        "skills": slide.get("skills"),
        "skills_label": slide.get("skills_label"),
        "figure_style": _figure_style(sid),
    }


def web_with_normalized_slides(web: dict, *, slide_shape: Literal["list_intro", "figure"]) -> dict:
    """Copy ``web`` and set ``slides_normalized``; keep original ``slides``."""

    out = dict(web)
    slides: list[dict] = list(web.get("slides") or [])
    if slide_shape == "list_intro":
        out["slides_normalized"] = [normalize_list_intro_slide(s) for s in slides]
    else:
        out["slides_normalized"] = [normalize_figure_prose_slide(s) for s in slides]
    return out
