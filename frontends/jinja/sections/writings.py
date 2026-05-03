"""Writings index + Markdown → article rows, listing fragment, and per-post HTML."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment

from frontends.jinja.env import render_html
from frontends.jinja.nav import NavBarItem, asset_hrefs, nav_for
from frontends.jinja.site_content import (
    SiteContentBundle,
    SiteSectionSpec,
    site_owner_name,
    writings_articles_for_posts,
)
from ingest.writings import load_writings_articles, parse_writings_index
from ingest.yaml_io import load_yaml

# --- Per-post HTML: one output per slug under ``dist/<segment>/<slug>/`` ---

POST_SECTION_SEGMENT = "writings"
POST_PAGE_TEMPLATE = "writing_post.html.j2"
POST_NAV_PAGE = "writing_post"
# ``dist/writings/<slug>/index.html`` → two levels below ``dist/`` for ``../`` asset prefixes.
POST_PAGE_DEPTH = 2

_WRITINGS_INDEX_YAML = ("content", "writings", "index.yaml")


def _writings_index_path(root: Path) -> Path:
    return root.joinpath(*_WRITINGS_INDEX_YAML)


def load_writings_bundle(
    root: Path,
    writings_index_path: Path,
) -> tuple[list[dict], list[dict]]:
    """Return ``(writings_articles, writings_listing)``.

    * ``writings_articles`` — full rows for per-post HTML (slug, body_html, …).
    * ``writings_listing`` — slim rows for the writings index template.
    """

    writings_index = parse_writings_index(
        load_yaml(writings_index_path) if writings_index_path.is_file() else {}
    )
    writings_articles = load_writings_articles(root, writings_index)
    writings_listing = [
        {
            "title": article["title"],
            "href": article["href"],
            "source_path": article["source_path"],
        }
        for article in writings_articles
    ]
    return writings_articles, writings_listing


def emit_site_pages(
    env: Environment,
    out_dir: Path,
    bundle: SiteContentBundle,
    *,
    under_construction: bool,
    nav_bar_items: tuple[NavBarItem, ...],
    post_rules: tuple[tuple[str, str], ...],
) -> None:
    """Emit ``writings/<slug>/index.html`` for each article (registered on :class:`SiteSectionSpec`)."""

    owner = site_owner_name(bundle)
    writings_articles = writings_articles_for_posts(bundle)
    writings_dir = out_dir / POST_SECTION_SEGMENT
    css_href, js_nav_href, js_carousel_href = asset_hrefs(POST_PAGE_DEPTH)
    nav = nav_for(
        POST_NAV_PAGE,
        POST_PAGE_DEPTH,
        items=nav_bar_items,
        post_rules=post_rules,
    )
    uc_post = "../../under_construction.gif" if under_construction else ""

    for article in writings_articles:
        post_dir = writings_dir / article["slug"]
        post_dir.mkdir(parents=True, exist_ok=True)
        (post_dir / "index.html").write_text(
            render_html(
                env,
                POST_PAGE_TEMPLATE,
                {
                    "site_owner_name": owner,
                    "page_title": article["title"],
                    "body_html": article["body_html"],
                    "css_href": css_href,
                    "js_nav_href": js_nav_href,
                    "js_carousel_href": js_carousel_href,
                    "nav": nav,
                    "under_construction": under_construction,
                    "under_construction_src": uc_post,
                },
            )
        )


def contribute_section(content_root: Path) -> SiteSectionSpec:
    """See :mod:`frontends.jinja.sections` package docstring."""

    writings_articles, writings_listing = load_writings_bundle(
        content_root, _writings_index_path(content_root)
    )
    return SiteSectionSpec(
        fragment={
            "writings_articles": writings_articles,
            "writings_listing": writings_listing,
        },
        content_merge={
            "writings_listing": "as:writings_articles",
            "writings_articles": "omit",
        },
        emit_only_templates=frozenset({POST_PAGE_TEMPLATE}),
        nav_post_rules=(
            {"post_nav_page": POST_NAV_PAGE, "section_nav_key": POST_SECTION_SEGMENT},
        ),
        emit_site_pages=emit_site_pages,
    )
