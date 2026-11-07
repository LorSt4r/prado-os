"""
Desktop application launcher entry point for PyInstaller standalone bundles.
"""

import sys
from prado.ui.tray import run_tray_app

if __name__ == "__main__":
    sys.exit(run_tray_app())
