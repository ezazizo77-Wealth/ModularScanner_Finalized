"""
Slope + Coil Scanner (SP004 Extended)
Version: 1.0.2
Last Updated: 2025-07-31
Author: A-Team (Aziz + Amy)

📌 Description:
    - Fetches Binance USDT spot market OHLCV data
    - Computes SMA150 and EMA (5, 13, 50, 20) indicators
    - Calculates slope over configurable lookback periods
    - Filters coins based on coil conditions (optional)
    - Logs detailed condition failures and slope rejections
    - Exports green-listed coins and performance stats

🧩 Configurable via: arnold.config.yaml or test.config.yaml

📁 Outputs:
    - slope_results_<timestamp>.csv         → Full slope data
    - green_list_<tf>_<timestamp>.txt       → Matches per timeframe
    - slope_failures_<timestamp>.csv        → Optional log of rejected symbols/slopes

✅ Recommended for:
    - Market benchmarking
    - Filtering coins with bullish structure
    - Daily slope & coil screening

🔧 Next version goals:
    - Multi-config support
    - Live scheduling
    - Modular strategy plug-ins
"""

import ccxt
import pandas as pd
import ta
import yaml
import time
import sys
from datetime import datetime
from pathlib import Path

# Load config
config_path = sys.argv[1] if len(sys.argv) > 1 else "arnold.config.yaml"
with open(config_path, "r") as f:
    config = yaml.safe_load(f)

scanner_cfg = config['scanner']
coil_cfg = config.get('coil_conditions', {})
indicators_cfg = config['indicators']

USE_TEST_MODE = scanner_cfg.get("use_test_symbols", False)
test_symbols = scanner_cfg.get("test_symbols", [])

def fetch_usdt_spot_markets():
    exchange = ccxt.binance()
    markets = exchange.load_markets()
    return [
        s for s, m in markets.items()
        if '/USDT' in s and m.get('spot') and m['active'] and not any(x in s for x in ['UP/', 'DOWN/', 'BULL/', 'BEAR/'])
    ]

def fetch_ohlcv(symbol, tf, limit):
    exchange = ccxt.binance()
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        print(f"❌ Error fetching {symbol} [{tf}]: {e}")
        return None

def calculate_indicators(df):
    if indicators_cfg['sma']['enabled']:
        df['SMA150'] = ta.trend.SMAIndicator(df['close'], window=indicators_cfg['sma']['period']).sma_indicator()
    for ema in indicators_cfg['ema']:
        col = ema['name'].upper()
        df[col] = ta.trend.EMAIndicator(df['close'], window=ema['period']).ema_indicator()
    df.dropna(inplace=True)
    return df

def calculate_slope(df, col, lookback):
    if len(df) <= lookback:
        return None  # Not enough data to calculate slope
    latest = df.iloc[-1]
    past = df.iloc[-1 - lookback]
    return (latest[col] - past[col]) / past[col]

def check_coil_conditions(df, log=False):
    latest = df.iloc[-1]
    past = df.iloc[-1 - coil_cfg['slope_check']['lookback']]
    logs = []

    cond1 = latest['EMA5'] > latest['EMA13'] > latest['EMA50']
    if not cond1: logs.append("EMA order failed (EMA5 > EMA13 > EMA50)")

    cond2 = latest['EMA50'] > latest['SMA150']
    if not cond2: logs.append("EMA50 not above SMA150")

    coil_gap = abs(latest['EMA5'] - latest['EMA50']) / latest['EMA50']
    cond3 = coil_gap < coil_cfg['coil_gap_check']['threshold']
    if not cond3: logs.append(f"EMA gap too wide: {coil_gap:.4f}")

    slope = (latest['SMA150'] - past['SMA150']) / past['SMA150']
    cond4 = slope > coil_cfg['slope_check']['threshold']
    if not cond4: logs.append(f"SMA slope too flat: {slope:.4f}")

    if cond1 and cond2 and cond3 and cond4:
        return True, None
    else:
        return False, logs if log else None

def run_scan():
    start = datetime.utcnow()
    results = []
    failures = []
    matches = {tf: [] for tf in scanner_cfg['timeframes']}

    if USE_TEST_MODE:
        symbols = test_symbols
        print("\n🧪 Test mode: Using manually specified top 10 coins")
    else:
        symbols = fetch_usdt_spot_markets()

    total_pairs = len(symbols)
    print(f"\n🔍 Scanning {len(scanner_cfg['timeframes'])} TFs over {total_pairs} symbols...\n")

    for symbol in symbols:
        for tf in scanner_cfg['timeframes']:
            df = fetch_ohlcv(symbol, tf, scanner_cfg['data_limit'])
            if df is None or df.isnull().values.any():
                continue

            df = calculate_indicators(df)
            slope = calculate_slope(df, 'SMA150', scanner_cfg['lookback'])

            if slope is None:
                continue  # Not enough data

            slope_pct = round(slope * 100, 3)

            if slope >= scanner_cfg['slope_threshold']:
                match_info = {'symbol': symbol, 'timeframe': tf, 'slope_pct': slope_pct}

                if coil_cfg.get('enabled', False):
                    passed, reasons = check_coil_conditions(df, log=scanner_cfg.get('log_conditions', False))
                    if passed:
                        print(f"✅ {symbol} [{tf}] Slope: {slope_pct}% ↑")
                        matches[tf].append(symbol)
                    else:
                        if scanner_cfg.get('log_conditions', False):
                            print(f"❌ {symbol} [{tf}] Failed:")
                            for r in reasons:
                                print(f"   - {r}")
                else:
                    print(f"✅ {symbol} [{tf}] Slope: {slope_pct}% ↑")
                    matches[tf].append(symbol)

                results.append(match_info)

            else:
                print(f"↘️ {symbol} [{tf}] Slope: {slope_pct}% < Threshold")
                failures.append({"symbol": symbol, "timeframe": tf, "slope_pct": slope_pct})

            time.sleep(scanner_cfg['delay_between_requests'])

    now_str = datetime.utcnow().strftime('%Y-%m-%d_%H-%M')
    pd.DataFrame(results).to_csv(f"slope_results_{now_str}.csv", index=False)
    pd.DataFrame(failures).to_csv(f"slope_failures_{now_str}.csv", index=False)

    for tf, coins in matches.items():
        with open(f"green_list_{tf}_{now_str}.txt", 'w') as f:
            f.write("Binance:" + ",".join([s.replace("/", "") for s in coins]))

    end = datetime.utcnow()
    duration_min = round((end - start).total_seconds() / 60, 2)

    print("\n⏱️ Scan Summary:")
    print(f"→ Start:    {start.strftime('%Y-%m-%d %H:%M')} UTC")
    print(f"→ End:      {end.strftime('%Y-%m-%d %H:%M')} UTC")
    print(f"→ Duration: {duration_min} minutes")

    print("\n📊 Effectiveness Stats:")
    print(f"→ Total scanned coins: {total_pairs}")
    for tf in scanner_cfg['timeframes']:
        count = len(matches[tf])
        pct = (count / total_pairs) * 100
        print(f"→ Matches in {tf}: {count} ({pct:.2f}%)")

if __name__ == "__main__":
    run_scan()