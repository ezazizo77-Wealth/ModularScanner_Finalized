#!/usr/bin/env python3
"""
analyze_slope_from_parquet.py
Version: 1.4.1
Author: A-Team (Aziz + Amy)

🔍 Description:
Loads OHLCV Parquet files for selected timeframes, calculates slope and angle of a chosen
price basis over a defined lookback period (supporting per-timeframe overrides), and saves
the results (symbol, timeframe, slope %, direction, angle_deg) to CSV/JSON.

✨ Notable Updates (v1.4.1):
- Verbose config echo: prints resolved lookback_map, input/output info (with --verbose)
- Results breakdown by timeframe after saving
- CSV filename format: slope_summary_YYYY-MM-DD___HH-MM.csv (when no -o is given)
- CSV includes a first-line comment header with generated time, resolved lookback map,
  price basis, and direction filter (tools can ignore via comment='#')
- All prior features retained:
  • Angle in degrees (atan of fraction-per-bar)
  • Direction filtering (all / only_up / only_down / only_flat)
  • Sorted output by timeframe + symbol, preserving CLI timeframe order
  • Safer/faster reads (only required columns), NaN handling
  • --lookback-map TF:INT ... per-timeframe overrides
"""

import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict
import numpy as np
import pandas as pd

# ========== DEFAULTS ==========
DEFAULT_INPUT_DIR = Path("ohlcv_parquet")
DEFAULT_LOOKBACK = 30  # updated default
DEFAULT_TIMEFRAMES = ["1h", "4h", "1d"]
DEFAULT_PRICE_BASIS = "close"  # close|open|hlc3|ohlc4
DEFAULT_FORMAT = "csv"          # csv|json
DEFAULT_DIRECTION_FILTER = "all"  # all|only_up|only_down|only_flat

READ_COLS = ["symbol", "timestamp", "open", "high", "low", "close"]
# ==============================


def calculate_slope(y_values: np.ndarray) -> float:
    """Linear slope (Δy/Δx) via polyfit on equally spaced x."""
    x = np.arange(len(y_values))
    slope, _ = np.polyfit(x, y_values, 1)
    return slope


def select_price_basis_series(df_symbol: pd.DataFrame, basis: str) -> np.ndarray:
    """Return the chosen price basis as a float64 numpy array."""
    basis = (basis or "close").lower()
    try:
        if basis == "close":
            return df_symbol["close"].astype(float).values
        if basis == "open":
            return df_symbol["open"].astype(float).values
        if basis == "hlc3":
            df_tmp = df_symbol[["high", "low", "close"]].astype(float)
            return ((df_tmp["high"] + df_tmp["low"] + df_tmp["close"]) / 3.0).values
        if basis == "ohlc4":
            df_tmp = df_symbol[["open", "high", "low", "close"]].astype(float)
            return ((df_tmp["open"] + df_tmp["high"] + df_tmp["low"] + df_tmp["close"]) / 4.0).values
    except Exception:
        # Fall back to close if any casting/index error occurs
        pass
    return df_symbol["close"].astype(float).values


def analyze_slope_for_tf(
    tf: str,
    input_dir: Path,
    lookback: int,
    price_basis: str,
    symbols_filter: Optional[List[str]] = None,
    direction_filter: str = "all",
    verbose: bool = False,
) -> List[dict]:
    """Compute slope metrics for a single timeframe parquet."""
    path = input_dir / f"ohlcv_{tf}.parquet"
    if not path.exists():
        print(f"⚠️ Parquet file not found for {tf}: {path}")
        return []

    try:
        # Read only the columns we need (faster + less memory)
        df = pd.read_parquet(path, columns=READ_COLS)
    except Exception as e:
        print(f"❌ Failed to read parquet for {tf}: {e}")
        return []

    # Ensure required columns exist
    missing = [c for c in ["symbol", "timestamp"] if c not in df.columns]
    if missing:
        print(f"❌ Missing required column(s) {missing} in {path}")
        return []

    # Symbols filtering (optional)
    if symbols_filter:
        df = df[df["symbol"].isin(symbols_filter)]
        if df.empty:
            if verbose:
                print(f"ℹ️ No rows after symbol filter for {tf}.")
            return []

    # Sort once by timestamp for correct rolling windows, then group by symbol
    results: List[dict] = []
    for symbol, df_symbol in df.sort_values("timestamp").groupby("symbol", sort=False):
        if len(df_symbol) < lookback:
            continue

        price_series = select_price_basis_series(df_symbol, price_basis)
        # Drop NaN, then take the last lookback window
        price_series = pd.Series(price_series, dtype="float64").dropna().values
        price_series = price_series[-lookback:]
        if len(price_series) < lookback:
            continue

        slope = calculate_slope(price_series)
        # Percent change per bar relative to the first value in the window
        slope_pct_per_bar = (slope / price_series[0]) * 100.0
        slope_pct = round(float(slope_pct_per_bar), 3)

        # Convert percent-per-bar to fraction-per-bar before atan
        slope_angle_deg = round(float(np.degrees(np.arctan(slope_pct_per_bar / 100.0))), 2)

        direction = "Up" if slope_pct > 0 else ("Down" if slope_pct < 0 else "Flat")

        # Optional direction filtering
        if (
            (direction_filter == "only_up" and direction != "Up") or
            (direction_filter == "only_down" and direction != "Down") or
            (direction_filter == "only_flat" and direction != "Flat")
        ):
            continue

        results.append(
            {
                "symbol": symbol,
                "timeframe": tf,
                "slope_%": slope_pct,
                "direction": direction,
                "angle_deg": slope_angle_deg,
            }
        )

    return results


def parse_lookback_map(items: Optional[List[str]]) -> Dict[str, int]:
    """
    Parse lookback map entries like ["1h:30","4h:72","1d:120"] into {"1h":30,...}.
    """
    mapping: Dict[str, int] = {}
    if not items:
        return mapping
    for item in items:
        try:
            tf, val = item.split(":")
            mapping[tf.strip()] = int(val)
        except Exception:
            raise argparse.ArgumentTypeError(
                f"Invalid --lookback-map entry '{item}'. Use format TF:INT (e.g., 1h:30)"
            )
    return mapping


def main() -> None:
    parser = argparse.ArgumentParser(
        description="📈 Analyze slope and angle from OHLCV parquet files"
    )
    parser.add_argument("-i", "--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("-l", "--lookback", type=int, default=DEFAULT_LOOKBACK)
    parser.add_argument(
        "-t", "--timeframes", nargs="+", default=DEFAULT_TIMEFRAMES,
        help="One or more timeframes to process (e.g., 1h 4h 1d)"
    )
    parser.add_argument("-s", "--symbols", nargs="+", default=None)
    parser.add_argument(
        "-p", "--price-basis",
        choices=["close", "open", "hlc3", "ohlc4"],
        default=DEFAULT_PRICE_BASIS
    )
    parser.add_argument(
        "-f", "--format",
        choices=["csv", "json"],
        default=DEFAULT_FORMAT
    )
    parser.add_argument("-o", "--output", type=str, default=None)
    parser.add_argument("--no-timestamp", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument(
        "-d", "--direction",
        choices=["all", "only_up", "only_down", "only_flat"],
        default=DEFAULT_DIRECTION_FILTER
    )
    parser.add_argument(
        "--lookback-map", nargs="+", metavar="TF:INT",
        help="Override lookback per timeframe, e.g. 1h:30 4h:72 1d:120"
    )

    args = parser.parse_args()
    lb_map = parse_lookback_map(args.lookback_map)

    # --- Build default output filename with human-friendly timestamp ---
    now = datetime.now()
    iso_date = now.strftime("%Y-%m-%d")
    iso_time = now.strftime("%H-%M")
    if args.output:
        output_file = args.output
    else:
        if args.format == "json":
            # keep JSON default naming if needed
            suffix = "" if args.no_timestamp else f"_{now.strftime('%Y%m%d_%H%M')}"
            output_file = f"slope_summary{suffix}.json"
        else:
            # new CSV naming: slope_summary_YYYY-MM-DD___HH-MM.csv
            if args.no_timestamp:
                output_file = "slope_summary.csv"
            else:
                output_file = f"slope_summary_{iso_date}___{iso_time}.csv"

    # --- Verbose config echo ---
    if args.verbose:
        resolved_lb = {tf: lb_map.get(tf, args.lookback) for tf in args.timeframes}
        print("[CONFIG]")
        print(f"  input_dir      : {args.input_dir}")
        print(f"  timeframes     : {args.timeframes}")
        print(f"  lookback (def) : {args.lookback}")
        print(f"  lookback_map   : {lb_map or '{}'}")
        print(f"  resolved_lb    : {resolved_lb}")
        print(f"  price_basis    : {args.price_basis}")
        print(f"  direction      : {args.direction}")
        print(f"  read_columns   : {READ_COLS}")
        print(f"  output_file    : {output_file}")
        print("")

    all_results: List[dict] = []
    for tf in args.timeframes:
        lookback_tf = lb_map.get(tf, args.lookback)
        if args.verbose:
            print(f"➡️ Processing timeframe: {tf} (lookback={lookback_tf})")
        results = analyze_slope_for_tf(
            tf=tf,
            input_dir=args.input_dir,
            lookback=lookback_tf,
            price_basis=args.price_basis,
            symbols_filter=args.symbols,
            direction_filter=args.direction,
            verbose=args.verbose,
        )
        all_results.extend(results)

    df_out = pd.DataFrame(all_results)
    if not df_out.empty:
        # Preserve CLI order of timeframes when sorting
        df_out["timeframe"] = pd.Categorical(
            df_out["timeframe"], categories=args.timeframes, ordered=True
        )
        df_out = df_out.sort_values(by=["timeframe", "symbol"]).reset_index(drop=True)
    else:
        df_out = pd.DataFrame(
            columns=["symbol", "timeframe", "slope_%", "direction", "angle_deg"]
        )

    # --- Write output (CSV with metadata header, or JSON as-is) ---
    if args.format == "json":
        df_out.to_json(output_file, orient="records")
    else:
        # Compose a human-friendly lookback summary for the header
        resolved_pairs = [f"{tf}={lb_map.get(tf, args.lookback)}" for tf in args.timeframes]
        lookback_summary = ",".join(resolved_pairs)
        header_line = (
            f"# Generated: {iso_date} {iso_time} | "
            f"Lookback Map: {lookback_summary} | "
            f"Basis: {args.price_basis} | Direction: {args.direction}"
        )

        # Write CSV headers first, then metadata comment, then data
        with open(output_file, "w", newline="") as f:
            f.write("symbol,timeframe,slope_%,direction,angle_deg\n")
            f.write(header_line + "\n")
            df_out.to_csv(f, index=False, header=False)

    print(f"✅ Saved slope summary to {output_file} with {len(df_out)} rows.")

    # --- Results breakdown by timeframe ---
    if not df_out.empty:
        per_tf_counts = (
            df_out.groupby("timeframe")["symbol"].nunique().reindex(args.timeframes, fill_value=0)
        )
        print("\n[RESULTS BREAKDOWN]")
        for tf, cnt in per_tf_counts.items():
            print(f"  {tf}: {int(cnt)} symbols")
        print(f"  TOTAL: {df_out['symbol'].nunique()} symbols")


if __name__ == "__main__":
    main()