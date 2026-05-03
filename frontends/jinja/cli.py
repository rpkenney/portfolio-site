"""CLI: load content, render Jinja, emit ``dist/``.

Invoked only via ``python build.py jinja`` using the hooks in ``build.py``’s module
docstring (:func:`register_build_subparser`, :func:`run_build`).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .env import create_env
from .site_build import run_jinja_site_build
from .site_content import load_site_content, parse_site_section_modules_file

# frontends/jinja/cli.py → repo root is three levels up
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FRONTEND_ROOT = Path(__file__).resolve().parent
STATIC_ROOT = FRONTEND_ROOT / "static"

# Shown next to the subcommand name in ``python build.py -h`` (registered frontends).
FRONTEND_SUBCOMMAND_HELP = "Static HTML site (Jinja templates + bundled CSS/JS)"

# Portfolio/writings placeholder; flip to False or delete the feature when ready.
UNDER_CONSTRUCTION = True


def register_build_subparser(subparsers, *, command_name: str) -> None:
    """``build.py`` hook: add the Jinja subparser (see ``build.py`` module docstring)."""

    root = REPO_ROOT
    p = subparsers.add_parser(
        command_name,
        help=FRONTEND_SUBCOMMAND_HELP,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--content-root",
        type=Path,
        default=root,
        help="Root directory for content/ layout (default: repository root).",
    )
    p.add_argument(
        "--sections-file",
        type=Path,
        metavar="PATH",
        help=(
            "Text file: one dotted section module per line (# comments and blank lines ok). "
            "Mutually exclusive with --section."
        ),
    )
    p.add_argument(
        "--section",
        action="append",
        dest="sections",
        default=None,
        metavar="MODULE",
        help=(
            "Site content section module (under frontends.jinja.sections.*). "
            "Repeat to set order. Mutually exclusive with --sections-file."
        ),
    )
    p.add_argument("-o", "--output", type=Path, default=root / "dist")


def _resolve_section_modules(args: argparse.Namespace) -> tuple[str, ...]:
    has_file = args.sections_file is not None
    has_cli = bool(args.sections)
    if has_file and has_cli:
        print(
            "jinja: use either --sections-file or --section, not both",
            file=sys.stderr,
        )
        raise SystemExit(2)
    if has_file:
        return parse_site_section_modules_file(args.sections_file)
    if has_cli:
        return tuple(args.sections)
    print(
        "jinja: specify --sections-file PATH or at least one --section MODULE "
        "(see content/site_sections.txt)",
        file=sys.stderr,
    )
    raise SystemExit(2)


def run_jinja_build(args: argparse.Namespace) -> None:
    """Emit ``dist/`` (or ``args.output``) from parsed Jinja CLI arguments."""

    section_modules = _resolve_section_modules(args)
    try:
        bundle = load_site_content(
            args.content_root,
            section_modules=section_modules,
        )
    except (ValueError, OSError) as exc:
        print(f"jinja: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    site_ui_path = STATIC_ROOT / "site_ui.json"
    try:
        site_ui_json = site_ui_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"jinja: missing or unreadable {site_ui_path}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    env = create_env(
        extra_globals={"site_ui_config_json": site_ui_json},
    )
    run_jinja_site_build(
        env,
        args.output,
        STATIC_ROOT,
        bundle,
        under_construction=UNDER_CONSTRUCTION,
    )


def run_build(args: argparse.Namespace) -> None:
    """``build.py`` hook; same as :func:`run_jinja_build`."""

    run_jinja_build(args)
