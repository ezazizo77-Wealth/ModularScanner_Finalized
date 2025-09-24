#!/usr/bin/env python3
import os
import datetime as dt
import duckdb
import pandas as pd
from pathlib import Path
from typing import List, Tuple

PARQUET_DIR = Path("ohlcv_parquet")
FILES = [
    PARQUET_DIR / "ohlcv_1h.parquet",
    PARQUET_DIR / "ohlcv_4h.parquet",
    PARQUET_DIR / "ohlcv_1d.parquet",
]
TF_ORDER = ["1h", "4h", "1d"]

def _bytes_mb(n: int) -> float:
    return n / (1024 * 1024)

def _list_extra_parquets() -> List[Path]:
    """Return any parquet files in the folder that are NOT the three canonical files."""
    if not PARQUET_DIR.exists():
        return []
    expected = {p.resolve() for p in FILES}
    extras = []
    for p in PARQUET_DIR.glob("*.parquet"):
        if p.resolve() not in expected:
            extras.append(p)
    return extras

def _per_file_snapshot(con: duckdb.DuckDBPyConnection, tf: str, path: Path) -> pd.Series:
    q = f"""
    SELECT
      COUNT(*)                           AS rows,
      COUNT(DISTINCT symbol)             AS distinct_symbols,
      MAX(ts)                            AS max_ts_utc,
      CAST(MAX(epoch_ms(ts)) AS BIGINT)  AS max_ts_ms
    FROM read_parquet('{path.as_posix()}')
    """
    row = con.sql(q).to_df().iloc[0]
    row["timeframe"] = tf
    return row

def _per_file_dupes(con: duckdb.DuckDBPyConnection, tf: str, path: Path) -> pd.Series:
    q = f"""
    WITH x AS (
      SELECT
        symbol, timeframe, ts,
        ROW_NUMBER() OVER (
          PARTITION BY symbol, timeframe, ts
          ORDER BY ts DESC
        ) AS rn
      FROM read_parquet('{path.as_posix()}')
    )
    SELECT
      SUM(CASE WHEN rn > 1 THEN 1 ELSE 0 END) AS extra_rows_due_to_dupes
    FROM x
    """
    row = con.sql(q).to_df().iloc[0]
    row["timeframe"] = tf
    return row

def main():
    # Basic presence checks
    missing = [p for p in FILES if not p.exists()]
    if missing:
        raise SystemExit(f"[ERR] Missing parquet files: {', '.join(str(m) for m in missing)}")

    # Warn if extra parquets exist (can cause false 'dupes' if globs are used elsewhere)
    extras = _list_extra_parquets()
    if extras:
        print("⚠️  Warning: extra parquet files detected (ignored by this check):")
        for p in sorted(extras):
            try:
                size_mb = _bytes_mb(os.path.getsize(p))
            except OSError:
                size_mb = 0.0
            print(f"   - {p}  ({size_mb:.2f} MB)")
        print()

    # Header
    now_utc = dt.datetime.utcnow()
    print("====== Post-Fetch Health Report ======")
    print(f"UTC now: {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}")

    # Size summary
    total_bytes = 0
    for p in FILES:
        try:
            total_bytes += os.path.getsize(p)
        except OSError:
            pass
    print(f"Parquet files: {len(FILES)} | Size: {total_bytes/(1024*1024):.1f} MB\n")

    con = duckdb.connect()

    # Snapshot per timeframe
    print("-- Snapshot per timeframe --")
    snap_rows = []
    for tf, path in zip(TF_ORDER, FILES):
        snap_rows.append(_per_file_snapshot(con, tf, path))
    snap_df = pd.DataFrame(snap_rows)[["timeframe", "rows", "distinct_symbols", "max_ts_utc", "max_ts_ms"]]
    # Ensure tz-aware UTC for printing
    snap_df["max_ts_utc"] = pd.to_datetime(snap_df["max_ts_utc"], utc=True)
    print(snap_df.to_string(index=False))

    # Dupes summary
    print("\n-- Dupes summary (expect 0) --")
    dup_rows = []
    for tf, path in zip(TF_ORDER, FILES):
        dup_rows.append(_per_file_dupes(con, tf, path))
    dup_df = pd.DataFrame(dup_rows)[["timeframe", "extra_rows_due_to_dupes"]].fillna(0).astype({"extra_rows_due_to_dupes": "int64"})
    print(dup_df.to_string(index=False))

    # Automated checks
    print("\n-- Automated Checks --")
    max_age_hours = {"1h": 2, "4h": 8, "1d": 48}
    now_utc_ts = pd.Timestamp.now(tz="UTC")

    for tf in TF_ORDER:
        row = snap_df[snap_df["timeframe"] == tf]
        if row.empty or pd.isna(row["max_ts_utc"].iloc[0]):
            print(f"⚠️ Freshness: no rows for {tf}")
            continue

        max_ts = pd.Timestamp(row["max_ts_utc"].iloc[0]).tz_convert("UTC")
        age_h = (now_utc_ts - max_ts).total_seconds() / 3600.0
        limit = max_age_hours[tf]
        if age_h <= limit:
            print(f"✅ Freshness: {tf} up to {max_ts} ({age_h:.2f}h ago) within {limit}h.")
        else:
            print(f"⚠️ Freshness: {tf} last candle at {max_ts} ({age_h:.2f}h ago) exceeds {limit}h.")

    extra_total = int(dup_df["extra_rows_due_to_dupes"].sum())
    if extra_total == 0:
        print("✅ Dupes: 0 extra rows across all timeframes.")
    else:
        print(f"❌ Dupes detected: {extra_total} extra rows. Recommend de-dup/compaction.")

    con.close()

if __name__ == "__main__":
    main()