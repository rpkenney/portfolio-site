"""Load YAML files from disk into plain dicts for ``ingest`` parsers."""

from __future__ import annotations

from pathlib import Path

import yaml


def load_yaml(path: Path) -> dict:
    """Read ``path`` as UTF-8 text; empty or whitespace-only file → ``{}``.

    If ``yaml.safe_load`` returns ``None``, returns ``{}`` (same as an empty file).
    """

    raw = path.read_text()
    if not raw.strip():
        return {}
    data = yaml.safe_load(raw)
    return data if data is not None else {}
