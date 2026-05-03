"""Relative ``href``s for static HTML (``site.css``, ``js/nav.js``, ``js/carousel.js`` by depth)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

# Current page kind for ``nav_for`` / templates.
NavPage = str


@dataclass(frozen=True)
class NavBarItem:
    """One top nav link: ``nav_key`` matches ``StaticSiteRoute.nav_page`` for that page."""

    nav_key: str
    label: str
    folder: str | None
    current_aliases: frozenset[str] = field(default_factory=frozenset)


def _href_for_nav_item(
    item: NavBarItem,
    *,
    current_nav: str,
    depth: int,
    post_rules: Sequence[tuple[str, str]],
) -> str:
    up = "../" * depth

    if item.folder is None:
        return "index.html" if depth == 0 else f"{up}index.html"

    folder = item.folder

    if current_nav == item.nav_key and depth == 1:
        return "index.html"

    for post_nav, section_nav in post_rules:
        if current_nav == post_nav and item.nav_key == section_nav:
            return "../index.html"

    return f"{up}{folder}/index.html"


def nav_for(
    nav_page: str,
    depth: int,
    *,
    items: Sequence[NavBarItem],
    post_rules: Sequence[tuple[str, str]] = (),
) -> dict[str, object]:
    """Nav for ``macros_nav.j2``: ``current_page`` plus ``links`` (href, label, keys for current state)."""

    entries: list[dict[str, object]] = []
    for it in items:
        entries.append(
            {
                "nav_key": it.nav_key,
                "label": it.label,
                "href": _href_for_nav_item(
                    it, current_nav=nav_page, depth=depth, post_rules=post_rules
                ),
                "current_aliases": tuple(it.current_aliases),
            }
        )
    return {"current_page": nav_page, "links": tuple(entries)}


def asset_hrefs(depth: int) -> tuple[str, str, str]:
    """CSS path, then nav script, then carousel script (order matches ``base.html.j2``)."""

    prefix = "../" * depth
    return (
        f"{prefix}site.css",
        f"{prefix}js/nav.js",
        f"{prefix}js/carousel.js",
    )
