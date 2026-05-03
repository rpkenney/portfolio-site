"""Pydantic models for ``content/data/resume.yaml``.

Fields are loaded from YAML; validators only enforce consistency (e.g. table vs deflist rows).
HTML section ids and template-facing reshaping are **not** applied here—see
``frontends.jinja.sections.resume.normalize()`` for the Jinja context layer.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Link(BaseModel):
    """Labeled URL under ``profile.links`` in YAML; passed through to templates unchanged."""

    label: str
    url: str


class Contact(BaseModel):
    """Contact block under ``profile.contact``; no derived fields."""

    email: str
    phone: str
    location: str


class Profile(BaseModel):
    """Masthead + summary from YAML; ``model_dump()`` is the template ``profile`` context."""

    full_name: str
    contact: Contact
    links: list[Link]
    summary: list[str] | None = None


class SectionMeta(BaseModel):
    """Per-section heading from YAML. ``id`` / ``heading_id`` for HTML are added in ``section_context()``."""

    model_config = ConfigDict(extra="forbid")

    heading: str


class NamedBulletItem(BaseModel):
    """One row in a list-with-intro slide (skills / education carousels)."""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str | None = None
    table_cells: list[str] | None = None

    @model_validator(mode="after")
    def _one_row_shape(self) -> "NamedBulletItem":
        has_d = self.description is not None and self.description.strip() != ""
        has_cells = bool(self.table_cells and any(c.strip() for c in self.table_cells))
        if has_d and has_cells:
            raise ValueError(
                f"item {self.name!r}: set `description` OR `table_cells`, not both"
            )
        if not has_d and not has_cells:
            raise ValueError(
                f"item {self.name!r}: need `description` or `table_cells`"
            )
        return self


class SlideListIntro(BaseModel):
    """Intro copy plus name + description bullets (shared shape for skills & education)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str | None = None
    image: str | None = None
    image_alt: str | None = None
    intro: str | None = None
    items_layout: Literal["deflist", "table"] = "deflist"
    table_first_column_header: str | None = None
    table_columns: list[str] | None = None
    items: list[NamedBulletItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def _layout_matches_items(self) -> "SlideListIntro":
        if self.image is not None:
            if self.image_alt is None or self.image_alt.strip() == "":
                raise ValueError(
                    f"slide {self.id!r}: `image_alt` is required when `image` is set"
                )

        has_intro = self.intro is not None and self.intro.strip() != ""
        if not has_intro and len(self.items) == 0:
            raise ValueError(
                f"slide {self.id!r}: provide `intro` and/or at least one `items` row"
            )

        for it in self.items:
            has_d = it.description is not None and it.description.strip() != ""
            if self.items_layout == "table":
                if not self.table_columns or len(self.table_columns) < 1:
                    raise ValueError(
                        f"slide {self.id!r} uses table layout: set `table_columns` (1+ headers)"
                    )
                if it.table_cells is None or len(it.table_cells) != len(self.table_columns):
                    raise ValueError(
                        f"slide {self.id!r} uses table layout: item {it.name!r} must have "
                        f"`table_cells` with {len(self.table_columns)} entr{'y' if len(self.table_columns)==1 else 'ies'}"
                    )
                if has_d:
                    raise ValueError(
                        f"slide {self.id!r} uses table layout: item {it.name!r} "
                        "must set only `table_cells`"
                    )
            else:
                if not has_d or it.table_cells is not None:
                    raise ValueError(
                        f"slide {self.id!r} uses deflist layout: item {it.name!r} "
                        "must set only `description`"
                    )
        return self


class SlideFigureProse(BaseModel):
    """Experience carousel slide: image, prose, optional ``title`` / ``date_range`` from YAML.

    Optional ``date_range`` here is author-written per slide (not auto-filled from
    the parent ``Position`` in YAML today).
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str | None = None
    date_range: str | None = None
    image: str
    image_alt: str = Field(min_length=1)
    paragraphs: list[str] = Field(min_length=1)
    skills: list[str] | None = None
    skills_label: str | None = None


class SkillsWebExtra(BaseModel):
    """Web-only carousel for the Skills section (print omits)."""

    model_config = ConfigDict(extra="forbid")

    slides: list[SlideListIntro] = Field(min_length=1)
    aria_label: str | None = None


class EducationWebExtra(BaseModel):
    """Web-only carousel for the Education section (print omits)."""

    model_config = ConfigDict(extra="forbid")

    slides: list[SlideListIntro] = Field(min_length=1)
    aria_label: str | None = None


class ExperienceWebExtra(BaseModel):
    """Web-only carousel for the Experience section (print omits)."""

    model_config = ConfigDict(extra="forbid")

    slides: list[SlideFigureProse] = Field(min_length=1)
    aria_label: str | None = None


class SkillGroup(BaseModel):
    """One row in the default (non-carousel) skills list."""

    id: str
    label: str
    items: list[str]


class Skills(BaseModel):
    """Skills section: YAML ``groups`` for print/default web; optional ``web`` carousel."""

    section: SectionMeta
    groups: list[SkillGroup]
    web: SkillsWebExtra | None = None


class Highlight(BaseModel):
    """Single bullet under an experience position."""

    text: str


class ProgressionSegment(BaseModel):
    """One segment in the role progression line; display strings come from YAML only."""

    model_config = ConfigDict(extra="forbid")

    title: str
    dates_compact: str


class Position(BaseModel):
    """Experience role: ``date_range`` and optional ``progression_segments`` are author-written in YAML."""

    id: str
    title: str
    company: str
    location: str
    employment: str
    seniority: str | None = None
    date_range: str
    progression_segments: list[ProgressionSegment] | None = None
    highlights: list[Highlight]


class Experience(BaseModel):
    """Experience section: positions plus optional ``web`` figure carousel."""

    section: SectionMeta
    positions: list[Position]
    web: ExperienceWebExtra | None = None


class Degree(BaseModel):
    """One degree line; ``date_display`` is the string shown next to the credential (author-chosen)."""

    credential: str
    date_display: str
    tag: str | None = None


class EducationEntry(BaseModel):
    """School block under education."""

    id: str
    institution: str
    location: str
    degrees: list[Degree]


class Education(BaseModel):
    """Education section: entries plus optional ``web`` list/table carousel."""

    section: SectionMeta
    entries: list[EducationEntry]
    web: EducationWebExtra | None = None


class Resume(BaseModel):
    """Root document matching ``content/data/resume.yaml`` after validation.

    Load with ``parse_resume``; pass to ``normalize`` in ``frontends.jinja.sections.resume``
    for the dict consumed by ``index.html.j2``.
    """

    profile: Profile
    skills: Skills
    experience: Experience
    education: Education


def parse_resume(data: dict) -> Resume:
    """Validate a loaded résumé mapping (e.g. from ``yaml.safe_load``) into a ``Resume``.

    Output is still “author data”: no ``section_context`` ids, no template-only keys.
    """

    return Resume.model_validate(data)
