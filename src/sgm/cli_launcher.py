import os
import sys

# Ensure src/ is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sgm.cli import app

if __name__ == "__main__":
    app()
