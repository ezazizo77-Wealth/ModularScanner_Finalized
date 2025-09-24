"""
analyze_slope_from_parquet.py
Version: 1.3.0
Author: A-Team (Aziz + Amy)

🔍 Description:
Loads OHLCV Parquet files for selected timeframes, calculates slope and angle of a chosen price basis
over a defined lookback period, and saves the results (symbol, tf, slope %, direction, angle) to a CSV/JSON.

✨ Updates:
- v1.3.0:
  ✅ Added slope angle in degrees
  ✅ CLI option to filter by direction
  ✅ Sort output by timeframe + symbol
  ✅ Safer error handling on file read
"""

import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import numpy as np
import pandas as pd

# ========== DEFAULTS ==========
DEFAULT_INPUT_DIR = Path("ohlcv_parquet")
DEFAULT_LOOKBACK = 10
DEFAULT_TIMEFRAMES = ["1h", "4h", "1d"]
DEFAULT_PRICE_BASIS = "close"
DEFAULT_FORMAT = "csv"
DEFAULT_DIRECTION_FILTER = "all"  # all, only_up, only_down, only_flat
# ==============================

def calculate_slope(y_values):
    x = np.arange(len(y_values))
    slope, _ = np.polyfit(x, y_values, 1)
    return slope

def select_price_basis_series(df_symbol: pd.DataFrame, basis: str) -> np.ndarray:
    basis = (basis or "close").lower()
    try:
        if basis == "close":
            return df_symbol["close"].astype(float).values
        if basis == "open":
            return df_symbol["open"].astype(float).values
        if basis == "hlc3":
            # Cast once for numeric stability
            df_tmp = df_symbol[["high", "low", "close"]].astype(float)
            return ((df_tmp["high"] + df_tmp["low"] + df_tmp["close"]) / 3.0).values
        if basis == "ohlc4":
            df_tmp = df_symbol[["open", "high", "low", "close"]].astype(float)
            return (
                (df_tmp["open"] + df_tmp["high"] + df_tmp["low"] + df_tmp["close"]) / 4.0
            ).values
    except Exception:
        pass
    return df_symbol["close"].astype(float).values  # fallback

def analyze_slope_for_tf(
    tf: str,
    input_dir: Path,
    lookback: int,
    price_basis: str,
    symbols_filter: Optional[List[str]] = None,
    direction_filter: str = "all",
    verbose: bool = False,
):
    path = input_dir / f"ohlcv_{tf}.parquet"
    if not path.exists():
        print(f"⚠️ Parquet file not found for {tf}: {path}")
        return []

    try:
        df = pd.read_parquet(path)
    except Exception as e:
        print(f"❌ Failed to read parquet for {tf}: {e}")
        return []

    df = df.reset_index()

    if symbols_filter:
        df = df[df["symbol"].isin(symbols_filter)]
        if df.empty and verbose:
            print(f"ℹ️ No rows after symbol filter for {tf}.")
            return []

    results = []
    # Sort once, then group for performance
    for symbol, df_symbol in df.sort_values('timestamp').groupby('symbol', sort=False):
        if len(df_symbol) < lookback:
            continue

        price_series = select_price_basis_series(df_symbol, price_basis)
        price_series = price_series[-lookback:]
        if len(price_series) < lookback:
            continue

        slope = calculate_slope(price_series)
        # Percent change per bar
        slope_pct_per_bar = (slope / price_series[0]) * 100.0
        slope_pct = round(slope_pct_per_bar, 3)
        # Angle based on unit-correct fraction (percent -> fraction)
        slope_angle_deg = round(np.degrees(np.arctan(slope_pct_per_bar / 100.0)), 2)
        direction = 'Up' if slope_pct > 0 else ('Down' if slope_pct < 0 else 'Flat')

        # Filter direction if needed
        if (
            direction_filter == "only_up" and direction != "Up" or
            direction_filter == "only_down" and direction != "Down" or
            direction_filter == "only_flat" and direction != "Flat"
        ):
            continue

        results.append({
            'symbol': symbol,
            'timeframe': tf,
            'slope_%': slope_pct,
            'direction': direction,
            'angle_deg': slope_angle_deg
        })

    return results

def main():
    parser = argparse.ArgumentParser(description="📈 Analyze slope and angle from OHLCV parquet files")
    parser.add_argument("-i", "--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("-l", "--lookback", type=int, default=DEFAULT_LOOKBACK)
    parser.add_argument("-t", "--timeframes", nargs="+", default=DEFAULT_TIMEFRAMES)
    parser.add_argument("-s", "--symbols", nargs="+", default=None)
    parser.add_argument("-p", "--price-basis", choices=["close", "open", "hlc3", "ohlc4"], default=DEFAULT_PRICE_BASIS)
    parser.add_argument("-f", "--format", choices=["csv", "json"], default=DEFAULT_FORMAT)
    parser.add_argument("-o", "--output", type=str, default=None)
    parser.add_argument("--no-timestamp", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-d", "--direction", choices=["all", "only_up", "only_down", "only_flat"], default=DEFAULT_DIRECTION_FILTER)

    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    if args.output:
        output_file = args.output
    else:
        base_name = "slope_summary"
        suffix = "" if args.no_timestamp else f"_{timestamp}"
        extension = "json" if args.format == "json" else "csv"
        output_file = f"{base_name}{suffix}.{extension}"

    all_results = []
    for tf in args.timeframes:
        if args.verbose:
            print(f"➡️ Processing timeframe: {tf}")
        results = analyze_slope_for_tf(
            tf=tf,
            input_dir=args.input_dir,
            lookback=args.lookback,
            price_basis=args.price_basis,
            symbols_filter=args.symbols,
            direction_filter=args.direction,
            verbose=args.verbose,
        )
        all_results.extend(results)

    df_out = pd.DataFrame(all_results)
    if not df_out.empty:
        # Preserve CLI order of timeframes when sorting
        df_out["timeframe"] = pd.Categorical(df_out["timeframe"], categories=args.timeframes, ordered=True)
        df_out = df_out.sort_values(by=["timeframe", "symbol"]).reset_index(drop=True)
    else:
        df_out = pd.DataFrame(columns=["symbol", "timeframe", "slope_%", "direction", "angle_deg"]) 
    if args.format == "json":
        df_out.to_json(output_file, orient="records")
    else:
        df_out.to_csv(output_file, index=False)
    print(f"✅ Saved slope summary to {output_file} with {len(df_out)} rows.")

if __name__ == "__main__":
    main()