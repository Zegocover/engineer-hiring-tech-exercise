import sys
from pathlib import Path

# make `from crawler import ...` work however pytest is invoked (bare `pytest tests/` included)
sys.path.insert(0, str(Path(__file__).parent))
