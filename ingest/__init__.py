"""YAML/Markdown → validated models (résumé, portfolio, writings).

Load mappings with ``ingest.yaml_io.load_yaml``; parse with ``parse_resume`` /
``parse_projects`` / ``parse_writings_index``. Consumed by ``frontends.jinja``;
site entry: ``python build.py jinja``.
"""
