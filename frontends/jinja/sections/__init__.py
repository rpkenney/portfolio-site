"""Per-area content and build metadata for the Jinja static site.

**Section hook**

``contribute_section(content_root: pathlib.Path) -> SiteSectionSpec``

Return a :class:`~frontends.jinja.site_content.SiteSectionSpec` (see that class for fields).
``content_root`` is the ``--content-root`` directory (usually the repo root). Fragment keys
must not overlap across sections. See :func:`~frontends.jinja.site_content.load_site_content`.

**``SiteSectionSpec`` fields (all optional except ``fragment``)**

* ``fragment`` — ``dict[str, object]`` merged into Jinja context (subject to ``content_merge``).
* ``content_merge`` — per fragment key, how :func:`~frontends.jinja.site_content.flattened_template_context`
  merges: ``assign`` (default), ``spread``, ``omit``, or ``as:<template_key>``.
* ``route_overrides`` — patch static route discovery (template base → ``nav_page`` / ``page_title``).
* ``nav_post_rules`` — tuple of ``{"post_nav_page", "section_nav_key"}`` for subpage nav hrefs.
* ``emit_only_templates`` — Jinja filenames not promoted to one static route each.
* ``emit_site_pages`` — optional ``callable`` run after static pages (receives ``env``, ``out_dir``,
  ``bundle``, ``under_construction``, ``nav_bar_items``, ``post_rules``).

**Extra static pages**

Use ``emit_site_pages`` on the spec for URLs not covered by template-derived static routes
(e.g. per-slug paths under ``writings/<slug>/``). The orchestrator calls it in ``site_sections``
order.

**Adding a section**

1. Add ``yoursection.py`` beside ``resume.py`` / ``portfolio.py`` / ``writings.py``.
2. Implement ``contribute_section`` (signature above).
3. Under ``content_root``, resolve input files in that module (see e.g. ``_RESUME_YAML`` in
   :mod:`frontends.jinja.sections.resume`).
4. Set ``content_merge`` on the spec for any fragment key that is not a plain ``assign``.
5. Add the module’s dotted path to ``content/site_sections.txt`` (or pass ``--section``).

Section modules are loaded by :func:`~frontends.jinja.site_content.load_site_section_modules`.
"""
