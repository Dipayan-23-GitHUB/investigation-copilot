"""Load all twelve included Source Ledger workbooks into the configured dev database.
Run from the repository root after installing requirements. Use only the fictional sample data.
"""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.catalog import MODULES
from app.db import Base, engine, SessionLocal
from app.seed import seed_initial_data
from app.services.ingestion import ingest_file
SAMPLES = ROOT / "sample_data"

def main():
    Base.metadata.create_all(bind=engine)
    loaded = []
    with SessionLocal() as db:
        seed_initial_data(db)
        for module in MODULES:
            stem = Path(module["workbook"]).stem
            candidates = [SAMPLES / f"{stem}.xlsx"]
            source = next((p for p in candidates if p.exists()), None)
            if not source:
                raise FileNotFoundError(f"Sample workbook is missing: {module['workbook']}")
            row, duplicate = ingest_file(db, module_key=module["key"], filename=source.name, content=source.read_bytes(), header_row=5, tenant_id="demo")
            loaded.append((module["key"], row.row_count, row.sheet_count, duplicate, row.status))
    for key, rows, sheets, duplicate, status in loaded:
        print(f"{key:22s} rows={rows:3d} sheets={sheets} duplicate={duplicate} status={status}")
    print(f"Loaded/verified {len(loaded)} Source Ledger workbooks. All values are illustrative.")

if __name__ == "__main__":
    main()
