#!/usr/bin/env python3
#!/usr/bin/env python3
# Coil & Spring (SP004/SP003) – CLI scanner
# Daily confirmation is OPTIONAL: if 'daily_confirm_1d' is absent in YAML,
# the scanner will NOT gate on any daily condition.
import os
import re
import sys
import argparse
import datetime as dt
from typing import Dict, List, Optional, Any

import pandas as pd
import numpy as np
import yaml

# --- import path bootstrap (lets us find src/indicators.py) ---
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CANDIDATES = [
    HERE,                 # project root if indicators.py is alongside
    HERE / "src",         # common layout: src/indicators.py
    HERE.parent,          # parent (in case you run from a subdir)
    HERE.parent / "src",
]

for p in CANDIDATES:
    if (p / "indicators.py").exists():
        sys.path.insert(0, str(p))
    if (p / "src" / "indicators.py").exists():
        sys.path.insert(0, str(p / "src"))
# --------------------------------------------------------------
# --- project-local ---
# We assume indicators.py lives in the same repo (src/ or alongside this file)
try:
    from indicators import compute_features
except Exception as e:
    print(f"[FATAL] Unable to import indicators.compute_features: {e}", file=sys.stderr)
    sys.exit(1)

def _count_trailing_trues(s: pd.Series) -> int:
    """How many consecutive True values up to the latest bar (trailing run-length)."""
    arr = s.to_numpy(dtype=bool)[::-1]  # reverse so latest bar is first
    if not arr.size or not arr[0]:
        return 0
    false_idx = np.where(~arr)[0]
    return int(false_idx[0]) if false_idx.size else int(arr.size)

# -------- Amy's v2 Core Functions --------
def fast3_width_pct(row: pd.Series, ema21_col: str = "EMA21", ema40_col: str = "EMA40", 
                   sma50_col: str = "SMA50", sma150_col: str = "SMA150") -> float:
    """
    Calculate the width percentage of the fast3 moving averages (EMA21, EMA40, SMA50).
    
    Formula: 100 * (max(EMA21, EMA40, SMA50) - min(EMA21, EMA40, SMA50)) / SMA150
    
    Args:
        row: DataFrame row containing MA values
        ema21_col: Column name for EMA21
        ema40_col: Column name for EMA40  
        sma50_col: Column name for SMA50
        sma150_col: Column name for SMA150 (baseline)
    
    Returns:
        Width percentage as float, or NaN if any MA is missing
    """
    try:
        ema21 = float(row[ema21_col])
        ema40 = float(row[ema40_col])
        sma50 = float(row[sma50_col])
        sma150 = float(row[sma150_col])
        
        if pd.isna([ema21, ema40, sma50, sma150]).any() or sma150 <= 0:
            return np.nan
            
        fast3_max = max(ema21, ema40, sma50)
        fast3_min = min(ema21, ema40, sma50)
        width = fast3_max - fast3_min
        
        return 100.0 * width / sma150
        
    except (KeyError, ValueError, TypeError):
        return np.nan

def bars_in_coil(series_width: pd.Series, series_tratr: pd.Series, 
                max_width_pct: float, max_tratr: float, min_bars: int) -> int:
    """
    Count consecutive bars where both width and volatility conditions are met.
    
    Args:
        series_width: Series of fast3_width_pct values
        series_tratr: Series of tr_range_atr values  
        max_width_pct: Maximum allowed width percentage
        max_tratr: Maximum allowed TR/ATR ratio
        min_bars: Minimum bars required (used for validation)
    
    Returns:
        Number of consecutive bars meeting both conditions
    """
    if len(series_width) == 0 or len(series_tratr) == 0:
        return 0
        
    # Create boolean mask for both conditions
    width_ok = series_width <= max_width_pct
    tratr_ok = series_tratr <= max_tratr
    both_ok = width_ok & tratr_ok
    
    # Count trailing consecutive True values
    return _count_trailing_trues(both_ok)

def slope_pct(series: pd.Series, lookback: int) -> float:
    """
    Calculate percentage slope over lookback period.
    
    Formula: 100 * (MA_t / MA_{t-L} - 1)
    
    Args:
        series: Series of MA values
        lookback: Number of bars to look back
    
    Returns:
        Slope percentage as float, or NaN if insufficient data
    """
    if len(series) <= lookback:
        return np.nan
        
    try:
        current = float(series.iloc[-1])
        past = float(series.iloc[-1 - lookback])
        
        if pd.isna([current, past]).any() or past == 0:
            return np.nan
            
        return 100.0 * (current / past - 1.0)
        
    except (IndexError, ValueError, TypeError):
        return np.nan

# -------- Amy's v2 Pipeline Stages --------
def pass_coil_1h(g1h: pd.DataFrame, cfg: Dict[str, Any]) -> bool:
    """
    Stage 1: Detect tight coil formation on 1h timeframe.
    
    Args:
        g1h: 1h DataFrame for a symbol
        cfg: coil_1h configuration section
    
    Returns:
        True if coil conditions are met
    """
    if g1h is None or g1h.empty:
        return False
        
    try:
        # Get configuration parameters
        max_width_pct = float(cfg.get("max_fast3_width_pct", 3.0))
        min_bars = int(cfg.get("min_bars_in_coil", 10))
        max_tratr = float(cfg.get("max_tr_range_atr", 1.2))
        min_ma21_slope = float(cfg.get("min_ma21_slope_pct", -0.10))
        
        # Use pre-computed FAST3_WIDTH_PCT and TR_RANGE_ATR columns if available
        if "FAST3_WIDTH_PCT" in g1h.columns and "TR_RANGE_ATR" in g1h.columns:
            width_series = g1h["FAST3_WIDTH_PCT"]
            tratr_series = g1h["TR_RANGE_ATR"]
        elif all(col in g1h.columns for col in ["EMA21", "EMA40", "SMA50", "SMA150"]):
            # Fallback to calculating width if pre-computed columns not available
            width_series = g1h.apply(lambda row: fast3_width_pct(row), axis=1)
            tratr_series = g1h.get("TR_RANGE_ATR", pd.Series([np.nan] * len(g1h)))
        else:
            return False
        
        # Count bars in coil
        bars_count = bars_in_coil(width_series, tratr_series, max_width_pct, max_tratr, min_bars)
        
        # Check minimum bars requirement
        if bars_count < min_bars:
            return False
            
        # Optional: Check EMA21 slope bias
        if "EMA21" in g1h.columns and len(g1h) >= 100:  # slope_window default
            slope_window = int(cfg.get("slope_window", 100))
            ema21_slope = slope_pct(g1h["EMA21"], slope_window)
            if not pd.isna(ema21_slope) and ema21_slope < min_ma21_slope:
                return False
        
        # Optional: Check SMA150 slope bias
        if "require_sma150_slope_bps_min" in cfg and "SMA150_SLOPE_BPS" in g1h.columns:
            sma150_slope_min = float(cfg.get("require_sma150_slope_bps_min", -15.0))
            sma150_slope = float(g1h["SMA150_SLOPE_BPS"].iloc[-1])
            if not pd.isna(sma150_slope) and sma150_slope < sma150_slope_min:
                return False
                
        return True
        
    except Exception as e:
        return False

def pass_match_4h(g4h: pd.DataFrame, cfg: Dict[str, Any]) -> bool:
    """
    Stage 2: Confirm with 4h timeframe (either coiled or turning up).
    
    Args:
        g4h: 4h DataFrame for a symbol
        cfg: match_4h configuration section
    
    Returns:
        True if 4h matching conditions are met
    """
    if g4h is None or g4h.empty:
        return False
        
    try:
        mode = cfg.get("mode", "either")
        
        # Option A: Also coiled on 4h
        cond_a = False
        if "max_fast3_width_pct" in cfg:
            max_width_pct = float(cfg.get("max_fast3_width_pct", 8.0))
            max_tratr = float(cfg.get("max_tr_range_atr", 1.2))  # Use config value instead of hardcoded 1.2
            min_bars = int(cfg.get("min_bars_in_coil", 4))
            
            # Use pre-computed FAST3_WIDTH_PCT and TR_RANGE_ATR columns if available
            if "FAST3_WIDTH_PCT" in g4h.columns and "TR_RANGE_ATR" in g4h.columns:
                width_series = g4h["FAST3_WIDTH_PCT"]
                tratr_series = g4h["TR_RANGE_ATR"]
                bars_count = bars_in_coil(width_series, tratr_series, max_width_pct, max_tratr, min_bars)
                cond_a = bars_count >= min_bars
            elif all(col in g4h.columns for col in ["EMA21", "EMA40", "SMA50", "SMA150"]):
                # Fallback to calculating width if pre-computed columns not available
                width_series = g4h.apply(lambda row: fast3_width_pct(row), axis=1)
                tratr_series = g4h.get("TR_RANGE_ATR", pd.Series([np.nan] * len(g4h)))
                bars_count = bars_in_coil(width_series, tratr_series, max_width_pct, max_tratr, min_bars)
                cond_a = bars_count >= min_bars
        
        # Option B: Alignment/turn-up on 4h
        cond_b = False
        if "min_ma21_slope_pct" in cfg and "min_ma50_slope_pct" in cfg:
            min_ma21_slope = float(cfg.get("min_ma21_slope_pct", 0.0))
            min_ma50_slope = float(cfg.get("min_ma50_slope_pct", 0.0))
            slope_window = int(cfg.get("slope_window", 100))
            
            if "EMA21" in g4h.columns and "SMA50" in g4h.columns and len(g4h) >= slope_window:
                ema21_slope = slope_pct(g4h["EMA21"], slope_window)
                sma50_slope = slope_pct(g4h["SMA50"], slope_window)
                
                if not pd.isna(ema21_slope) and not pd.isna(sma50_slope):
                    cond_b = (ema21_slope >= min_ma21_slope and sma50_slope >= min_ma50_slope)
        
        # Return based on mode
        if mode == "either":
            return cond_a or cond_b
        else:  # "and" mode
            return cond_a and cond_b
            
    except Exception as e:
        return False

def pass_confirm_1d(g1d: pd.DataFrame, cfg: Dict[str, Any]) -> bool:
    """
    Stage 3: Final confirmation with daily trend bias.
    
    Args:
        g1d: 1d DataFrame for a symbol
        cfg: confirm_1d configuration section
    
    Returns:
        True if daily confirmation conditions are met
    """
    if g1d is None or g1d.empty:
        return False
        
    try:
        min_slope_pct = float(cfg.get("min_sma150_slope_pct", 0.0))
        tolerance_pct = float(cfg.get("tolerance_pct", 0.0))
        
        # Use pre-computed SMA150_SLOPE_BPS column if available
        if "SMA150_SLOPE_BPS" in g1d.columns:
            sma150_slope = float(g1d["SMA150_SLOPE_BPS"].iloc[-1])
            if not pd.isna(sma150_slope):
                threshold = min_slope_pct - tolerance_pct
                return sma150_slope >= threshold
        
        # Fallback to manual calculation if column not available
        slope_window = int(cfg.get("slope_window", 100))
        if "SMA150" in g1d.columns and len(g1d) >= slope_window:
            sma150_slope = slope_pct(g1d["SMA150"], slope_window)
            if not pd.isna(sma150_slope):
                threshold = min_slope_pct - tolerance_pct
                return sma150_slope >= threshold
                
        return False
        
    except Exception as e:
        return False

def pipeline(symbol_df_dict: Dict[str, pd.DataFrame], yaml_cfg: Dict[str, Any]) -> Dict[str, bool]:
    """
    Amy's v2 pipeline orchestration.
    
    Args:
        symbol_df_dict: {"1h": df1h_symbol, "4h": df4h_symbol, "1d": df1d_symbol}
        yaml_cfg: Full YAML configuration
    
    Returns:
        Dictionary with stage results: {"coil_pass": bool, "match_pass": bool, "confirm_pass": bool}
    """
    result = {"coil_pass": False, "match_pass": False, "confirm_pass": False}
    
    # Get enabled stages from control section
    enabled_stages = yaml_cfg.get("control", {}).get("enabled_stages", ["coil_1h", "match_4h", "confirm_1d"])
    
    # Import compute_features
    from src.indicators import compute_features
    
    # Stage 1: 1h Coil Detection
    if "coil_1h" in enabled_stages and "1h" in symbol_df_dict:
        coil_cfg = yaml_cfg.get("coil_1h", {})
        # Compute features for 1h data
        h1feat = compute_features(symbol_df_dict["1h"].copy(), coil_cfg)
        result["coil_pass"] = pass_coil_1h(h1feat, coil_cfg)
    
    # Stage 2: 4h Matching
    if "match_4h" in enabled_stages and "4h" in symbol_df_dict:
        match_cfg = yaml_cfg.get("match_4h", {})
        # Compute features for 4h data
        h4feat = compute_features(symbol_df_dict["4h"].copy(), match_cfg)
        result["match_pass"] = pass_match_4h(h4feat, match_cfg)
    
    # Stage 3: 1d Confirmation
    if "confirm_1d" in enabled_stages and "1d" in symbol_df_dict:
        confirm_cfg = yaml_cfg.get("confirm_1d", {})
        # Compute features for 1d data
        d1feat = compute_features(symbol_df_dict["1d"].copy(), confirm_cfg)
        result["confirm_pass"] = pass_confirm_1d(d1feat, confirm_cfg)
    
    return result

# -------- YAML helpers --------
def load_yaml(path: str) -> Dict[str, Any]:
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}

def cfg_flag(cfg: Dict[str, Any], path: str, default: bool = False) -> bool:
    cur: Any = cfg
    for k in path.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return bool(cur)

def cfg_get(cfg: Dict[str, Any], path: str, default: Any = None) -> Any:
    cur: Any = cfg
    for k in path.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur

# -------- Data I/O --------
def read_parquet_monolithic(input_dir: str, tf: str) -> pd.DataFrame:
    """
    Reads monolithic parquet (ohlcv_{tf}.parquet) with columns:
    symbol | timeframe | ts | open | high | low | close | volume
    """
    fn = os.path.join(input_dir, f"ohlcv_{tf}.parquet")
    if not os.path.exists(fn):
        raise FileNotFoundError(f"Missing parquet file: {fn}")
    df = pd.read_parquet(fn)
    # basic sanity
    needed = {"symbol", "timeframe", "ts", "open", "high", "low", "close", "volume"}
    missing = needed - set(map(str.lower, df.columns.str.lower()))
    # normalize just in case of column case mismatches
    lower = {c.lower(): c for c in df.columns}
    cols = {c: lower[c] for c in lower}
    df = df.rename(columns={cols.get("symbol","symbol"):"symbol",
                            cols.get("timeframe","timeframe"):"timeframe",
                            cols.get("ts","ts"):"ts",
                            cols.get("open","open"):"open",
                            cols.get("high","high"):"high",
                            cols.get("low","low"):"low",
                            cols.get("close","close"):"close",
                            cols.get("volume","volume"):"volume"})
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df = df[df["timeframe"] == tf] if "timeframe" in df.columns else df
    return df

def discover_symbols(df_1h: pd.DataFrame,
                     regex: str,
                     exclude_list: List[str],
                     cli_symbols: Optional[List[str]]) -> List[str]:
    all_syms = sorted(df_1h["symbol"].dropna().unique().tolist())
    if cli_symbols:
        # honor CLI explicit subset (exact match)
        syms = [s for s in cli_symbols if s in all_syms]
    else:
        pat = re.compile(regex) if regex else re.compile(".*")
        syms = [s for s in all_syms if pat.match(s)]
        if exclude_list:
            excl = set(exclude_list)
            syms = [s for s in syms if s not in excl]
    return syms

# -------- Daily gate (optional) --------
def passes_daily(dfeat: pd.DataFrame, dcfg: Dict[str, Any]) -> bool:
    """
    Daily confirm gate. Returns False if required daily columns are missing.
    Expected columns if used:
      - "BB_UPPER", "BB_LOWER" (Bollinger)
      - "SMA_150"
      - "SMA150_SLOPE_BPS"
    YAML keys used:
      - flat_sma_window           (int)
      - flat_sma_slope_bps_max    (float)
      - tight_cloud_bb_window     (int)
      - tight_cloud_bb_k          (float)
      - tight_cloud_pct_max       (float)
    """
    if dfeat is None or dfeat.empty:
        return False

    # take last row
    last = dfeat.iloc[-1].to_dict()

    # graceful guards: if a needed column is missing, fail the daily check
    def have(col: str) -> bool:
        return col in dfeat.columns

    # Flat SMA150 slope (bps abs <= max)
    slope_bps_max = float(dcfg.get("flat_sma_slope_bps_max", 15))
    if not have("SMA150_SLOPE_BPS"):
        return False
    if abs(float(last.get("SMA150_SLOPE_BPS", np.nan))) > slope_bps_max:
        return False

    # Tight cloud (BB width / price <= max%)
    cloud_max_pct = float(dcfg.get("tight_cloud_pct_max", 8.0))
    if not (have("BB_UPPER") and have("BB_LOWER") and have("close")):
        return False

    bbw = abs(dfeat["BB_UPPER"].iloc[-1] - dfeat["BB_LOWER"].iloc[-1])
    ref = float(dfeat["close"].iloc[-1])
    if ref <= 0 or not np.isfinite(ref):
        return False
    cloud_pct = (bbw / ref) * 100.0
    if cloud_pct > cloud_max_pct:
        return False

    return True

# -------- 1h filters / metrics --------
def extract_1h_metrics(hf: pd.DataFrame) -> Dict[str, float]:
    """
    Fetches last-value metrics if present; returns dict with NaNs when absent.
    Expected (if produced by compute_features):
      - FAST3_WIDTH_PCT
      - BARS_IN_COIL
      - TR_RANGE_ATR
      - SMA150_SLOPE_BPS
    """
    out = {
        "FAST3_WIDTH_PCT": np.nan,
        "BARS_IN_COIL": np.nan,
        "TR_RANGE_ATR": np.nan,
        "SMA150_SLOPE_BPS": np.nan,
        "CLOSE": np.nan
    }
    if hf is None or hf.empty:
        return out
    last = hf.iloc[-1]
    for k in list(out.keys()):
        if k in hf.columns:
            out[k] = float(last[k])
    return out

def passes_1h_filters(metrics: Dict[str, float], hcfg: Dict[str, Any]) -> bool:
    # Read thresholds; if a threshold is absent from YAML, skip that condition.
    m = metrics
    # fast3 width
    if "max_fast3_width_pct" in hcfg and np.isfinite(m.get("FAST3_WIDTH_PCT", np.nan)):
        if m["FAST3_WIDTH_PCT"] > float(hcfg["max_fast3_width_pct"]):
            return False
    # persistence
    if "min_bars_in_coil" in hcfg and np.isfinite(m.get("BARS_IN_COIL", np.nan)):
        if m["BARS_IN_COIL"] < float(hcfg["min_bars_in_coil"]):
            return False
    # wick/noise guard
    if "max_tr_range_atr" in hcfg and np.isfinite(m.get("TR_RANGE_ATR", np.nan)):
        if m["TR_RANGE_ATR"] > float(hcfg["max_tr_range_atr"]):
            return False
    # SMA150 slope min (flat-or-up)
    if "require_sma150_slope_bps_min" in hcfg and np.isfinite(m.get("SMA150_SLOPE_BPS", np.nan)):
        if m["SMA150_SLOPE_BPS"] < float(hcfg["require_sma150_slope_bps_min"]):
            return False
    return True

# -------- Output helpers --------
def write_outputs(res: pd.DataFrame, out_dir: str, config_name: str, explicit_out: Optional[str] = None, enabled_stages: Optional[list] = None) -> None:
    os.makedirs(out_dir, exist_ok=True)
    stamp = dt.datetime.utcnow().strftime("%Y-%m-%d___%H-%M")
    
    # main CSV
    out_csv = explicit_out or os.path.join(out_dir, f"coil_spring_{config_name}_{stamp}.csv")
    res.to_csv(out_csv, index=False)

    # Binance list CSV
    # Convert SYMBOLS like "BTC/USDT" -> "BTCUSDT"
    pairs = [s.replace("/", "") for s in res["symbol"].tolist()]
    line = "Binance:" + ",".join(pairs)
    out_csv_binance = os.path.join(out_dir, f"coil_spring_{config_name}_{stamp}_binance_list.csv")
    pd.DataFrame({"binance_list": [line]}).to_csv(out_csv_binance, index=False)

    # TXT line
    out_txt = os.path.join(out_dir, f"coil_spring_{config_name}_{stamp}.txt")
    with open(out_txt, "w") as f:
        f.write(line + "\n")

    # Enhanced Watchlist System - Individual watchlists per stage
    def create_watchlist(symbols: list, stage_name: str) -> None:
        """Create individual watchlist file for a specific stage"""
        if not symbols:
            return
        
        # Convert symbols to Binance format
        binance_symbols = [f"binance:{s.replace('/', '').lower()}" for s in symbols]
        
        # Create watchlist file
        watchlist_file = os.path.join(out_dir, f"watchlist_{stage_name}.txt")
        with open(watchlist_file, "w") as f:
            for symbol in binance_symbols:
                f.write(f"{symbol}\n")
        
        print(f"[OK] Wrote: {watchlist_file} ({len(symbols)} symbols)")

    # Generate individual stage watchlists
    if "coil_pass" in res.columns:
        coil_symbols = res[res["coil_pass"] == True]["symbol"].tolist()
        create_watchlist(coil_symbols, "coil_1h")
    
    if "match_pass" in res.columns:
        match_symbols = res[res["match_pass"] == True]["symbol"].tolist()
        create_watchlist(match_symbols, "match_4h")
    
    if "confirm_pass" in res.columns:
        confirm_symbols = res[res["confirm_pass"] == True]["symbol"].tolist()
        create_watchlist(confirm_symbols, "confirm_1d")
    
    # Generate pipeline all-pass watchlist (only enabled stages)
    if enabled_stages:
        all_pass_mask = pd.Series([True] * len(res), index=res.index)
        
        for stage in enabled_stages:
            if stage == "coil_1h" and "coil_pass" in res.columns:
                all_pass_mask &= res["coil_pass"]
            elif stage == "match_4h" and "match_pass" in res.columns:
                all_pass_mask &= res["match_pass"]
            elif stage == "confirm_1d" and "confirm_pass" in res.columns:
                all_pass_mask &= res["confirm_pass"]
        
        all_pass_symbols = res[all_pass_mask]["symbol"].tolist()
        create_watchlist(all_pass_symbols, "pipeline_all_pass")

    print(f"[OK] Wrote: {out_txt}")
    print(f"[OK] Wrote: {out_csv_binance}")
    print(f"[OK] Wrote: {out_csv}  (rows={len(res)})")

# -------- Main --------
def main():
    ap = argparse.ArgumentParser(description="Coil & Spring (SP004/SP003) scanner")
    ap.add_argument("--input-dir", default="./ohlcv_parquet", help="Parquet root (contains ohlcv_1h.parquet, ohlcv_1d.parquet) [default: ./ohlcv_parquet]")
    ap.add_argument("--cfg", required=True, help="YAML config (e.g., coil_spring.yaml or coil_spring_benchmark.yaml)")
    ap.add_argument("--symbols", nargs="*", default=None, help="Optional explicit symbol list (e.g. BTC/USDT ETH/USDT)")
    ap.add_argument("--output", default=None, help="Optional explicit CSV output path")
    ap.add_argument("--verbose", action="store_true", help="Verbose logs")
    args = ap.parse_args()

    cfg = load_yaml(args.cfg)

    # Read control flags
    benchmark = cfg_flag(cfg, "control.benchmark", False) or cfg_flag(cfg, "coil_1h.benchmark", False)
    use_daily = cfg_flag(cfg, "control.use_daily_confirm", cfg_flag(cfg, "use_daily_confirm", False))

    # Resolve universe
    universe_regex = cfg_get(cfg, "universe.regex", ".*") or cfg_get(cfg, "universe_regex", ".*")
    exclude_symbols = cfg_get(cfg, "universe.exclude_symbols", []) or []

    # Read data (monolithic) - Amy's v2: 1h + 4h + 1d
    try:
        h1 = read_parquet_monolithic(args.input_dir, "1h")
    except Exception as e:
        print(f"[ERR] Cannot read 1h data: {e}")
        return

    # 4h data for Amy's v2 pipeline
    h4 = None
    try:
        h4 = read_parquet_monolithic(args.input_dir, "4h")
    except Exception as e:
        print(f"[WARN] Cannot read 4h data: {e}")
        print(f"[INFO] 4h data required for Amy's v2 pipeline. Falling back to 1h+1d only.")
        h4 = None

    # Daily data only if we'll use it at all
    d1 = None
    if use_daily:
        try:
            d1 = read_parquet_monolithic(args.input_dir, "1d")
        except Exception as e:
            print(f"[WARN] Daily confirm enabled but cannot read 1d data: {e}")
            d1 = None

    # Discover symbols
    syms = discover_symbols(h1, universe_regex, exclude_symbols, args.symbols)
    if args.verbose:
        mode = "monolithic"
        print(f"[CFG] mode: {mode}")
        print(f"[CFG] 1h file: {os.path.join(args.input_dir, 'ohlcv_1h.parquet')}")
        print(f"[CFG] 4h file: {os.path.join(args.input_dir, 'ohlcv_4h.parquet')} {'✅' if h4 is not None else '❌'}")
        print(f"[CFG] 1d file: {os.path.join(args.input_dir, 'ohlcv_1d.parquet')}")
        print(f"[CFG] universe_regex: {universe_regex}")
        print(f"[DISCOVERY] Found {len(syms)} symbols in {os.path.join(args.input_dir, 'ohlcv_1h.parquet')}")
        if h4 is not None:
            print(f"[DISCOVERY] Found {len(h4['symbol'].unique())} symbols in 4h data")

    # Params sections
    hcfg = cfg.get("coil_1h", {})
    dcfg = cfg.get("daily_confirm_1d", {})

    rows = []
    for s in syms:
        try:
            g1 = h1[h1["symbol"] == s].sort_values("ts")
            if g1.empty:
                continue

            # Amy's v2: Load 4h data if available
            g4 = None
            if h4 is not None:
                g4 = h4[h4["symbol"] == s].sort_values("ts")
                if g4.empty:
                    g4 = None

            # Amy's v2: Load 1d data if available
            g1d = None
            if d1 is not None:
                g1d = d1[d1["symbol"] == s].sort_values("ts")
                if g1d.empty:
                    g1d = None

            # Compute features for all timeframes
            hfeat = compute_features(g1.copy(), hcfg)
            
            # Compute 4h features if data available
            h4feat = None
            if g4 is not None:
                h4feat = compute_features(g4.copy(), hcfg)
                
            # Compute 1d features if data available  
            d1feat = None
            if g1d is not None:
                d1feat = compute_features(g1d.copy(), dcfg)

            # Amy's v2: Run pipeline stages
            symbol_data = {"1h": hfeat}
            if h4feat is not None:
                symbol_data["4h"] = h4feat
            if d1feat is not None:
                symbol_data["1d"] = d1feat
                
            # Run Amy's v2 pipeline
            pipeline_results = pipeline(symbol_data, cfg)
            
            # Extract metrics for output
            last_1h = hfeat.iloc[-1] if not hfeat.empty else {}
            
            # Create output row with pipeline results
            row = {
                "symbol": s,
                "coil_pass": pipeline_results.get("coil_pass", False),
                "match_pass": pipeline_results.get("match_pass", False), 
                "confirm_pass": pipeline_results.get("confirm_pass", False),
                "fast3_width_pct": float(last_1h.get("FAST3_WIDTH_PCT", np.nan)),
                "bars_in_coil": int(last_1h.get("BARS_IN_COIL", np.nan)) if not pd.isna(last_1h.get("BARS_IN_COIL")) else np.nan,
                "tr_range_atr": float(last_1h.get("TR_RANGE_ATR", np.nan)),
                "sma150_slope_bps": float(last_1h.get("SMA150_SLOPE_BPS", np.nan)),
                "close": float(last_1h.get("close", np.nan)),
            }
            
            # Apply filtering based on benchmark mode
            if not benchmark:
                # Check if all enabled stages passed
                enabled_stages = cfg.get("control", {}).get("enabled_stages", ["coil_1h", "match_4h", "confirm_1d"])
                all_passed = True
                
                for stage in enabled_stages:
                    if stage == "coil_1h" and not pipeline_results.get("coil_pass", False):
                        all_passed = False
                        break
                    elif stage == "match_4h" and not pipeline_results.get("match_pass", False):
                        all_passed = False
                        break
                    elif stage == "confirm_1d" and not pipeline_results.get("confirm_pass", False):
                        all_passed = False
                        break
                        
                if not all_passed:
                    continue
            
            # Include in output (benchmark includes everyone, filtered only includes pipeline passes)
            rows.append(row)

        except KeyError as ke:
            if args.verbose:
                print(f"[WARN] {s}: missing expected feature column {ke}")
            # In benchmark we still include the symbol (even if features missing)
            if benchmark:
                rows.append({"symbol": s})
            continue
        except Exception as e:
            if args.verbose:
                print(f"[WARN] {s}: {e}")
            continue

    res = pd.DataFrame(rows)
    if args.verbose:
        print(f"Scanned {len(syms)} symbols (TF: 1h + 4h + 1d)")
        print(f"Detected {len(res)} coil rows" if not benchmark else f"Produced {len(res)} rows (benchmark mode)")
        
    # Handle empty results
    if res.empty:
        print(f"[WARN] No symbols passed the pipeline filters")
        # Create empty DataFrame with expected columns
        res = pd.DataFrame(columns=["symbol", "coil_pass", "match_pass", "confirm_pass", 
                                   "fast3_width_pct", "bars_in_coil", "tr_range_atr", 
                                   "sma150_slope_bps", "close"])

    # Output
    os.makedirs("out", exist_ok=True)
    out_dir = "out"
    
    # Extract config name from file path and clean it up
    config_name = os.path.splitext(os.path.basename(args.cfg))[0]
    if config_name == "coil_spring":
        config_name = "filtered"  # For coil_spring.yaml (with filters)
    elif config_name == "coil_spring_benchmark":
        config_name = "benchmark"  # For coil_spring_benchmark.yaml (no filters)
    
    # Extract enabled stages for watchlist generation
    enabled_stages = cfg_get(cfg, "control.enabled_stages", ["coil_1h", "match_4h", "confirm_1d"])
    
    write_outputs(res, out_dir, config_name, explicit_out=args.output, enabled_stages=enabled_stages)

if __name__ == "__main__":
    main()