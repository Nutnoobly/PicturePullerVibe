"""
Main CLI entry point for Picture Puller Vibe.
Provides convenient root-level invocation for running the picture puller.
"""

import sys
from pathlib import Path

# Add src to pythonpath so picture_puller can be imported directly
src_dir = Path(__file__).resolve().parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from picture_puller.cli import app  # pylint: disable=wrong-import-position

if __name__ == "__main__":
    app()
