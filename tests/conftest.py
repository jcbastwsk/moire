# Add the project root (one above tests/) to sys.path so `from tests.oracles.*`
# imports work when pytest is invoked from any cwd.

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
