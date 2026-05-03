"""Résumé: YAML on disk → Jinja root dict (``profile``, ``skills``, …).

**Carousel data:** optional YAML ``web`` blocks are passed through
``ingest.carousel_normalize.web_with_normalized_slides`` inside
:func:`normalize` — that package owns slide body shape (``slides_normalized``);
this module owns section wrappers, date denormalization on experience slides,
and the overall dict layout for the home page.
"""

from __future__ import annotations

from pathlib import Path

from frontends.jinja.site_content import SiteSectionSpec
from ingest.carousel_normalize import web_with_normalized_slides
from ingest.resume import Resume, SectionMeta, parse_resume
from ingest.yaml_io import load_yaml

# Default layout under ``--content-root`` (override by changing this module).
_RESUME_YAML = ("content", "data", "resume.yaml")


def _resume_yaml_path(root: Path) -> Path:
    return root.joinpath(*_RESUME_YAML)


def section_context(slug: str, meta: SectionMeta) -> dict[str, str]:
    """Section header bundle for templates.

    * ``heading`` — from YAML (``SectionMeta`` in ``ingest.resume``)
    * ``id``, ``heading_id`` — derived here for DOM/aria (not in YAML)
    """

    return {
        "id": slug,
        "heading": meta.heading,
        "heading_id": f"{slug}-heading",
    }


def normalize(resume: Resume) -> dict:
    """Build the résumé root context for ``index.html.j2``.

    **Keys:** ``profile``, ``skills``, ``experience``, ``education``.

    **Straight from YAML** (``model_dump()``): ``profile``; ``skills`` groups/items
    and optional ``web`` slides; ``experience.positions`` (including ``date_range``,
    ``progression_segments``) and optional ``web`` slides; ``education.entries`` and
    optional ``web``.

    **Changed here:** for ``skills``, ``experience``, and ``education``, the ``section``
    key is not a raw ``SectionMeta`` dump—it is replaced with ``section_context``
    so templates get ``id``, ``heading``, ``heading_id``.

    Each optional ``web`` dict gets ``slides_normalized`` (see ``ingest.carousel_normalize``):
    list-intro carousels use a table/deflist body model; experience uses figure slides
    with optional ``figure_style`` from slide ``id``.
    """

    experience_view = {
        "section": section_context("experience", resume.experience.section),
        "positions": [p.model_dump() for p in resume.experience.positions],
        "web": (
            web_with_normalized_slides(
                resume.experience.web.model_dump(),
                slide_shape="figure",
            )
            if resume.experience.web
            else None
        ),
    }
    education_view = {
        "section": section_context("education", resume.education.section),
        "entries": [e.model_dump() for e in resume.education.entries],
        "web": (
            web_with_normalized_slides(
                resume.education.web.model_dump(),
                slide_shape="list_intro",
            )
            if resume.education.web
            else None
        ),
    }
    skills_data = resume.skills.model_dump()
    skills_data["section"] = section_context("skills", resume.skills.section)
    if skills_data.get("web"):
        skills_data["web"] = web_with_normalized_slides(
            skills_data["web"],
            slide_shape="list_intro",
        )
    return {
        "profile": resume.profile.model_dump(),
        "skills": skills_data,
        "experience": experience_view,
        "education": education_view,
    }


def load_resume_view(resume_path: Path) -> tuple[dict, str]:
    """Return ``(resume_view, site_owner_name)`` for templates."""

    resume = parse_resume(load_yaml(resume_path))
    resume_view = normalize(resume)
    site_owner_name = str(resume_view["profile"]["full_name"])
    return resume_view, site_owner_name


def contribute_section(content_root: Path) -> SiteSectionSpec:
    """See :mod:`frontends.jinja.sections` package docstring."""

    resume_view, site_owner_name = load_resume_view(_resume_yaml_path(content_root))
    return SiteSectionSpec(
        fragment={
            "resume_view": resume_view,
            "site_owner_name": site_owner_name,
        },
        content_merge={"resume_view": "spread"},
        route_overrides={"index": {"page_title": "Résumé"}},
    )
