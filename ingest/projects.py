"""Portfolio: ``content/data/projects.yaml`` schema and rows for ``portfolio.html.j2``.

``Project`` fields are YAML-only. ``portfolio_projects_view`` adds derived
``github_url`` and ``readme_display_path`` for templates.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    """Root shape for ``content/data/projects.yaml``."""

    model_config = ConfigDict(extra="forbid")

    projects: list[Project] = Field(default_factory=list)


def parse_projects(data: dict) -> ProjectsFile:
    """Validate projects YAML dict (default file: ``content/data/projects.yaml``)."""

    return ProjectsFile.model_validate(data)


def portfolio_projects_view(pf: ProjectsFile) -> dict:
    """``{"projects": [...]}`` for Jinja: each row is ``Project.model_dump()`` plus

    * ``github_url`` — from ``repo`` (``owner/name``)
    * ``readme_display_path`` — ``readme_path`` or default ``README.md``
    """

    rows: list[dict] = []
    for p in pf.projects:
        d = p.model_dump()
        owner, name = p.repo.split("/", 1)
        d["github_url"] = f"https://github.com/{owner}/{name}"
        d["readme_display_path"] = p.readme_path or "README.md"
        rows.append(d)
    return {"projects": rows}
