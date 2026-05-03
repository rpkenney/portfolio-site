"""Bundle this frontend's CSS and copy non-CSS files into ``dist/``."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


def _site_ui_path(static_root: Path) -> Path:
    return static_root / "site_ui.json"


def _load_site_ui(static_root: Path) -> dict[str, Any]:
    path = _site_ui_path(static_root)
    return json.loads(path.read_text(encoding="utf-8"))


def _ms_to_transition_duration(ms: int) -> str:
    s = ms / 1000
    if s == int(s):
        return f"{int(s)}s"
    return f"{s:g}s"


def css_token_replacements(static_root: Path) -> dict[str, str]:
    """Map ``__UI_*__`` substrings in ``static/css/*.css`` to concrete values from ``site_ui.json``."""

    c = _load_site_ui(static_root)
    open_ms = int(c["carouselOpenHeightMs"])
    close_ms = int(c["carouselCloseHeightMs"])
    nav_max = int(c["siteNavMaxWidthPx"])
    return {
        "__UI_RESUME_MODAL_MAX__": str(int(c["resumeModalMaxWidthPx"])),
        "__UI_SITE_NAV_MAX__": str(nav_max),
        "__UI_SITE_NAV_DESKTOP_MIN__": str(nav_max + 1),
        "__UI_CAROUSEL_OPEN__": _ms_to_transition_duration(open_ms),
        "__UI_CAROUSEL_CLOSE__": _ms_to_transition_duration(close_ms),
    }


def apply_ui_tokens_to_css(static_root: Path, css: str) -> str:
    """Expand UI placeholders for the concat CSS bundle."""

    for token, value in css_token_replacements(static_root).items():
        if token not in css:
            continue
        css = css.replace(token, value)
    return css


def css_bundle_source_paths(static_root: Path) -> tuple[Path, ...]:
    """All ``static/css/*.css`` in lexicographic order by filename (use ``00_``… prefixes for cascade)."""

    src_dir = static_root / "css"
    return tuple(sorted(src_dir.glob("*.css"), key=lambda p: p.name))


def copy_static_tree(static_root: Path, out_dir: Path) -> None:
    """Copy files under ``static_root`` into ``out_dir`` (skips ``css/``; CSS is bundled separately)."""

    if not static_root.is_dir():
        return
    for path in static_root.rglob("*"):
        if path.is_file():
            rel = path.relative_to(static_root)
            if rel.parts and rel.parts[0] == "css":
                continue
            dest = out_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)


def build_css_bundle(static_root: Path, out_dir: Path) -> None:
    """Concatenate ``static/css/*.css`` (sorted by filename) into ``dist/site.css``."""

    src_dir = static_root / "css"
    if not src_dir.is_dir():
        raise FileNotFoundError(f"missing css sources dir: {src_dir}")
    if not _site_ui_path(static_root).is_file():
        raise FileNotFoundError(f"missing UI config: {_site_ui_path(static_root)}")

    order = css_bundle_source_paths(static_root)
    if not order:
        raise ValueError(f"no *.css files under {src_dir}")
    parts: list[str] = []
    for p in order:
        parts.append(apply_ui_tokens_to_css(static_root, p.read_text()))
    bundled = "\n".join(s.rstrip() for s in parts).rstrip() + "\n"
    for token in css_token_replacements(static_root):
        if token in bundled:
            raise ValueError(f"site.css still contains unreplaced token {token!r}")
    (out_dir / "site.css").write_text(bundled)
