#!/usr/bin/env python3
"""Build entrypoint: **required** frontend subcommand (``jinja``, ``list``, …).

**Registered frontends** — each ``FRONTEND_MODULES`` value is an importable module that
must define:

- ``register_build_subparser(subparsers, *, command_name: str) -> None`` — add one
  subparser (named ``command_name``) and attach CLI flags. Convention: set short
  help from module-level ``FRONTEND_SUBCOMMAND_HELP`` or pass ``help=`` to
  ``add_parser``.
- ``run_build(args: argparse.Namespace) -> None`` — run the build for that namespace.

``build.py`` loads them with ``importlib`` only (see ``_LOADED_FRONTENDS``).
"""

from __future__ import annotations

import argparse
import importlib
import sys

# Subcommand name → importable module (see module docstring: hooks + run_build).
FRONTEND_MODULES: dict[str, str] = {
    "jinja": "frontends.jinja.cli",
}

# Filled in ``_register_frontend_subparsers`` so ``main`` does not import twice.
_LOADED_FRONTENDS: dict[str, object] = {}


def _list_frontends() -> None:
    for key in sorted(FRONTEND_MODULES):
        print(f"{key}\t{FRONTEND_MODULES[key]}")
    print(
        "# Short names = FRONTEND_MODULES. See build.py module docstring for the hook contract.",
        file=sys.stdout,
    )


def _register_frontend_subparsers(sub) -> None:
    _LOADED_FRONTENDS.clear()
    for name, modpath in sorted(FRONTEND_MODULES.items()):
        mod = importlib.import_module(modpath)
        _LOADED_FRONTENDS[name] = mod
        reg = getattr(mod, "register_build_subparser", None)
        if not callable(reg):
            sys.exit(
                f"build.py: module {modpath!r} (key {name!r}) "
                "must define register_build_subparser(subparsers, *, command_name=...)"
            )
        reg(sub, command_name=name)


def _build_root_parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="build.py",
        description="Resume site build drivers. Choose a frontend subcommand.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  %(prog)s jinja\n"
            "  %(prog)s jinja -o /tmp/out\n"
            "  %(prog)s jinja -h\n"
            "  %(prog)s list\n"
        ),
    )
    sub = root.add_subparsers(
        dest="frontend",
        metavar="COMMAND",
        help="frontend to run (required)",
        required=True,
    )
    _register_frontend_subparsers(sub)
    sub.add_parser("list", help="print configured frontend names and modules")
    return root


def main() -> None:
    argv = sys.argv[1:]
    root = _build_root_parser()

    if not argv:
        root.print_help()
        sys.exit(2)

    args = root.parse_args(argv)
    if args.frontend == "list":
        _list_frontends()
        return

    mod = _LOADED_FRONTENDS.get(args.frontend)
    if mod is None:
        sys.exit(
            f"build.py: unknown frontend subcommand {args.frontend!r} "
            f"(expected one of: {', '.join(sorted(FRONTEND_MODULES))}, list)"
        )
    run = getattr(mod, "run_build", None)
    if not callable(run):
        sys.exit(
            f"build.py: module {FRONTEND_MODULES[args.frontend]!r} must define run_build(args)"
        )
    run(args)


if __name__ == "__main__":
    main()
