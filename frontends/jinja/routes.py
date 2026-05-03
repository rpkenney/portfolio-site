"""Route types and template-derived static pages (with section overrides)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from frontends.jinja.nav import NavBarItem, NavPage

# Always skip (layout); emit-only templates come from section ``SITE_EMIT_ONLY_TEMPLATES``.
_DEFAULT_PAGE_TEMPLATE_SKIP_NAMES: frozenset[str] = frozenset({"base.html.j2"})


def _is_page_level_template(path: Path, emit_only_names: frozenset[str]) -> bool:
    """True for top-level ``*.html.j2`` that become one HTML file under ``dist/``."""

    if not path.is_file():
        return False
    name = path.name
    if not name.endswith(".html.j2"):
        return False
    if name in _DEFAULT_PAGE_TEMPLATE_SKIP_NAMES | emit_only_names:
        return False
    if name.startswith("macros_") or name.startswith("under_construction"):
        return False
    return True


def _template_base(path: Path) -> str:
    return path.name.removesuffix(".html.j2")


def _default_nav_page(base: str) -> str:
    return "home" if base == "index" else base


def _effective_nav_and_title(
    base: str,
    overrides: Mapping[str, Mapping[str, str]],
) -> tuple[str, str]:
    """Defaults from filename; optional ``SITE_ROUTE_OVERRIDES`` per template base."""

    nav_page = _default_nav_page(base)
    page_title = base.replace("_", " ").title()
    patch = dict(overrides.get(base, {}))
    if "nav_page" in patch:
        nav_page = str(patch.pop("nav_page"))
    if "page_title" in patch:
        page_title = str(patch.pop("page_title"))
    if patch:
        raise ValueError(
            f"unknown SITE_ROUTE_OVERRIDES keys for template base {base!r}: {sorted(patch)} "
            "(allowed: nav_page, page_title)"
        )
    return nav_page, page_title


def _route_for_page_template(
    path: Path,
    overrides: Mapping[str, Mapping[str, str]],
) -> StaticSiteRoute:
    base = _template_base(path)
    template = path.name
    nav_page, page_title = _effective_nav_and_title(base, overrides)
    if base == "index":
        return StaticSiteRoute(
            name="home",
            template=template,
            out_parts=("index.html",),
            depth=0,
            page_title=page_title,
            nav_page=nav_page,
        )
    return StaticSiteRoute(
        name=base,
        template=template,
        out_parts=(base, "index.html"),
        depth=1,
        page_title=page_title,
        nav_page=nav_page,
    )


def discover_static_site_routes(
    templates_dir: Path,
    route_overrides: Mapping[str, Mapping[str, str]],
    *,
    emit_only_template_names: frozenset[str] = frozenset(),
) -> tuple[StaticSiteRoute, ...]:
    """One route per page-level template; ``route_overrides`` from :func:`merged_site_route_overrides`.

    ``emit_only_template_names`` is the union of section ``SITE_EMIT_ONLY_TEMPLATES`` (templates used
    only by ``emit_site_pages``, not one static URL each).
    """

    if not templates_dir.is_dir():
        raise FileNotFoundError(f"missing templates dir: {templates_dir}")
    paths = [
        p
        for p in templates_dir.iterdir()
        if _is_page_level_template(p, emit_only_template_names)
    ]

    def sort_key(p: Path) -> tuple[int, str]:
        b = _template_base(p)
        return (0 if b == "index" else 1, p.name)

    return tuple(
        _route_for_page_template(p, route_overrides)
        for p in sorted(paths, key=sort_key)
    )


def nav_bar_items_from_static_routes(
    routes: tuple[StaticSiteRoute, ...],
    post_rules: tuple[tuple[str, str], ...],
) -> tuple[NavBarItem, ...]:
    """Top nav from static routes; ``post_rules`` add ``current_aliases`` for section indexes."""

    by_section: dict[str, set[str]] = {}
    for post_nav, section_nav in post_rules:
        by_section.setdefault(section_nav, set()).add(post_nav)

    out: list[NavBarItem] = []
    for r in routes:
        aliases = frozenset(by_section.get(r.nav_page, ()))
        out.append(
            NavBarItem(
                nav_key=r.nav_page,
                label=r.page_title,
                folder=None if r.nav_page == "home" else r.name,
                current_aliases=aliases,
            )
        )
    return tuple(out)


@dataclass(frozen=True)
class StaticSiteRoute:
    """One built ``index.html`` (or nested ``.../index.html``) under ``dist/``."""

    name: str
    template: str
    out_parts: tuple[str, ...]
    depth: int
    page_title: str
    nav_page: NavPage
