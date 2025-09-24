"""
fetch_ohlcv_to_parquet_v4.0.0.py
Version: 3.1.0
Author: A-Team (Aziz + Amy)

🔍 Description:
High-performance OHLCV fetcher with concurrent downloads, incremental updates,
retry logic, and safe file writes. Compatible with analyze_slope_from_parquet.py.

✨ Features:
- Concurrent fetching with ThreadPoolExecutor
- Incremental updates (since last timestamp)
- Retry with exponential backoff
- Safe concurrent writes (gather → merge → single write)
- Top-N symbols by volume
- Rich progress tracking
- 🆕 Canonical OHLCV normalization (Triad standard)
- 🆕 Standardized ts column (UTC datetime) for cross-timeframe analysis
- 🆕 Robust column detection and data validation
"""

import ccxt
import pandas as pd
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import typer
import rich
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
import time
import logging
import random
from typing import Dict, Optional, List

# === Canonical OHLCV normalizer (Triad standard) ===
_TIME_COL_CANDIDATES = ["ts", "timestamp", "time", "open_time", "datetime", "date"]

def _find_time_col(cols):
    low = [c.lower() for c in cols]
    for name in _TIME_COL_CANDIDATES:
        if name in low:
            return cols[low.index(name)]
    return None

def _to_datetime_utc(s: pd.Series) -> pd.Series:
    # already datetime
    if pd.api.types.is_datetime64_any_dtype(s):
        return pd.to_datetime(s, utc=True)
    # numeric epoch sec/ms
    if pd.api.types.is_integer_dtype(s) or pd.api.types.is_float_dtype(s):
        unit = "ms" if s.dropna().astype(float).abs().median() > 1e11 else "s"
        return pd.to_datetime(s, unit=unit, utc=True)
    # strings
    return pd.to_datetime(s, utc=True, errors="coerce")

def standardize_ohlcv(df: pd.DataFrame, symbol: str, timeframe: str) -> pd.DataFrame:
    """
    Returns a DataFrame with columns:
      symbol | timeframe | ts | open | high | low | close | volume
    where ts is UTC datetime.
    """
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=["symbol","timeframe","ts","open","high","low","close","volume"])

    df = df.copy()

    # 1) time -> ts (UTC)
    tcol = _find_time_col(df.columns)
    if tcol is None:
        raise ValueError("No time column found (expected one of: ts/timestamp/time/open_time/datetime/date)")
    df["ts"] = _to_datetime_utc(df[tcol])

    # 2) rename price/volume columns to canonical names
    lower = {c.lower(): c for c in df.columns}
    def pick(*aliases):
        for a in aliases:
            if a in lower:
                return lower[a]
        return None

    cols_map = {}
    for target, aliases in {
        "open":  ("open","o","openprice"),
        "high":  ("high","h","highprice"),
        "low":   ("low","l","lowprice"),
        "close": ("close","c","closeprice","price","last"),
        "volume":("volume","vol","base_volume","qty","quantity","amount"),
    }.items():
        src = pick(*aliases)
        if src: cols_map[src] = target

    df = df.rename(columns=cols_map)

    # 3) ensure required columns present
    required = ["open","high","low","close","volume","ts"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns after normalization: {missing}")

    # 4) add symbol & timeframe, order & types
    df["symbol"] = symbol
    df["timeframe"] = timeframe
    df = df.sort_values("ts").reset_index(drop=True)
    df = df[["symbol","timeframe","ts","open","high","low","close","volume"]]

    # enforce numeric
    for c in ["open","high","low","close","volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["ts"] = pd.to_datetime(df["ts"], utc=True)

    # drop rows without ts or close
    df = df.dropna(subset=["ts","close"])
    return df
# === end normalizer ===

app = typer.Typer()

# Lazy client creation
_exchange = None
def get_exchange():
    global _exchange
    if _exchange is None:
        _exchange = ccxt.binance({
            'enableRateLimit': True,
            'rateLimit': 200,
            'timeout': 20000,
            'options': {'defaultType': 'spot'}
        })
    return _exchange

# ========== LOGGING ==========
logging.basicConfig(filename="fetch_ohlcv.log", level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)
# =============================

def retry_with_backoff(fn, max_retries=3, base_delay=1.0):
    for attempt in range(max_retries):
        try:
            return fn()
        except (ccxt.NetworkError, ccxt.DDoSProtection, ccxt.ExchangeError) as e:
            wait = base_delay * (2 ** attempt) + random.uniform(0, 1)
            log.warning(f"Retry {attempt + 1} failed: {e}. Waiting {wait:.2f}s")
            time.sleep(wait)
    raise Exception(f"Failed after {max_retries} retries")

def fetch_symbols(top_n: int = 0) -> List[str]:
    """Fetch top N USDT pairs by 24h volume, excluding leveraged tokens."""
    exchange = get_exchange()
    try:
        tickers = exchange.fetch_tickers()
        pairs = []
        for k, v in tickers.items():
            if (k.endswith('/USDT') and 
                not k.startswith('1000') and
                not any(x in k for x in ['UP/', 'DOWN/', 'BULL/', 'BEAR/']) and
                v.get('quoteVolume') is not None):
                try:
                    volume = float(v['quoteVolume'])
                    if volume > 0:
                        pairs.append((k, volume))
                except (ValueError, TypeError):
                    continue
        
        sorted_pairs = sorted(pairs, key=lambda x: x[1], reverse=True)
        symbols = [s[0] for s in sorted_pairs[:top_n]] if top_n else [s[0] for s in sorted_pairs]
        log.info(f"Fetched {len(symbols)} symbols (top {top_n if top_n else 'all'})")
        return symbols
    except Exception as e:
        log.error(f"Failed to fetch symbols: {e}")
        raise

def fetch_single(symbol: str, tf: str, since: Optional[int], full_refresh: bool) -> Optional[pd.DataFrame]:
    """Fetch OHLCV data for a single symbol with pagination support."""
    exchange = get_exchange()
    
    all_data = []
    current_since = since
    
    while True:
        def fetch_fn():
            return exchange.fetch_ohlcv(symbol, tf, since=current_since, limit=1000)
        
        try:
            data = retry_with_backoff(fetch_fn)
            if not data:
                break
            
            all_data.extend(data)
            
            # Check if we got a full page (need to paginate)
            if len(data) < 1000:
                break
            
            # Update since for next iteration
            current_since = int(data[-1][0]) + 1
            
        except Exception as e:
            log.error(f"Failed to fetch {symbol} [{tf}]: {e}")
            return None
    
    if not all_data:
        return None
    
    # Convert to DataFrame and normalize
    df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df = standardize_ohlcv(df, symbol, tf)
    
    # Clean duplicates (normalizer already sorts)
    df = df.drop_duplicates(subset=['ts']).reset_index(drop=True)
    
    return df

def get_last_timestamps(filename: Path) -> Dict[str, int]:
    """Get the last timestamp for each symbol from existing parquet file."""
    if not filename.exists():
        return {}
    
    try:
        # Read only necessary columns for efficiency
        df = pd.read_parquet(filename, columns=['symbol', 'ts'])
        last_ts = df.groupby('symbol')['ts'].max()
        return {symbol: int(pd.to_datetime(ts).timestamp() * 1000) 
                for symbol, ts in last_ts.items()}
    except Exception as e:
        log.warning(f"Error reading existing file {filename}: {e}")
        return {}

def fetch_for_timeframe(tf: str, symbols: List[str], full_refresh: bool, 
                       max_workers: int, show_progress: bool, output_dir: Path) -> int:
    """Fetch data for all symbols in a timeframe with safe concurrent writes."""
    filename = output_dir / f"ohlcv_{tf}.parquet"
    
    # Get last timestamps for incremental updates
    last_timestamps = {} if full_refresh else get_last_timestamps(filename)
    
    with Progress(SpinnerColumn(), BarColumn(), TextColumn("{task.description}"),
                  TimeElapsedColumn(), transient=True, disable=not show_progress) as progress:
        task = progress.add_task(f"[{tf}] Fetching {len(symbols)} symbols", total=len(symbols))
        
        # Collect DataFrames from workers (no file I/O in workers)
        collected_dfs = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for symbol in symbols:
                since = last_timestamps.get(symbol) if not full_refresh else None
                future = executor.submit(fetch_single, symbol, tf, since, full_refresh)
                futures[future] = symbol
            
            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    df = future.result()
                    if df is not None and not df.empty:
                        collected_dfs.append(df)
                except Exception as e:
                    log.error(f"[{tf}] Failed {symbol}: {e}")
                progress.update(task, advance=1)
    
    # Safe write: merge all data and write once
    if collected_dfs:
        # Load existing data if not full refresh
        existing_df = None
        if not full_refresh and filename.exists():
            try:
                existing_df = pd.read_parquet(filename)
            except Exception as e:
                log.warning(f"Error reading existing file for merge: {e}")
        
        # Concatenate and clean
        if existing_df is not None:
            all_dfs = [existing_df] + collected_dfs
        else:
            all_dfs = collected_dfs
        
        merged_df = pd.concat(all_dfs, ignore_index=True)
        merged_df = merged_df.drop_duplicates(subset=['symbol', 'ts']).sort_values(['symbol', 'ts'])
        
        # Write once
        merged_df.to_parquet(filename, index=False)
        log.info(f"Saved {len(merged_df)} rows to {filename}")
        return len(merged_df)
    else:
        log.warning(f"No data collected for {tf}")
        return 0

@app.command()
def main(
    config_path: Path = typer.Option("fetch.config.yaml", "--config-path", help="Path to config YAML (unused)"),
    full_refresh: bool = typer.Option(False, "--full-refresh", help="Ignore existing files and fetch everything"),
    max_workers: int = typer.Option(5, "--max-workers", help="Max concurrent fetch threads per timeframe"),
    no_progress: bool = typer.Option(False, "--no-progress", help="Disable rich progress bar"),
    top_n: int = typer.Option(300, "--top-n", help="Top N USDT pairs by volume"),
    output_dir: Path = typer.Option(Path("ohlcv_parquet"), "--output-dir", help="Where to save parquet files"),
    timeframes: List[str] = typer.Option(['1h', '4h', '1d'], "--timeframes", help="Timeframes to fetch")
):
    start = time.time()
    rich.print(f"📦 [bold cyan]Fetch v3.0.0 started[/] at {datetime.utcnow().strftime('%H:%M:%S UTC')}")
    rich.print(f"🔧 Full refresh: {full_refresh}, Workers: {max_workers}, Top N: {top_n}")
    rich.print(f"📁 Output dir: {output_dir}, Timeframes: {timeframes}")
    
    # Ensure output directory exists
    output_dir.mkdir(exist_ok=True)
    
    symbols = fetch_symbols(top_n)
    rich.print(f"📊 Fetched {len(symbols)} symbols")
    
    total_rows = 0
    for tf in timeframes:
        rows = fetch_for_timeframe(tf, symbols, full_refresh, max_workers, not no_progress, output_dir)
        total_rows += rows
        rich.print(f"✅ {tf}: {rows} rows")
    
    elapsed = time.time() - start
    rich.print(f"🎯 Done in {elapsed:.1f}s | Total rows: {total_rows}")
    log.info(f"Job completed in {elapsed:.1f}s with {total_rows} total rows")

if __name__ == "__main__":
    app()