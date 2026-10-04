"""
Data preparation for the Swiggy food orders dataset.
----------------------------------------------------
1. Finds the raw Swiggy file in data/ (TXT tab-separated or CSV).
2. Loads it with pandas and assigns column names.
3. Cleans invalid prices, missing restaurants/items/cities and bad dates.
4. Adds Revenue (one row is treated as one order line, Revenue = Price).
5. Saves the result to SQLite table orders.
6. Prints row counts before and after cleaning.

Usage from the project root:
    python -m src.data_prep
    python -m src.data_prep --raw "data/SWIGGY DATA.txt" --db "data/retail.db"
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_DB = DATA_DIR / "retail.db"

# Expected columns in the Swiggy file (tab-separated, no header in the source file)
SWIGGY_COLUMNS = [
    "State", "City", "OrderDate", "DayOfWeek", "Quarter", "WeekNo",
    "Restaurant", "Area", "Category", "Item", "VegType",
    "Price", "Rating", "RatingCount",
]

KNOWN_RAW_NAMES = [
    "SWIGGY DATA.txt",
    "swiggy.csv",
    "swiggy_data.csv",
    "SWIGGY DATA.csv",
    "food_delivery_dataset.csv",
]


def find_raw_file(explicit: str | None = None) -> Path:
    """Locate the raw dataset file in data/."""
    if explicit:
        p = (PROJECT_ROOT / explicit).resolve() if not Path(explicit).is_absolute() else Path(explicit)
        if not p.exists():
            raise FileNotFoundError(f"Raw file not found: {p}")
        return p

    for name in KNOWN_RAW_NAMES:
        candidate = DATA_DIR / name
        if candidate.exists():
            return candidate

    # Fallback: prefer the Swiggy txt, then any txt/csv
    for pattern in ("*SWIGGY*.txt", "*swiggy*.csv", "*.txt", "*.csv"):
        matches = sorted([p for p in DATA_DIR.glob(pattern) if p.name != "cleaned_sales.csv"])
        if matches:
            # Skip tiny placeholder files
            for m in matches:
                if m.stat().st_size > 10000:
                    return m
            return matches[0]

    raise FileNotFoundError(
        "No raw Swiggy file found in data/. "
        "Place the Swiggy CSV/TXT in data/ and re-run this script."
    )


def load_raw(path: Path) -> pd.DataFrame:
    """Load the Swiggy TXT/CSV into a DataFrame with named columns."""
    print(f"[1/5] Loading raw file: {path.name} ...")
    if path.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(path, engine="openpyxl")
        if len(df.columns) == len(SWIGGY_COLUMNS) and "State" not in str(df.columns[0]):
            df.columns = SWIGGY_COLUMNS
    else:
        # Swiggy file is tab-separated without a header row. Item names contain
        # quotes and commas, so disable quoting and skip malformed lines.
        import csv
        try:
            df = pd.read_csv(path, sep="\t", header=None, engine="python",
                             encoding="utf-8", quoting=csv.QUOTE_NONE,
                             on_bad_lines="skip")
        except Exception:
            df = pd.read_csv(path, sep="\t", header=None, engine="python",
                             encoding="unicode_escape", quoting=csv.QUOTE_NONE,
                             on_bad_lines="skip")
        # If pandas picked up a header row that matches data, keep as is; else assign
        if df.shape[1] == len(SWIGGY_COLUMNS):
            # Detect header: first cell would be 'Karnataka' style state, not 'State'
            first = str(df.iloc[0, 0]).strip().lower()
            if first not in ("state", "karnataka", "maharashtra", "tamil nadu", "delhi", "telangana"):
                pass
            df.columns = SWIGGY_COLUMNS
        else:
            df.columns = [c.strip() for c in df.columns]
    print(f"      Raw rows: {len(df):,} | columns: {list(df.columns)}")
    return df


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Cleaning applied:
    1. Drop rows missing Restaurant, Item or City (needed for all analyses).
    2. Drop Price <= 0 or missing (revenue would be invalid).
    3. Parse OrderDate, drop unreadable dates.
    4. Revenue = Price (each row is one order line, quantity of 1).
    Note: the Swiggy file has no CustomerID and no cancellation flag,
    so customer-level retention cannot be computed. Restaurant and item
    level analysis is used instead.
    """
    stats = {"raw_rows": len(df)}
    print(f"[2/5] Starting cleaning from {len(df):,} rows...")

    df = df.rename(columns={c: c.strip() for c in df.columns})
    required = ["Restaurant", "Item", "City", "OrderDate", "Price"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing expected columns {missing}. Found: {list(df.columns)}")

    before = len(df)
    for col in ("Restaurant", "Item", "City"):
        df[col] = df[col].astype(str).str.strip()
        df = df[(df[col].notna()) & (df[col] != "") & (df[col].str.lower() != "nan")].copy()
    stats["missing_key_removed"] = before - len(df)
    print(f"      - Rows missing Restaurant/Item/City removed: {stats['missing_key_removed']:,}")

    before = len(df)
    df["Price"] = pd.to_numeric(df["Price"], errors="coerce")
    df["Rating"] = pd.to_numeric(df.get("Rating"), errors="coerce")
    df["RatingCount"] = pd.to_numeric(df.get("RatingCount"), errors="coerce").fillna(0).astype(int)
    df = df[(df["Price"].notna()) & (df["Price"] > 0)].copy()
    stats["bad_price_removed"] = before - len(df)
    print(f"      - Rows with missing or non-positive Price removed: {stats['bad_price_removed']:,}")

    before = len(df)
    df["OrderDate"] = pd.to_datetime(df["OrderDate"], errors="coerce")
    df = df[df["OrderDate"].notna()].copy()
    stats["bad_date_removed"] = before - len(df)
    print(f"      - Rows with unreadable dates removed: {stats['bad_date_removed']:,}")

    df["Revenue"] = df["Price"]
    for col in ("State", "City", "Area", "Category", "Item", "Restaurant", "VegType", "DayOfWeek", "Quarter"):
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    df = df.sort_values("OrderDate").reset_index(drop=True)
    stats["clean_rows"] = len(df)
    stats["pct_kept"] = round(100 * len(df) / stats["raw_rows"], 2) if stats["raw_rows"] else 0
    print(f"[3/5] Cleaning done: {stats['clean_rows']:,} rows kept ({stats['pct_kept']}% of raw).")
    return df, stats


def save_to_sqlite(df: pd.DataFrame, db_path: Path) -> None:
    """Save clean DataFrame into SQLite table called orders."""
    print(f"[4/5] Saving to SQLite: {db_path} (table=orders) ...")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    df_to_save = df.copy()
    df_to_save["OrderDate"] = pd.to_datetime(df_to_save["OrderDate"]).dt.strftime("%Y-%m-%d")

    conn = sqlite3.connect(db_path)
    try:
        df_to_save.to_sql("orders", conn, if_exists="replace", index=False)
        cur = conn.cursor()
        cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(OrderDate)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_city ON orders(City)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_restaurant ON orders(Restaurant)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_item ON orders(Item)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_category ON orders(Category)")
        conn.commit()
        count = cur.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        print(f"      SQLite table 'orders' now has {count:,} rows.")
    finally:
        conn.close()


def print_summary(stats: dict, df: pd.DataFrame) -> None:
    """Print row counts and totals from the cleaning run."""
    print("\n" + "=" * 60)
    print("CLEANING SUMMARY")
    print("=" * 60)
    print(f"Raw rows:                   {stats['raw_rows']:,}")
    print(f"Missing key rows removed:   {stats['missing_key_removed']:,}")
    print(f"Bad price rows removed:     {stats['bad_price_removed']:,}")
    print(f"Bad date rows removed:      {stats['bad_date_removed']:,}")
    print(f"Clean rows:                 {stats['clean_rows']:,} ({stats['pct_kept']}% kept)")
    if len(df):
        print(f"Date range: {df['OrderDate'].min().date()} to {df['OrderDate'].max().date()}")
        print(f"Total revenue (clean): Rs.{df['Revenue'].sum():,.2f}")
        print(f"Unique restaurants: {df['Restaurant'].nunique():,}")
        print(f"Unique items: {df['Item'].nunique():,}")
        print(f"Cities: {sorted(df['City'].unique().tolist())}")
    print("=" * 60 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean Swiggy data into SQLite.")
    parser.add_argument("--raw", default=None, help="Relative path to raw file, e.g. data/SWIGGY DATA.txt")
    parser.add_argument("--db", default=str(DEFAULT_DB.relative_to(PROJECT_ROOT)),
                        help="Relative output DB path (default: data/retail.db)")
    args = parser.parse_args()

    raw_path = find_raw_file(args.raw)
    db_path = (PROJECT_ROOT / args.db).resolve() if not Path(args.db).is_absolute() else Path(args.db)

    df_raw = load_raw(raw_path)
    df_clean, stats = clean(df_raw)
    save_to_sqlite(df_clean, db_path)
    print_summary(stats, df_clean)
    print("[5/5] Done. The orders table is ready for analysis.")
    print(f"      DB location: {db_path}")


if __name__ == "__main__":
    sys.exit(main())
