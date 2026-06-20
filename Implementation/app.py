#!/usr/bin/env python3
"""Legacy entry point — use start_portal.py instead."""

import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    script = Path(__file__).resolve().parent / "start_portal.py"
    sys.exit(subprocess.call([sys.executable, str(script)]))
