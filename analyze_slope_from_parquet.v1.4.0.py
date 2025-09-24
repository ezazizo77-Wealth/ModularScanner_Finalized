#!/usr/bin/env python3
"""
fetch_ohlcv_to_parquet_v1.1.1
Enhanced with:
- --verbose flag for optional detailed logging
- Per-timeframe results breakdown
"""

import argparse
import pandas as pd
import ccxt
import os
from datetime import datetime, timedelta
import yaml
from collections import defaultdict

def parse_args():
    parser = argparse.ArgumentParser(description="Fetch OHLCV data and save to Parquet.")
    parser.add_argument("config", type=str, help="Path to YAML config file")
    parser.add_argument("--lookback-map", type=str, default=None,
                        help="Custom lookback per timeframe in JSON-like format, e.g. '{\"1h\":72,\"4h\":60}'")
    parser.add_argument("--verbose", action="store_true",
                        help="Enable detailed logging")
    return parser.parse_args()

def load_config(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)

def parse_lookback_map(arg_val, default_map):
    import json
    if arg_val:
        try:
            return json.loads(arg_val)
        except Exception as e:
            raise ValueError(f"Invalid --lookback-map format: {e}")
    return default_map

def fetch_ohlcv(exchange, symbol, timeframe, since, limit, verbose=False):
    try:
        if verbose:
            print(f"[DEBUG] Fetching {symbol} {timeframe} since {since}")
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=limit)
        df = pd.DataFrame(
            ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        return df
    except Exception as e:
        print(f"[ERROR] Failed to fetch {symbol} {timeframe}: {e}")
        return None

def save_parquet(df, filepath):
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        df.to_parquet(filepath, index=False)
    except Exception as e:
        print(f"[ERROR] Failed to save {filepath}: {e}")

def main():
    args = parse_args()
    config = load_config(args.config)

    exchange_id = config.get("exchange", "binance")
    api_key = config.get("apiKey", "")
    secret = config.get("secret", "")
    timeframes = config.get("timeframes", ["1h", "4h", "1d"])
    symbols = config.get("symbols", [])
    lookback_map = parse_lookback_map(args.lookback_map, config.get("lookback_map", {}))
    output_dir = config.get("output_dir", "data")

    if args.verbose:
        print(f"[INFO] Using exchange: {exchange_id}")
        print(f"[INFO] Timeframes: {timeframes}")
        print(f"[INFO] Lookback map: {lookback_map}")

    exchange_class = getattr(ccxt, exchange_id)
    exchange = exchange_class({
        "apiKey": api_key,
        "secret": secret,
        "enableRateLimit": True
    })

    results_count = defaultdict(int)

    for timeframe in timeframes:
        lookback = lookback_map.get(timeframe, 100)
        since = exchange.milliseconds() - lookback * exchange.parse_timeframe(timeframe) * 1000

        for symbol in symbols:
            df = fetch_ohlcv(exchange, symbol, timeframe, since, lookback, verbose=args.verbose)
            if df is not None and not df.empty:
                save_path = os.path.join(output_dir, timeframe, f"{symbol.replace('/', '_')}.parquet")
                save_parquet(df, save_path)
                results_count[timeframe] += 1

    # Final results
    print("\n[RESULTS BREAKDOWN]")
    for tf in timeframes:
        print(f"  {tf}: {results_count[tf]} symbols updated")
    print(f"  TOTAL: {sum(results_count.values())} symbols updated")

if __name__ == "__main__":
    main()