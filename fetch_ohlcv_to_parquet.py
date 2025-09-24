"""
fetch_ohlcv_to_parquet.py
Version: 1.0.2
Author: A-Team (Aziz + Amy)

🔍 Description:
Fetches OHLCV data from Binance for selected symbols and timeframes, then stores the results
in centralized Parquet files by timeframe with multi-indexed rows (symbol + timestamp).
Includes error handling, minimum data validation, and logging.

✨ Future Enhancements (TODO):
- CLI support for --tf, --symbols
- Daily cron-based incremental updates
- Metadata caching (skipped/failed coins)
"""

import ccxt
import pandas as pd
import pyarrow.parquet as pq
import pyarrow as pa
from pathlib import Path
from datetime import datetime
import os
import time

# ==== CONFIGURABLE SECTION ====
TIMEFRAMES = ['1h', '4h', '1d']
LOOKBACK = 200
OUTPUT_DIR = Path("ohlcv_parquet")
TEST_SYMBOLS = [
    'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT',
    'ADA/USDT', 'DOGE/USDT', 'LINK/USDT', 'AVAX/USDT', 'MATIC/USDT'
]
USE_TEST_MODE = True
# ==============================

def fetch_symbols():
    if USE_TEST_MODE:
        return TEST_SYMBOLS
    exchange = ccxt.binance({
    'options': {
        'defaultType': 'spot'  # Enforce spot market only
    }
})
    markets = exchange.load_markets()
    return [
        s for s, m in markets.items()
        if '/USDT' in s and m.get('spot') and m['active']
           and not any(x in s for x in ['UP/', 'DOWN/', 'BULL/', 'BEAR/'])
    ]

def fetch_ohlcv(symbol, tf, limit):  
    exchange = ccxt.binance({
        'options': {
            'defaultType': 'spot'  # Enforce spot market only
        }
    })
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['symbol'] = symbol
        return df
    except Exception as e:
        print(f"❌ Error fetching {symbol} [{tf}]: {e}")
        return None

def save_to_parquet(df, tf):
    file_path = OUTPUT_DIR / f"ohlcv_{tf}.parquet"
    table = pa.Table.from_pandas(df)
    if not file_path.exists():
        pq.write_table(table, file_path)
    else:
        with pq.ParquetWriter(file_path, table.schema, use_dictionary=True) as writer:
            writer.write_table(table)

def main():
    job_start = datetime.now()
    start = time.time()
    OUTPUT_DIR.mkdir(exist_ok=True)

    print(f"🕰️ Job started at {job_start.strftime('%Y-%m-%d %H:%M:%S')}")
    symbols = fetch_symbols()
    print(f"🔁 Fetching OHLCV for {len(symbols)} symbols x {len(TIMEFRAMES)} TFs")

    for tf in TIMEFRAMES:
        collected = []
        for symbol in symbols:
            df = fetch_ohlcv(symbol, tf, LOOKBACK)
            if df is None:
                continue
            if len(df) < LOOKBACK:
                print(f"⚠️ {symbol} [{tf}] skipped: only {len(df)} rows")
                continue
            df.set_index(['symbol', 'timestamp'], inplace=True)
            collected.append(df)
            time.sleep(0.15)

        skipped = len(symbols) - len(collected)
        print(f"ℹ️ {skipped} symbol(s) skipped due to insufficient rows for [{tf}]")

        if collected:
            full_df = pd.concat(collected)
            save_to_parquet(full_df, tf)
            print(f"✅ Saved {len(full_df)} rows to ohlcv_{tf}.parquet")
        else:
            print(f"❌ No valid data to save for {tf}")

    elapsed = round(time.time() - start)
    minutes, seconds = divmod(elapsed, 60)
    job_end = datetime.now()

    print(f"\n⏱️ Finished in {minutes}m {seconds}s")
    print(f"🕓 Job ended at {job_end.strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()