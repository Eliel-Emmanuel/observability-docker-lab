import sys
from pathlib import Path

# Rend main.py importable depuis les tests.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
