#!/usr/bin/env python3
import argparse
import shutil
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel, ConfigDict, Field


class Link(BaseModel):
    label: str
    url: str


class Contact(BaseModel):
    email: str
    phone: str
    location: str


class Profile(BaseModel):
    full_name: str
    contact: Contact
    links: list[Link]


class NamedBulletItem(BaseModel):
    """One row in a list-with-intro slide (skills / education carousels)."""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str


class SlideListIntro(BaseModel):
    """Intro copy plus name + description bullets (shared shape for skills & education)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str | None = None
    intro: str | None = None
    items: list[NamedBulletItem] = Field(min_length=1)


class SlideFigureProse(BaseModel):
    """Image + paragraph(s) for experience carousel slides."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str | None = None
    image: str
    image_alt: str = Field(min_length=1)
    paragraphs: list[str] = Field(min_length=1)


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
    id: str
    label: str
    items: list[str]


class Skills(BaseModel):
    groups: list[SkillGroup]
    web: SkillsWebExtra | None = None


class Highlight(BaseModel):
    text: str


class Tenure(BaseModel):
    start: str
    end: str | None = None
    arrangement: str | None = None
    title: str


class Position(BaseModel):
    id: str
    title: str
    company: str
    location: str
    employment: str
    start: str
    end: str | None = None
    seniority: str | None = None
    tenure: list[Tenure] | None = None
    highlights: list[Highlight]


class Experience(BaseModel):
    positions: list[Position]
    web: ExperienceWebExtra | None = None


class Degree(BaseModel):
    credential: str
    date: str


class EducationEntry(BaseModel):
    id: str
    institution: str
    location: str
    degrees: list[Degree]


class Education(BaseModel):
    entries: list[EducationEntry]
    web: EducationWebExtra | None = None


class Resume(BaseModel):
    profile: Profile
    skills: Skills
    experience: Experience
    education: Education


MONTHS = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)


def fmt_month(ym: str) -> str:
    y, m = ym.split("-", 1)
    return f"{MONTHS[int(m) - 1]} {y}"


def fmt_range(start: str, end: str | None) -> str:
    a = fmt_month(start)
    if end is None:
        return f"{a} – Present"
    return f"{a} – {fmt_month(end)}"


def fmt_range_compact(start: str, end: str | None) -> str:
    """Short ranges for tenure strips, e.g. Jun '24 – Aug '24."""

    def part(ym: str) -> str:
        y, m = ym.split("-", 1)
        return f"{MONTHS[int(m) - 1][:3]} '{y[-2:]}"

    a = part(start)
    if end is None:
        return f"{a} – Present"
    return f"{a} – {part(end)}"


def _ym_key(seg: dict) -> tuple[int, int]:
    y, m = seg["start"].split("-", 1)
    return (int(y), int(m))


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def parse_resume(data: dict) -> Resume:
    return Resume.model_validate(data)


def normalize(resume: Resume) -> dict:
    positions = []
    for pos in resume.experience.positions:
        p = pos.model_dump()
        p["date_range"] = fmt_range(pos.start, pos.end)
        if p.get("tenure"):
            segs = sorted(p["tenure"], key=_ym_key)
            p["progression_segments"] = [
                {
                    "title": s["title"],
                    "dates_compact": fmt_range_compact(s["start"], s.get("end")),
                }
                for s in segs
            ]
        else:
            p["progression_segments"] = None
        positions.append(p)
    edu_entries = []
    for ent in resume.education.entries:
        e = ent.model_dump()
        for d in e["degrees"]:
            d["date_display"] = fmt_month(d["date"])
        edu_entries.append(e)
    experience_view = {
        "positions": positions,
        "web": resume.experience.web.model_dump() if resume.experience.web else None,
    }
    education_view = {
        "entries": edu_entries,
        "web": resume.education.web.model_dump() if resume.education.web else None,
    }
    return {
        "profile": resume.profile.model_dump(),
        "skills": resume.skills.model_dump(),
        "experience": experience_view,
        "education": education_view,
    }


def copy_static_tree(static_root: Path, out_dir: Path) -> None:
    """Copy all files under static/ (e.g. carousel images) into the output directory."""

    if not static_root.is_dir():
        return
    for path in static_root.rglob("*"):
        if path.is_file():
            rel = path.relative_to(static_root)
            dest = out_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)


def nav_for_page(page: str) -> dict[str, str]:
    """§4 — hrefs for flat `index.html` at root and nested `*/index.html` pages."""

    if page == "resume":
        return {
            "current_page": "resume",
            "home_href": "index.html",
            "portfolio_href": "portfolio/index.html",
            "writings_href": "writings/index.html",
        }
    if page == "portfolio":
        return {
            "current_page": "portfolio",
            "home_href": "../index.html",
            "portfolio_href": "index.html",
            "writings_href": "../writings/index.html",
        }
    if page == "writings":
        return {
            "current_page": "writings",
            "home_href": "../index.html",
            "portfolio_href": "../portfolio/index.html",
            "writings_href": "index.html",
        }
    raise ValueError(f"unknown nav page: {page!r}")


def asset_hrefs(depth: int) -> tuple[str, str]:
    prefix = "../" * depth
    return f"{prefix}resume.css", f"{prefix}resume.js"


def render_html(env: Environment, template_name: str, context: dict) -> str:
    return env.get_template(template_name).render(**context)


def main() -> None:
    root = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input", type=Path, default=root / "resume.yaml")
    ap.add_argument("-o", "--output", type=Path, default=root / "dist")
    args = ap.parse_args()

    data = load_yaml(args.input)

    resume = parse_resume(data)
    view = normalize(resume)

    template_dir = root / "templates"
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )

    out_dir = args.output
    out_dir.mkdir(parents=True, exist_ok=True)

    css0, js0 = asset_hrefs(0)
    resume_ctx = {
        **view,
        "page_title": "Résumé",
        "nav": nav_for_page("resume"),
        "css_href": css0,
        "js_href": js0,
    }
    (out_dir / "index.html").write_text(render_html(env, "index.html.j2", resume_ctx))

    css1, js1 = asset_hrefs(1)
    nested_ctx = {**view, "css_href": css1, "js_href": js1}

    portfolio_dir = out_dir / "portfolio"
    portfolio_dir.mkdir(parents=True, exist_ok=True)
    (portfolio_dir / "index.html").write_text(
        render_html(
            env,
            "portfolio.html.j2",
            {
                **nested_ctx,
                "page_title": "Portfolio",
                "nav": nav_for_page("portfolio"),
            },
        )
    )

    writings_dir = out_dir / "writings"
    writings_dir.mkdir(parents=True, exist_ok=True)
    (writings_dir / "index.html").write_text(
        render_html(
            env,
            "writings.html.j2",
            {
                **nested_ctx,
                "page_title": "Writings",
                "nav": nav_for_page("writings"),
            },
        )
    )

    copy_static_tree(root / "static", out_dir)


if __name__ == "__main__":
    main()
