#!/usr/bin/env python3
import argparse
import re
import shutil
from pathlib import Path

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class SectionMeta(BaseModel):
    """Section heading text from YAML; HTML `id` slug is set in `normalize()`."""

    model_config = ConfigDict(extra="forbid")

    heading: str


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
    section: SectionMeta
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
    section: SectionMeta
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
    section: SectionMeta
    entries: list[EducationEntry]
    web: EducationWebExtra | None = None


class Resume(BaseModel):
    profile: Profile
    skills: Skills
    experience: Experience
    education: Education


class Project(BaseModel):
    """Portfolio entry: overview plus GitHub repo for future README embed."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    overview: str
    repo: str
    ref: str | None = None
    readme_path: str | None = None

    @field_validator("repo")
    @classmethod
    def repo_must_be_owner_slash_name(cls, v: str) -> str:
        v = v.strip()
        if v.count("/") != 1:
            raise ValueError('repo must be exactly "owner/name"')
        owner, name = v.split("/", 1)
        if not owner.strip() or not name.strip():
            raise ValueError("repo owner and name must be non-empty")
        return f"{owner.strip()}/{name.strip()}"


class ProjectsFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    projects: list[Project] = Field(default_factory=list)


class WritingsIndex(BaseModel):
    """Ordered list of Markdown paths (repo-root relative); each file becomes a writings page."""

    model_config = ConfigDict(extra="forbid")

    paths: list[str] = Field(default_factory=list)


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
    raw = path.read_text()
    if not raw.strip():
        return {}
    data = yaml.safe_load(raw)
    return data if data is not None else {}


def parse_resume(data: dict) -> Resume:
    return Resume.model_validate(data)


def parse_projects(data: dict) -> ProjectsFile:
    return ProjectsFile.model_validate(data)


def parse_writings_index(data: dict) -> WritingsIndex:
    return WritingsIndex.model_validate(data)


def portfolio_projects_view(pf: ProjectsFile) -> dict:
    """Template-ready project rows; README fetch and embed come later."""

    rows: list[dict] = []
    for p in pf.projects:
        d = p.model_dump()
        owner, name = p.repo.split("/", 1)
        d["github_url"] = f"https://github.com/{owner}/{name}"
        d["readme_display_path"] = p.readme_path or "README.md"
        rows.append(d)
    return {"projects": rows}


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
    """Resolve index paths to slugs, titles, and rendered bodies."""

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


def section_context(slug: str, meta: SectionMeta) -> dict[str, str]:
    return {
        "id": slug,
        "heading": meta.heading,
        "heading_id": f"{slug}-heading",
    }


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
        "section": section_context("experience", resume.experience.section),
        "positions": positions,
        "web": resume.experience.web.model_dump() if resume.experience.web else None,
    }
    education_view = {
        "section": section_context("education", resume.education.section),
        "entries": edu_entries,
        "web": resume.education.web.model_dump() if resume.education.web else None,
    }
    skills_data = resume.skills.model_dump()
    skills_data["section"] = section_context("skills", resume.skills.section)
    return {
        "profile": resume.profile.model_dump(),
        "skills": skills_data,
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

    if page == "home":
        return {
            "current_page": "home",
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
    if page == "writing_post":
        return {
            "current_page": "writing_post",
            "home_href": "../../index.html",
            "portfolio_href": "../../portfolio/index.html",
            "writings_href": "../index.html",
        }
    raise ValueError(f"unknown nav page: {page!r}")


def asset_hrefs(depth: int) -> tuple[str, str]:
    prefix = "../" * depth
    return f"{prefix}site.css", f"{prefix}site.js"


def render_html(env: Environment, template_name: str, context: dict) -> str:
    return env.get_template(template_name).render(**context)


def main() -> None:
    root = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input", type=Path, default=root / "data" / "resume.yaml")
    ap.add_argument(
        "--projects",
        type=Path,
        default=root / "data" / "projects.yaml",
        help="Portfolio projects YAML (default: ./data/projects.yaml)",
    )
    ap.add_argument(
        "--writings-index",
        type=Path,
        default=root / "writings" / "index.yaml",
        help="Writings index YAML (default: ./writings/index.yaml)",
    )
    ap.add_argument("-o", "--output", type=Path, default=root / "dist")
    args = ap.parse_args()

    data = load_yaml(args.input)

    resume = parse_resume(data)
    view = normalize(resume)

    projects_file = parse_projects(
        load_yaml(args.projects) if args.projects.is_file() else {}
    )
    writings_index = parse_writings_index(
        load_yaml(args.writings_index) if args.writings_index.is_file() else {}
    )
    proj_view = portfolio_projects_view(projects_file)
    writings_idx_view = writings_index.model_dump()
    writings_articles = load_writings_articles(root, writings_index)
    writings_articles_list = [
        {
            "title": a["title"],
            "href": a["href"],
            "source_path": a["source_path"],
        }
        for a in writings_articles
    ]

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
        "nav": nav_for_page("home"),
        "css_href": css0,
        "js_href": js0,
    }
    (out_dir / "index.html").write_text(render_html(env, "index.html.j2", resume_ctx))

    css1, js1 = asset_hrefs(1)
    nested_ctx = {
        **view,
        "css_href": css1,
        "js_href": js1,
        **proj_view,
        "writings_index": writings_idx_view,
        "writings_articles": writings_articles_list,
    }

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

    css2, js2 = asset_hrefs(2)
    for art in writings_articles:
        post_dir = writings_dir / art["slug"]
        post_dir.mkdir(parents=True, exist_ok=True)
        (post_dir / "index.html").write_text(
            render_html(
                env,
                "writing_post.html.j2",
                {
                    **view,
                    "page_title": art["title"],
                    "body_html": art["body_html"],
                    "css_href": css2,
                    "js_href": js2,
                    "nav": nav_for_page("writing_post"),
                },
            )
        )

    copy_static_tree(root / "static", out_dir)


if __name__ == "__main__":
    main()
