import sys
import os

# Ensure project root and OOP package can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from OOP.AppUI_OOP import AppUI


def main():
    ui = AppUI()
    ui.run()


if __name__ == "__main__":
    main()
