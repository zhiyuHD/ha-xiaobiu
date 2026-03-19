from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

if str(SRC) not in sys.path:
  sys.path.insert(0, str(SRC))

from suning_biu_ha import main as package_main


if __name__ == "__main__":
  raise SystemExit(package_main())
