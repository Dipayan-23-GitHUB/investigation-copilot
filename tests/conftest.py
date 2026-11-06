import os
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DATABASE_URL", f"sqlite:///{(ROOT / 'data' / 'test_api.db').as_posix()}")
os.environ.setdefault("APP_ENV", "testing")
os.environ.setdefault("AUTO_CREATE_DB", "true")
os.environ.setdefault("API_ACCESS_KEY", "")
