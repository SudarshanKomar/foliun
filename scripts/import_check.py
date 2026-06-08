import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import foliun.main
import foliun.worker

print("imports ok")
