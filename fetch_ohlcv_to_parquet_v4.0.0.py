"""
fetch_ohlcv_to_parquet_v4.0.0.py
Version: 4.0.0
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
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import typer
import rich
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
import time
import logging
import random
from typing import Dict, Optional, List, Union

# near the top
__version__ = "v4.0.0"
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
            'options': {
                'defaultType': 'spot',
                'fetchMarkets': 'spot'  # Explicitly fetch only spot markets
            }
        })
    return _exchange

# ========== LOGGING ==========
logging.basicConfig(filename="fetch_ohlcv.log", level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)
# =============================

# === BACKFILL FUNCTIONALITY ===
TF_MS = {"1h": 60*60*1000, "4h": 4*60*60*1000, "1d": 24*60*60*1000}

def parse_iso_to_ms(s: str) -> Optional[int]:
    """Parse ISO date string to milliseconds timestamp."""
    if not s: 
        return None
    # Accept YYYY-MM-DD or ISO with Z
    try:
        if "T" in s:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        else:
            dt = datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    except Exception:
        raise ValueError(f"Could not parse --since value: {s}")

def load_cli_symbols(symbols_str: str, symbols_file: str) -> List[str]:
    """Load symbols from CLI string or file."""
    out = []
    if symbols_str.strip():
        out += [s.strip() for s in symbols_str.split(",") if s.strip()]
    if symbols_file.strip():
        p = Path(symbols_file)
        if not p.exists():
            raise FileNotFoundError(f"--symbols-file not found: {symbols_file}")
        if p.suffix.lower() == ".csv":
            df = pd.read_csv(p)
            col = next((c for c in df.columns if c.lower()=="symbol"), df.columns[0])
            out += df[col].dropna().astype(str).str.strip().tolist()
        else:
            out += [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
    # dedupe + normalize keep original slash form
    seen, res = set(), []
    for s in out:
        if s not in seen:
            seen.add(s)
            res.append(s)
    return res

def normalize_binance_symbol(sym: str) -> str:
    """Canonicalize to with slash (ccxt form): BTC/USDT."""
    if "/" in sym:
        return sym.upper()
    # If given BTCUSDT → insert slash
    if sym.upper().endswith("USDT"):
        base = sym.upper()[:-4]
        return f"{base}/USDT"
    return sym.upper()

def filter_spot_usdt_markets(exchange, symbols: List[str]) -> List[str]:
    """Ensure we only keep spot USDT pairs that exist on binance spot."""
    markets = exchange.load_markets()
    keep = []
    for s in symbols:
        ss = normalize_binance_symbol(s)
        m = markets.get(ss)
        if not m:
            continue
        if (m.get("type") == "spot" or m.get("spot") is True) and ss.endswith("/USDT"):
            if m.get("active", True):
                keep.append(ss)
    return sorted(set(keep))

def safe_fetch_ohlcv(exchange, symbol: str, timeframe: str, since_ms: Optional[int], limit: int = 1000):
    """Wrap CCXT fetch with basic retry."""
    for attempt in range(5):
        try:
            return exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since_ms, limit=limit)
        except ccxt.NetworkError as e:
            time.sleep(1.0 + attempt * 0.5)
        except ccxt.ExchangeError as e:
            raise
    return []

def backfill_symbol_tf(exchange, symbol: str, timeframe: str, since_ms: Optional[int], rate_limit_ms: int = 200):
    """
    Chunked forward-fetch from since_ms to now for one symbol+tf.
    Returns a DataFrame with columns: symbol, ts, open, high, low, close, volume
    """
    tf_ms = TF_MS[timeframe]
    lim = 1000
    rows = []
    cursor = since_ms
    while True:
        batch = safe_fetch_ohlcv(exchange, symbol, timeframe, cursor, limit=lim)
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < lim:
            break
        last_ts = batch[-1][0]
        cursor = max(cursor or last_ts, last_ts) + tf_ms
        # be gentle
        time.sleep(rate_limit_ms/1000.0)
    if not rows:
        return pd.DataFrame(columns=["symbol","ts","open","high","low","close","volume"])
    df = pd.DataFrame(rows, columns=["ts","open","high","low","close","volume"])
    df.insert(0, "symbol", symbol.replace("/", ""))  # canonical noslash in parquet
    # ensure ints
    df["ts"] = df["ts"].astype("int64")
    return df

def merge_and_write_parquet(df_new: pd.DataFrame, out_path: Path, append: bool):
    """Merge new data with existing parquet, deduplicate, and write."""
    if df_new.empty:
        return 0, 0
    
    # Convert new data ts to datetime to match existing format
    if 'ts' in df_new.columns:
        df_new = df_new.copy()
        df_new['ts'] = pd.to_datetime(df_new['ts'], unit='ms', utc=True)
    
    if append and out_path.exists():
        df_old = pd.read_parquet(out_path)
        df_all = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df_all = df_new
    before = len(df_all)
    df_all = df_all.drop_duplicates(subset=["symbol","ts"], keep="last")
    after = len(df_all)
    df_all = df_all.sort_values(["symbol","ts"])
    df_all.to_parquet(out_path, index=False)
    return before, after

def timeframe_ms(tf: str) -> int:
    """Get timeframe in milliseconds."""
    if tf not in TF_MS: 
        raise ValueError(f"Unsupported timeframe: {tf}")
    return TF_MS[tf]

def tf_out_parquet_dir(base_dir: Path, tf: str) -> Path:
    """Get parquet file path for timeframe."""
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / f"ohlcv_{tf}.parquet"

def backfill_mode(symbols_str: str, symbols_file: str, since: str, since_1h: str, since_4h: str, since_1d: str, 
                 timeframes: List[str], output_dir: Path, append: bool, strict_spot_usdt: bool):
    """Main backfill functionality."""
    exchange = get_exchange()
    
    # Resolve timeframes
    for tf in timeframes:
        if tf not in TF_MS:
            raise ValueError(f"Unsupported timeframe in --timeframes: {tf}")
    
    # Resolve symbols set
    cli_syms = load_cli_symbols(symbols_str, symbols_file)
    if cli_syms:
        # Use only CLI-provided symbols, filtered to spot/USDT if requested
        if strict_spot_usdt:
            target_symbols = filter_spot_usdt_markets(exchange, cli_syms)
        else:
            target_symbols = [normalize_binance_symbol(s) for s in cli_syms]
    else:
        # Dynamic discovery from markets (spot USDT only)
        markets = exchange.load_markets()
        target_symbols = []
        for m in markets.values():
            if (m.get("type") == "spot" or m.get("spot") is True) and m.get("active", True):
                if m.get("symbol","").endswith("/USDT"):
                    target_symbols.append(m["symbol"])
        target_symbols = sorted(set(target_symbols))
    
    rich.print(f"Symbols to fetch: {len(target_symbols)}")
    if not target_symbols:
        raise SystemExit("No symbols to fetch. Check --symbols / --symbols-file or market filtering.")
    
    # Parse global/per-TF since
    global_since_ms = parse_iso_to_ms(since)
    since_map = {
        "1h": parse_iso_to_ms(since_1h) if since_1h else global_since_ms,
        "4h": parse_iso_to_ms(since_4h) if since_4h else global_since_ms,
        "1d": parse_iso_to_ms(since_1d) if since_1d else global_since_ms,
    }
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    total_new_rows = 0
    for tf in timeframes:
        tf_since = since_map.get(tf, None)
        out_path = tf_out_parquet_dir(output_dir, tf)
        rich.print(f"\n⏳ Backfilling {tf} → {out_path} (since={tf_since}) | symbols={len(target_symbols)}")
        
        df_tf_list = []
        for i, sym in enumerate(target_symbols, 1):
            try:
                df_sym = backfill_symbol_tf(exchange, sym, tf, tf_since, rate_limit_ms=exchange.rateLimit or 200)
                if not df_sym.empty:
                    df_tf_list.append(df_sym)
            except Exception as e:
                rich.print(f"warn: fetch failed for {sym} {tf}: {e}")
            if (i % 25) == 0:
                rich.print(f"… {tf} progress: {i}/{len(target_symbols)} symbols")
        
        df_tf = pd.concat(df_tf_list, ignore_index=True) if df_tf_list else pd.DataFrame(
            columns=["symbol","ts","open","high","low","close","volume"]
        )
        
        before, after = merge_and_write_parquet(df_tf, out_path, append=append)
        total_new_rows += (after - (before - len(df_tf)))
        rich.print(f"✅ {tf}: wrote {after} rows (deduped), file: {out_path}")
    
    rich.print(f"\n🎯 Backfill complete. Timeframes: {timeframes} | Symbols: {len(target_symbols)}")
    return total_new_rows

# === END BACKFILL FUNCTIONALITY ===

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
    """Fetch top N USDT spot pairs by 24h volume, excluding leveraged tokens."""
    exchange = get_exchange()
    try:
        # First, get all spot market symbols to ensure we only work with spot pairs
        markets = exchange.load_markets()
        spot_symbols = set()
        
        for symbol, market in markets.items():
            # Only include spot market symbols that end with USDT
            if (market.get('type') == 'spot' and 
                symbol.endswith('/USDT') and
                market.get('active', True)):  # Ensure market is active
                spot_symbols.add(symbol)
        
        log.info(f"Found {len(spot_symbols)} active USDT spot symbols")
        
        # Now get tickers only for spot symbols
        tickers = exchange.fetch_tickers()
        pairs = []
        
        for symbol in spot_symbols:
            if symbol in tickers:
                v = tickers[symbol]
                # Additional filtering for leveraged tokens and invalid symbols
                if (not symbol.startswith('1000') and
                    not any(x in symbol for x in ['UP/', 'DOWN/', 'BULL/', 'BEAR/']) and
                    v.get('quoteVolume') is not None):
                    try:
                        volume = float(v['quoteVolume'])
                        if volume > 0:
                            pairs.append((symbol, volume))
                    except (ValueError, TypeError):
                        continue
        
        sorted_pairs = sorted(pairs, key=lambda x: x[1], reverse=True)
        symbols = [s[0] for s in sorted_pairs[:top_n]] if top_n else [s[0] for s in sorted_pairs]
        log.info(f"Fetched {len(symbols)} spot USDT symbols (top {top_n if top_n else 'all'})")
        return symbols
    except Exception as e:
        log.error(f"Failed to fetch symbols: {e}")
        raise

def transform_symbol_format(symbol: str) -> str:
    """Transform symbol from COW/USDT format to COWUSDT format."""
    return symbol.replace('/', '').upper()

def validate_spot_symbol(symbol: str) -> bool:
    """Validate that a symbol is actually a spot market symbol."""
    exchange = get_exchange()
    try:
        markets = exchange.load_markets()
        if symbol in markets:
            market = markets[symbol]
            return (market.get('type') == 'spot' and 
                   market.get('active', True) and
                   symbol.endswith('/USDT'))
        return False
    except Exception as e:
        log.warning(f"Failed to validate symbol {symbol}: {e}")
        return False

def fetch_single(symbol: str, tf: str, since: Optional[int], full_refresh: bool) -> Optional[pd.DataFrame]:
    """Fetch OHLCV data for a single symbol with pagination support."""
    # Validate symbol is spot market before fetching
    if not validate_spot_symbol(symbol):
        log.warning(f"Skipping non-spot symbol: {symbol}")
        return None
        
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
    # Transform symbol format before standardizing
    transformed_symbol = transform_symbol_format(symbol)
    df = standardize_ohlcv(df, transformed_symbol, tf)
    
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
                # Use transformed symbol for timestamp lookup (existing files use transformed format)
                transformed_symbol = transform_symbol_format(symbol)
                since = last_timestamps.get(transformed_symbol) if not full_refresh else None
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
    timeframes: List[str] = typer.Option(['1h', '4h', '1d'], "--timeframes", help="Timeframes to fetch"),
    
    # Backfill options
    symbols: str = typer.Option("", "--symbols", help='Comma-separated list: "BTC/USDT,ETH/USDT" (spot/USDT only)'),
    symbols_file: str = typer.Option("", "--symbols-file", help="Path to a txt/csv with symbols (column 'symbol' or one per line)"),
    since: str = typer.Option("", "--since", help='Global start date/time UTC, e.g. "2025-06-01" or "2025-06-01T00:00:00Z"'),
    since_1h: str = typer.Option("", "--since-1h", help="Override --since for 1h"),
    since_4h: str = typer.Option("", "--since-4h", help="Override --since for 4h"),
    since_1d: str = typer.Option("", "--since-1d", help="Override --since for 1d"),
    append: bool = typer.Option(False, "--append", help="Append/merge into existing parquet (dedupe by symbol+ts)"),
    strict_spot_usdt: bool = typer.Option(True, "--strict-spot-usdt", help="Filter to Binance spot USDT markets only (default True)")
):
    start = time.time()
    rich.print(f"📦 [bold cyan]Fetch {__version__} started[/] at {datetime.utcnow().strftime('%H:%M:%S UTC')}")
    
    # Check if we're in backfill mode
    is_backfill_mode = symbols or symbols_file or since or since_1h or since_4h or since_1d
    
    if is_backfill_mode:
        rich.print(f"🔄 [bold yellow]Backfill Mode[/]")
        rich.print(f"📁 Output dir: {output_dir}, Timeframes: {timeframes}")
        rich.print(f"🔧 Append: {append}, Strict spot/USDT: {strict_spot_usdt}")
        
        total_rows = backfill_mode(
            symbols_str=symbols,
            symbols_file=symbols_file,
            since=since,
            since_1h=since_1h,
            since_4h=since_4h,
            since_1d=since_1d,
            timeframes=timeframes,
            output_dir=output_dir,
            append=append,
            strict_spot_usdt=strict_spot_usdt
        )
        
        elapsed = time.time() - start
        rich.print(f"🎯 Backfill completed in {elapsed:.1f}s | Total rows: {total_rows}")
        log.info(f"Backfill job completed in {elapsed:.1f}s with {total_rows} total rows")
    else:
        # Original mode
        rich.print(f"🔧 Full refresh: {full_refresh}, Workers: {max_workers}, Top N: {top_n}")
        rich.print(f"📁 Output dir: {output_dir}, Timeframes: {timeframes}")
        
        # Ensure output directory exists
        output_dir.mkdir(exist_ok=True)
        
        symbols = fetch_symbols(top_n)
        # Show first few symbols in transformed format for user confirmation
        sample_symbols = [transform_symbol_format(s) for s in symbols[:5]]
        rich.print(f"📊 Fetched {len(symbols)} symbols (sample: {', '.join(sample_symbols)})")
        
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