"""Site output adapters; each subpackage is one frontend (HTML/Jinja, …).

New frontends: implement the ``register_build_subparser`` / ``run_build`` hooks (see
``build.py`` module docstring), add the module path to ``FRONTEND_MODULES``, then
``python build.py list`` will show it.
"""
