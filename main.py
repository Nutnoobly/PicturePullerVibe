import sys
from pathlib import Path

# Add src to pythonpath
src_dir = Path(__file__).resolve().parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from picture_puller.cli import app

if __name__ == "__main__":
    app()
