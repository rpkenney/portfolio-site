"""Projects YAML → portfolio template context (``projects``, derived URLs)."""

from __future__ import annotations

from pathlib import Path

from frontends.jinja.site_content import SiteSectionSpec
from ingest.projects import parse_projects, portfolio_projects_view
from ingest.yaml_io import load_yaml

_PROJECTS_YAML = ("content", "data", "projects.yaml")


def _projects_yaml_path(root: Path) -> Path:
    return root.joinpath(*_PROJECTS_YAML)


def load_portfolio_view(projects_path: Path) -> dict:
    """Return ``portfolio_projects_view`` dict (``{"projects": [...]}``)."""

    data = load_yaml(projects_path) if projects_path.is_file() else {}
    return portfolio_projects_view(parse_projects(data))


def contribute_section(content_root: Path) -> SiteSectionSpec:
    """See :mod:`frontends.jinja.sections` package docstring."""

    return SiteSectionSpec(
        fragment={"portfolio_view": load_portfolio_view(_projects_yaml_path(content_root))},
        content_merge={"portfolio_view": "spread"},
    )
