"""Emit static HTML: registered pages, optional section emit hooks, assets."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment

from frontends.jinja.assets import build_css_bundle, copy_static_tree
from frontends.jinja.env import jinja_templates_dir, render_html
from frontends.jinja.nav import NavBarItem, asset_hrefs, nav_for
from frontends.jinja.routes import (
    StaticSiteRoute,
    discover_static_site_routes,
    nav_bar_items_from_static_routes,
)
from frontends.jinja.site_content import (
    SiteContentBundle,
    flattened_template_context,
    merged_emit_only_template_names,
    merged_site_route_overrides,
    nav_post_subpage_rules,
)


def static_page_context(
    route: StaticSiteRoute,
    bundle: SiteContentBundle,
    *,
    under_construction: bool,
    under_construction_src_depth1: str,
    nav_bar_items: tuple[NavBarItem, ...],
    post_rules: tuple[tuple[str, str], ...],
) -> dict:
    """Full template context for one static route (superset for all static pages)."""

    css_href, js_nav_href, js_carousel_href = asset_hrefs(route.depth)
    nav = nav_for(
        route.nav_page,
        route.depth,
        items=nav_bar_items,
        post_rules=post_rules,
    )
    base = flattened_template_context(bundle)
    return {
        **base,
        "page_title": route.page_title,
        "nav": nav,
        "css_href": css_href,
        "js_nav_href": js_nav_href,
        "js_carousel_href": js_carousel_href,
        "under_construction": under_construction,
        "under_construction_src": under_construction_src_depth1,
    }


def build_static_pages(
    env: Environment,
    out_dir: Path,
    bundle: SiteContentBundle,
    *,
    routes: tuple[StaticSiteRoute, ...],
    nav_bar_items: tuple[NavBarItem, ...],
    post_rules: tuple[tuple[str, str], ...],
    under_construction: bool,
) -> None:
    """Render each page-level template (see :func:`~frontends.jinja.routes.discover_static_site_routes`)."""

    uc_depth1 = "../under_construction.gif" if under_construction else ""
    for route in routes:
        out_path = out_dir.joinpath(*route.out_parts)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        ctx = static_page_context(
            route,
            bundle,
            under_construction=under_construction,
            under_construction_src_depth1=uc_depth1,
            nav_bar_items=nav_bar_items,
            post_rules=post_rules,
        )
        out_path.write_text(render_html(env, route.template, ctx))


def _emit_section_site_pages(
    env: Environment,
    out_dir: Path,
    bundle: SiteContentBundle,
    *,
    under_construction: bool,
    nav_bar_items: tuple[NavBarItem, ...],
    post_rules: tuple[tuple[str, str], ...],
) -> None:
    """Call each section spec’s ``emit_site_pages`` when set."""

    for c in bundle.contributions:
        fn = c.spec.emit_site_pages
        if fn is not None:
            fn(
                env,
                out_dir,
                bundle,
                under_construction=under_construction,
                nav_bar_items=nav_bar_items,
                post_rules=post_rules,
            )


def run_jinja_site_build(
    env: Environment,
    out_dir: Path,
    static_root: Path,
    bundle: SiteContentBundle,
    *,
    under_construction: bool,
) -> None:
    """CSS bundle, static pages, optional section ``emit_site_pages``, copy ``static/``."""

    out_dir.mkdir(parents=True, exist_ok=True)
    build_css_bundle(static_root, out_dir)
    route_overrides = merged_site_route_overrides(bundle)
    emit_only = merged_emit_only_template_names(bundle)
    routes = discover_static_site_routes(
        jinja_templates_dir(),
        route_overrides,
        emit_only_template_names=emit_only,
    )
    post_rules = nav_post_subpage_rules(bundle)
    nav_bar_items = nav_bar_items_from_static_routes(routes, post_rules)
    build_static_pages(
        env,
        out_dir,
        bundle,
        routes=routes,
        nav_bar_items=nav_bar_items,
        post_rules=post_rules,
        under_construction=under_construction,
    )
    _emit_section_site_pages(
        env,
        out_dir,
        bundle,
        under_construction=under_construction,
        nav_bar_items=nav_bar_items,
        post_rules=post_rules,
    )
    copy_static_tree(static_root, out_dir)
