"""Regenerate LedgerFlow's code-native identity from the shared source."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().parents[2] / "native/assets/generate_identity.py"), run_name="__main__")
