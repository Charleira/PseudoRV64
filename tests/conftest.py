import os
import sys
from pathlib import Path

sys.path.insert(
    0, os.environ.get("MICROC_CODEGEN_DIR", str(Path(__file__).resolve().parents[1]))
)
import load_previous
