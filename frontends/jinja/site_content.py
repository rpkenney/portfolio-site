"""Compose ordered :class:`SiteSectionSpec` contributions into a :class:`SiteContentBundle`.

Section modules are imported by dotted path (see :func:`load_site_section_modules`).
Package docs for authors: :mod:`frontends.jinja.sections`.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

SECTION_MODULE_PREFIX = "frontends.jinja.sections."


@dataclass(frozen=True)
class SiteSectionSpec:
    """Single structured contribution from one section module (:func:`contribute_section`).

    * ``fragment`` — keys merged into the flat Jinja context (must not overlap across sections).
    * ``content_merge`` — per fragment key, merge rule for :func:`flattened_template_context`.
    * ``route_overrides`` — optional static-route patches (template base → ``nav_page`` / ``page_title``).
    * ``nav_post_rules`` — optional post-page nav rows (``post_nav_page``, ``section_nav_key``).
    * ``emit_only_templates`` — Jinja basenames excluded from static route discovery.
    * ``emit_site_pages`` — optional callable run after static pages (same signature as before).
    """

    fragment: dict[str, object]
    content_merge: dict[str, str] = field(default_factory=dict)
    route_overrides: dict[str, dict[str, str]] = field(default_factory=dict)
    nav_post_rules: tuple[dict[str, str], ...] = ()
    emit_only_templates: frozenset[str] = field(default_factory=frozenset)
    emit_site_pages: Callable[..., None] | None = None


def load_site_section_modules(names: Sequence[str]) -> tuple[ModuleType, ...]:
    """Import section modules in the given order (each name is a dotted import path).

    Each name must start with ``SECTION_MODULE_PREFIX`` (no ``..``).
    """

    if not names:
        raise ValueError("section module list is empty")
    out: list[ModuleType] = []
    for name in names:
        if ".." in name or not name.startswith(SECTION_MODULE_PREFIX):
            raise ValueError(
                f"section module {name!r} must start with {SECTION_MODULE_PREFIX!r} "
                "and must not contain '..'"
            )
        mod = importlib.import_module(name)
        if not callable(getattr(mod, "contribute_section", None)):
            raise ValueError(f"{name!r} has no callable contribute_section")
        out.append(mod)
    return tuple(out)


@dataclass(frozen=True)
class SiteSectionContribution:
    """One section module’s :class:`SiteSectionSpec` after :func:`load_site_content`."""

    module: ModuleType
    spec: SiteSectionSpec

    @property
    def module_name(self) -> str:
        return self.module.__name__


@dataclass(frozen=True)
class SiteContentBundle:
    """Ordered section specs (module load order).

    Static Jinja pages use :func:`flattened_template_context` to merge ``fragment`` keys.
    Route discovery and emit hooks read merged fields from each :class:`SiteSectionSpec`.
    """

    contributions: tuple[SiteSectionContribution, ...]


def merged_site_route_overrides(bundle: SiteContentBundle) -> dict[str, dict[str, str]]:
    """Merge ``route_overrides`` from each section (later modules win per field)."""

    out: dict[str, dict[str, str]] = {}
    for c in bundle.contributions:
        raw = c.spec.route_overrides
        for base, patch in raw.items():
            if not isinstance(patch, dict):
                raise TypeError(
                    f"{c.module.__name__}: route_overrides[{base!r}] must be a dict"
                )
            merged = dict(out.get(base, {}))
            merged.update({k: str(v) for k, v in patch.items()})
            out[str(base)] = merged
    return out


def merged_emit_only_template_names(bundle: SiteContentBundle) -> frozenset[str]:
    """Union of ``emit_only_templates`` from each section."""

    names: set[str] = set()
    for c in bundle.contributions:
        raw = c.spec.emit_only_templates
        for n in raw:
            names.add(str(n))
    return frozenset(names)


def nav_post_subpage_rules(bundle: SiteContentBundle) -> tuple[tuple[str, str], ...]:
    """Flatten ``nav_post_rules`` (post ``nav_page`` → parent section ``nav_page``)."""

    rules: list[tuple[str, str]] = []
    for c in bundle.contributions:
        raw = c.spec.nav_post_rules
        for i, item in enumerate(raw):
            if not isinstance(item, dict):
                raise TypeError(f"{c.module.__name__}: nav_post_rules[{i}] must be a dict")
            try:
                post = item["post_nav_page"]
                section = item["section_nav_key"]
            except KeyError as exc:
                raise ValueError(
                    f"{c.module.__name__}: nav_post_rules[{i}] needs "
                    "post_nav_page and section_nav_key"
                ) from exc
            rules.append((str(post), str(section)))
    return tuple(rules)


def parse_site_section_modules_file(path: Path) -> tuple[str, ...]:
    """Read ``path``: one dotted module path per line; ``#`` starts a comment; blank lines ignored."""

    text = path.read_text(encoding="utf-8")
    out: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        out.append(s)
    if not out:
        raise ValueError(
            f"site sections file {path} has no module paths "
            "(add non-empty, non-comment lines)"
        )
    return tuple(out)


def load_site_content(
    content_root: Path,
    *,
    section_modules: Sequence[str],
) -> SiteContentBundle:
    """Collect :func:`contribute_section` from each module in ``section_modules`` order."""

    names = tuple(section_modules)
    seen_keys: set[str] = set()
    out: list[SiteSectionContribution] = []

    for mod in load_site_section_modules(names):
        spec = mod.contribute_section(content_root)
        if not isinstance(spec, SiteSectionSpec):
            raise TypeError(
                f"{mod.__name__}: contribute_section must return a SiteSectionSpec "
                f"(got {type(spec).__name__})"
            )
        keys = set(spec.fragment)
        overlap = seen_keys & keys
        if overlap:
            raise ValueError(
                f"site content overlap on keys {sorted(overlap)!r}: "
                f"already set, then {mod.__name__} also returned them"
            )
        seen_keys |= keys
        out.append(SiteSectionContribution(module=mod, spec=spec))

    return SiteContentBundle(contributions=tuple(out))


def _merge_fragment_key(
    ctx: dict[str, object],
    *,
    module: ModuleType,
    fragment_key: str,
    value: object,
    rule: str,
) -> None:
    """Apply one ``content_merge`` rule for :func:`flattened_template_context`."""

    if rule == "spread":
        if not isinstance(value, dict):
            raise TypeError(
                f"{module.__name__}: content_merge[{fragment_key!r}] is 'spread' "
                f"but value is not a dict (got {type(value).__name__})"
            )
        ctx.update(value)
        return
    if rule == "assign":
        ctx[fragment_key] = value
        return
    if rule == "omit":
        return
    if rule.startswith("as:"):
        target = rule[3:]
        if not target:
            raise ValueError(
                f"{module.__name__}: content_merge[{fragment_key!r}] has invalid "
                f"rule {rule!r} (expected as:<template_key>)"
            )
        ctx[target] = value
        return
    raise ValueError(
        f"{module.__name__}: unknown content_merge rule {rule!r} for key "
        f"{fragment_key!r} (use spread, assign, omit, or as:<key>)"
    )


def flattened_template_context(bundle: SiteContentBundle) -> dict[str, object]:
    """Merge ``fragment`` keys in order using each section’s ``content_merge`` map.

    Rules (per fragment key):

    * ``assign`` — ``ctx[fragment_key] = value`` (default when a key is omitted from the map).
    * ``spread`` — ``ctx.update(value)`` (``value`` must be a ``dict``).
    * ``omit`` — skip for static pages (e.g. full rows used only for post HTML).
    * ``as:<name>`` — ``ctx[name] = value``.

    Later ``assign`` / ``as:`` keys overwrite existing ``ctx`` entries on collision.
    """

    ctx: dict[str, object] = {}
    for c in bundle.contributions:
        rules = c.spec.content_merge
        for fragment_key, value in c.spec.fragment.items():
            rule = rules.get(fragment_key, "assign")
            _merge_fragment_key(
                ctx,
                module=c.module,
                fragment_key=fragment_key,
                value=value,
                rule=rule,
            )
    return ctx


def site_owner_name(bundle: SiteContentBundle) -> str:
    """First ``site_owner_name`` string in contribution order."""

    for c in bundle.contributions:
        v = c.spec.fragment.get("site_owner_name")
        if v is not None:
            return str(v)
    raise ValueError(
        "site content: no section contributed site_owner_name "
        "(expected from the résumé section)"
    )


def writings_articles_for_posts(bundle: SiteContentBundle) -> list[dict]:
    """Full article rows (``writings_articles``) for per-post HTML, if any section supplied them."""

    for c in bundle.contributions:
        v = c.spec.fragment.get("writings_articles")
        if isinstance(v, list):
            return v
    return []
