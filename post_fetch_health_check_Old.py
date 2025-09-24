import duckdb as d, pandas as pd, time, os, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = Path("ohlcv_parquet")
OUT_DIR = Path("fetch_snapshots")
OUT_DIR.mkdir(exist_ok=True, parents=True)
now_utc = datetime.now(timezone.utc)

timeframes = ["1h","4h","1d"]
files = {tf: BASE / f"ohlcv_{tf}.parquet" for tf in timeframes}
present = {tf: p for tf,p in files.items() if p.exists()}

def fmt_bytes(n):
    for u in ["B","KB","MB","GB","TB"]:
        if n < 1024: return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} PB"

snap_rows, dupe_rows = [], []
total_bytes = 0
total_files = 0

for tf, path in present.items():
    total_files += 1
    total_bytes += path.stat().st_size

    q_snap = f"""
    select
      '{tf}' as timeframe,
      count(*) as rows,
      count(distinct symbol) as distinct_symbols,
      max(timestamp) as max_ts_utc,
      cast(epoch_ms(max(timestamp)) as bigint) as max_ts_ms
    from read_parquet('{path.as_posix()}')
    """
    snap_rows.append(d.query(q_snap).to_df().iloc[0])

    q_dupes = f"""
    with base as (
      select symbol, timestamp
      from read_parquet('{path.as_posix()}')
    ),
    cnt as (
      select symbol, timestamp, count(*) c
      from base
      group by 1,2
    )
    select '{tf}' as timeframe, coalesce(sum(c-1),0) as extra_rows_due_to_dupes
    from cnt
    where c > 1
    """
    dupe_rows.append(d.query(q_dupes).to_df().iloc[0])

snap = pd.DataFrame(snap_rows) if snap_rows else pd.DataFrame(
    columns=["timeframe","rows","distinct_symbols","max_ts_utc","max_ts_ms"]
)
dupes = pd.DataFrame(dupe_rows) if dupe_rows else pd.DataFrame(
    columns=["timeframe","extra_rows_due_to_dupes"]
)

freshness_hrs = {'1h': 2, '4h': 8, '1d': 48}
alerts = []

def fmt_dt(dt):
    if hasattr(dt, "to_pydatetime"):
        dt = dt.to_pydatetime()
    return dt.replace(tzinfo=timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")

for tf in timeframes:
    row = snap[snap["timeframe"] == tf]
    if row.empty:
        alerts.append(f"⚠️ Missing timeframe file: {tf} ({files[tf]})")
        continue
    last_dt = row.iloc[0]["max_ts_utc"]
    age = datetime.now(timezone.utc) - last_dt.to_pydatetime().replace(tzinfo=timezone.utc)
    lim = timedelta(hours=freshness_hrs[tf])
    if age > lim:
        alerts.append(f"⚠️ Freshness: {tf} last candle at {fmt_dt(last_dt)} ({age} ago) exceeds {freshness_hrs[tf]}h.")
    else:
        alerts.append(f"✅ Freshness: {tf} up to {fmt_dt(last_dt)} ({age} ago) within {freshness_hrs[tf]}h.")

if not dupes.empty:
    total_dupes = int(dupes["extra_rows_due_to_dupes"].fillna(0).sum())
    alerts.append("✅ Dupes: 0 extra rows across all timeframes." if total_dupes == 0
                  else f"❌ Dupes detected: {total_dupes} extra rows. Recommend de-dup/compaction.")
else:
    alerts.append("✅ Dupes: none detected (table empty).")

ts = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
snap_path = OUT_DIR / f"snapshot_{ts}.csv"
dupe_path = OUT_DIR / f"dupes_{ts}.csv"
snap.to_csv(snap_path, index=False)
dupes.to_csv(dupe_path, index=False)

print("\n====== Post-Fetch Health Report ======")
print(f"UTC now: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S %Z')}")
print(f"Parquet files: {total_files} | Size: {fmt_bytes(total_bytes)}")
print("\n-- Snapshot per timeframe --")
print(snap.to_string(index=False))
print("\n-- Dupes summary (expect 0) --")
print(dupes.to_string(index=False) if len(dupes) else "(no dupe rows)")
print("\n-- Automated Checks --")
for a in alerts: print(a)
print(f"\nSaved: {snap_path}")
print(f"Saved: {dupe_path}")

bad = any(a.startswith("❌") for a in alerts)
sys.exit(1 if bad else 0)
PY