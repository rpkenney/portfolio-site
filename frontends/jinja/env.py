"""Jinja environment and one-shot HTML render for this frontend."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape


def jinja_templates_dir() -> Path:
    return Path(__file__).resolve().parent / "templates"


def create_env(*, extra_globals: dict | None = None) -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(jinja_templates_dir())),
        autoescape=select_autoescape(["html", "xml"]),
    )
    if extra_globals:
        env.globals.update(extra_globals)
    return env


def render_html(env: Environment, template_name: str, context: dict) -> str:
    return env.get_template(template_name).render(**context)
