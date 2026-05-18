"""Load the entire dataset into a single DuckDB database for fast querying.

Usage:
    pip install duckdb
    python3 scripts/load_into_duckdb.py            # creates ./zs_challenge.duckdb
    python3 scripts/load_into_duckdb.py --db ./mydb.duckdb

After this, you can:
    duckdb zs_challenge.duckdb
    > SELECT COUNT(*) FROM orders;

DuckDB is a single-file analytical database (think SQLite for OLAP). It reads
.csv.gz directly and is dramatically faster than pandas for the order_items table.
"""

import argparse
from pathlib import Path

import duckdb  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

TABLES = [
    "calendar", "categories", "stores", "store_geo_mapping", "store_events",
    "products", "pricing_history", "customers", "promotions",
    "inventory_snapshots", "orders", "order_items", "returns",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(ROOT / "zs_challenge.duckdb"))
    ap.add_argument("--tables", nargs="*", default=TABLES)
    args = ap.parse_args()

    db_path = Path(args.db)
    if db_path.exists():
        print(f"removing existing {db_path}")
        db_path.unlink()

    con = duckdb.connect(str(db_path))
    for t in args.tables:
        src = DATA / f"{t}.csv.gz"
        if not src.exists():
            print(f"  ! {src} not found — skipping")
            continue
        print(f"  loading {t}...")
        # Empty-string convention for "current/ongoing" rows breaks DATE auto-detect; force VARCHAR.
        type_overrides = {
            "store_geo_mapping": {"effective_from": "VARCHAR", "effective_to": "VARCHAR"},
            "pricing_history":   {"effective_from": "VARCHAR", "effective_to": "VARCHAR"},
            "store_events":      {"start_date": "VARCHAR", "end_date": "VARCHAR"},
        }
        if t in type_overrides:
            con.execute(f"CREATE TABLE {t} AS SELECT * FROM read_csv_auto('{src}', header=true, types={type_overrides[t]});")
        else:
            con.execute(f"CREATE TABLE {t} AS SELECT * FROM read_csv_auto('{src}', header=true);")
        n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"    {t}: {n:,} rows")
    con.close()
    print(f"\nDone. Open with:  duckdb {db_path}")


if __name__ == "__main__":
    main()
