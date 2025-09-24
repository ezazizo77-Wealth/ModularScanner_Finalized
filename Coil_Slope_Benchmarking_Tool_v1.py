"""
SMA150 Slope Benchmarking Tool (SP004)
Author: A-Team (Aziz + Amy)

Scans Binance USDT spot markets and calculates the slope of SMA150 across user-defined timeframes.
Outputs both % and absolute slope, saves green-listed coins (slope >= threshold), and logs scan stats.
"""

import argparse
import ccxt
import pandas as pd
import ta
from datetime import datetime
from pathlib import Path
import time

# ---------------------------- CLI ARGUMENTS ----------------------------

def get_cli_args():
    parser = argparse.ArgumentParser(description="Slope Scanner CLI")
    parser.add_argument('--timeframes', nargs='+', default=['1h', '4h', '1d'], help='Timeframes to scan')
    parser.add_argument('--threshold', type=float, default=0.005, help='Slope % threshold (e.g. 0.005 = 0.5%)')
    return parser.parse_args()

# ---------------------------- FETCH SYMBOLS ----------------------------

def fetch_usdt_spot_markets():
    exchange = ccxt.binance()
    markets = exchange.load_markets()
    return [
        symbol for symbol, market in markets.items()
        if (
            '/USDT' in symbol and
            market.get('spot') and
            market['active'] and
            not any(x in symbol for x in ['UP/', 'DOWN/', 'BULL/', 'BEAR/'])
        )
    ]

# ---------------------------- FETCH OHLCV ----------------------------

def fetch_ohlcv_data(symbol, timeframe, limit=200):
    exchange = ccxt.binance()
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        print(f"❌ Error fetching {symbol} [{timeframe}]: {e}")
        return None

# ---------------------------- CALCULATE SLOPE ----------------------------

def calculate_sma_slope(df, window=150, lookback=10):
    df['SMA'] = ta.trend.SMAIndicator(df['close'], window=window).sma_indicator()
    df.dropna(inplace=True)
    latest = df.iloc[-1]
    past = df.iloc[-1 - lookback]
    sma_now, sma_past = latest['SMA'], past['SMA']
    slope = (sma_now - sma_past) / sma_past
    return slope, sma_now, sma_past

# ---------------------------- MAIN ----------------------------

def main():
    args = get_cli_args()
    timeframes = args.timeframes
    threshold = args.threshold

    results = []
    match_counts = {tf: 0 for tf in timeframes}

    symbols = fetch_usdt_spot_markets()
    total_coins = len(symbols)
    print(f"\n🔍 Scanning {total_coins} USDT spot pairs across {timeframes}...\n")

    start_time = datetime.utcnow()

    total_scans = 0
    for symbol in symbols:
        for tf in timeframes:
            total_scans += 1
            print(f"📊 {symbol} @ {tf} ... ", end='', flush=True)
            df = fetch_ohlcv_data(symbol, tf)
            if df is None or df.isnull().values.any():
                print("⚠️ Skipped.")
                continue

            try:
                slope, now, past = calculate_sma_slope(df)
                slope_pct = round(slope * 100, 3)
                abs_diff = round(now - past, 4)

                if slope > threshold:
                    results.append({
                        'symbol': symbol,
                        'timeframe': tf,
                        'slope_pct': slope_pct,
                        'sma_now': round(now, 4),
                        'sma_past': round(past, 4),
                        'abs_diff': abs_diff
                    })
                    match_counts[tf] += 1
                    print(f"✅ Slope: {slope_pct}% ↑")
                else:
                    print(f"⏭️ Slope: {slope_pct}%")

            except Exception as e:
                print(f"⚠️ Error: {e}")
                continue

            time.sleep(0.2)

    end_time = datetime.utcnow()
    duration_seconds = (end_time - start_time).total_seconds()
    duration_minutes = round(duration_seconds / 60, 2)

    now_str = datetime.utcnow().strftime('%Y-%m-%d_%H-%M')
    df_out = pd.DataFrame(results)
    out_csv = Path(f"slope_summary_{now_str}.csv")
    df_out.to_csv(out_csv, index=False)

    # Write per-timeframe green lists
    for tf in timeframes:
        tf_df = df_out[df_out['timeframe'] == tf]
        symbols_binance = ','.join([
            f"BINANCE:{symbol.replace('/', '')}"
            for symbol in tf_df['symbol']
        ])
        file_path = Path(f"green_list_{tf}_{now_str}.txt")
        with open(file_path, 'w') as f:
            f.write(symbols_binance)

    # Summary
    print(f"\n✅ Scan complete. {len(results)} matches found across all timeframes.")
    print(f"\n📁 Results saved to: {out_csv}")
    for tf in timeframes:
        print(f"📄 {tf.upper()} Green List saved: green_list_{tf}_{now_str}.txt")

    print("\n⏱️ Scan Summary:")
    print(f"→ Start:    {start_time.strftime('%Y-%m-%d %H:%M')} UTC")
    print(f"→ End:      {end_time.strftime('%Y-%m-%d %H:%M')} UTC")
    print(f"→ Duration: {duration_minutes} minutes")

    print("\n📊 Effectiveness Stats:")
    print(f"→ Total scans performed: {total_scans}")
    print(f"→ Unique coins scanned: {total_coins}")
    for tf in timeframes:
        print(f"→ Matches in {tf}: {match_counts[tf]} (slope >= {threshold*100:.2f}%)")

if __name__ == "__main__":
    main()