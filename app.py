import importlib
import sys
import os

# Ensure project root and OOP package can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import OOP.AppUI_OOP as app_ui_module


def main():
    # Reload UI module on each Streamlit rerun so edits apply without restarting Docker
    importlib.reload(app_ui_module)
    ui = app_ui_module.AppUI()
    ui.run()


if __name__ == "__main__":
    main()
