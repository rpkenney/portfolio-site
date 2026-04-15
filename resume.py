#!/usr/bin/env python3
import argparse
import shutil
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel


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


class SkillGroup(BaseModel):
    id: str
    label: str
    items: list[str]


class Skills(BaseModel):
    groups: list[SkillGroup]


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
    return {
        "profile": resume.profile.model_dump(),
        "skills": resume.skills.model_dump(),
        "experience": {"positions": positions},
        "education": {"entries": edu_entries},
    }


def render_html(view: dict, template_dir: Path) -> str:
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    return env.get_template("index.html.j2").render(**view)


def main() -> None:
    root = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input", type=Path, default=root / "resume.yaml")
    ap.add_argument("-o", "--output", type=Path, default=root / "dist")
    args = ap.parse_args()

    data = load_yaml(args.input)

    resume = parse_resume(data)
    view = normalize(resume)

    out_dir = args.output
    out_dir.mkdir(parents=True, exist_ok=True)
    html = render_html(view, root / "templates")
    (out_dir / "index.html").write_text(html)
    shutil.copy(root / "static" / "resume.css", out_dir / "resume.css")


if __name__ == "__main__":
    main()
