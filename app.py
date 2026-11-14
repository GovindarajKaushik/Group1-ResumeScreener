import importlib
import os
import sys

# Ensure project root and OOP package can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import OOP.ui.ui_theme as ui_theme_module
import OOP.ui.ui_views as ui_views_module
import OOP.AppUI_OOP as app_ui_module

_WATCHED_MODULES = (ui_theme_module, ui_views_module, app_ui_module)


def _reload_if_modified():
    # Store mtimes on sys so they persist across Streamlit script reruns
    last_mtimes = getattr(sys, "_ra_last_mtimes", None)
    current_mtimes = {}
    changed = last_mtimes is None

    for mod in _WATCHED_MODULES:
        try:
            mtime = os.path.getmtime(mod.__file__)
            current_mtimes[mod.__name__] = mtime
            if last_mtimes is not None and last_mtimes.get(mod.__name__) != mtime:
                changed = True
        except OSError:
            pass

    if changed:
        for mod in _WATCHED_MODULES:
            importlib.reload(mod)
        setattr(sys, "_ra_last_mtimes", current_mtimes)


def main():
    _reload_if_modified()
    ui = app_ui_module.AppUI()
    ui.run()


if __name__ == "__main__":
    main()
