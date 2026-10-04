"""
Shared helpers for the dashboard.
---------------------------------
- Queries use parameterised placeholders (?) throughout.
- Paths are relative to the project root.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
SQL_DIR = (PROJECT_ROOT / "sql").resolve()
DEFAULT_DB = DATA_DIR / "retail.db"
CLEANED_CSV = DATA_DIR / "cleaned_orders.csv"
SAMPLE_CSV = DATA_DIR / "cleaned_orders_sample.csv"


def get_connection(db_path: Path | str = DEFAULT_DB) -> sqlite3.Connection:
    """Open a SQLite connection."""
    return sqlite3.connect(str(db_path))


def run_query(sql: str, params: tuple | list = (), db_path: Path | str = DEFAULT_DB) -> pd.DataFrame:
    """
    Run a SELECT query safely with parameters and return a DataFrame.
    Example:
        run_query("SELECT * FROM orders WHERE City = ? LIMIT 10", ("Bengaluru",))
    """
    with get_connection(db_path) as conn:
        return pd.read_sql_query(sql, conn, params=tuple(params))


def load_sql(filename: str) -> str:
    """Load a .sql file from the sql/ folder as text."""
    path = SQL_DIR / filename
    return path.read_text(encoding="utf-8")


def _table_exists(db_path: Path | str = DEFAULT_DB) -> bool:
    try:
        with get_connection(db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='orders'")
            return cur.fetchone() is not None
    except Exception:
        return False


def _orders_diagnostics(db_path: Path | str = DEFAULT_DB) -> tuple[int, str | None, str | None]:
    """Return (row count, min date, max date) for the orders table."""
    with get_connection(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM orders")
        n = cur.fetchone()[0]
        cur.execute("SELECT MIN(date(OrderDate)), MAX(date(OrderDate)) FROM orders")
        mn, mx = cur.fetchone()
    return n, mn, mx


def _build_from_csv(source: Path, db_path: Path = DEFAULT_DB) -> int:
    """Build the orders table from a CSV source. Returns rows written."""
    df = pd.read_csv(source, parse_dates=["OrderDate"])
    print(f"[ensure_db] parsed {len(df)} rows from {source.name} "
          f"({source.stat().st_size} bytes)")
    df["OrderDate"] = pd.to_datetime(df["OrderDate"]).dt.strftime("%Y-%m-%d")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with get_connection(db_path) as conn:
        df.to_sql("orders", conn, if_exists="replace", index=False)
        cur = conn.cursor()
        cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(OrderDate)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_city ON orders(City)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_restaurant ON orders(Restaurant)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_item ON orders(Item)")
        cur.execute("SELECT COUNT(*) FROM orders")
        n = cur.fetchone()[0]
    print(f"[ensure_db] orders table now has {n} rows")
    return n


def ensure_db() -> Path:
    """
    Make sure the SQLite DB exists with a usable orders table.
    - If data/retail.db with a non-empty orders table and valid dates exists, use it.
    - Else build it from data/cleaned_orders.csv if present.
    - Else build it from the committed data/cleaned_orders_sample.csv
      (stratified sample used for hosting).
    - Raises a detailed error naming row counts when nothing usable is found,
      so hosting logs show the data state instead of a downstream crash.
    """
    tried: list[str] = []
    if DEFAULT_DB.exists() and _table_exists():
        n, mn, mx = _orders_diagnostics()
        print(f"[ensure_db] existing orders table: {n} rows, {mn} to {mx}")
        if n > 0 and mn is not None and mx is not None:
            return DEFAULT_DB
        tried.append(f"existing db ({n} rows)")
    for source in (CLEANED_CSV, SAMPLE_CSV):
        if source.exists():
            n = _build_from_csv(source)
            _, mn, mx = _orders_diagnostics()
            if n > 0 and mn is not None and mx is not None:
                return DEFAULT_DB
            tried.append(f"{source.name} (built {n} rows)")
    if DEFAULT_DB.exists():
        return DEFAULT_DB
    raise RuntimeError(
        "No usable order data found. Tried: "
        + (", ".join(tried) if tried else "nothing")
        + ". Run locally: place the Swiggy file in data/ and run python -m src.data_prep."
    )


def get_filter_bounds(db_path: Path | str = DEFAULT_DB) -> dict:
    """Get min/max date and city list for sidebar filters."""
    sql = "SELECT MIN(date(OrderDate)) AS min_d, MAX(date(OrderDate)) AS max_d FROM orders"
    bounds = run_query(sql, db_path=db_path).iloc[0].to_dict()
    cities = run_query(
        "SELECT DISTINCT City FROM orders ORDER BY City", db_path=db_path
    )["City"].tolist()
    return {"min_date": bounds["min_d"], "max_date": bounds["max_d"], "cities": cities,
            "countries": cities}


def build_where_clause(start: str, end: str, cities: list[str]) -> tuple[str, tuple]:
    """
    Build a safe WHERE clause for dashboard filters.
    Returns (clause_sql, params). Uses ? placeholders only.
    Dates are inclusive. Cities list may be empty (= all).
    """
    clauses = ["date(OrderDate) BETWEEN date(?) AND date(?)"]
    params: list = [start, end]
    if cities:
        placeholders = ",".join(["?"] * len(cities))
        clauses.append(f"City IN ({placeholders})")
        params.extend(cities)
    return "WHERE " + " AND ".join(clauses), tuple(params)
