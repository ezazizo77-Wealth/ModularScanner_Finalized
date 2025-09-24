"""
trend_radar_stack_analyzer.py
Version: 1.0.0
Author: A-Team (Aziz + Amy)

🔍 Description:
Analyzes EMA stacking across multiple timeframes and outputs a report showing
whether the EMAs are stacked in bullish, bearish, or mixed order for each symbol.

✨ Features:
- Calculates EMAs (5, 13, 21, 50, 200) for 1h, 4h, and 1d timeframes
- Detects stacking order (bullish, bearish, mixed)
- Identifies which EMAs break the stack
- Outputs to a timestamped CSV
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

# ========== CONFIGURATION ==========
INPUT_DIR = Path("ohlcv_parquet")
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M")
OUTPUT_FILE = f"trend_radar_stack_report_{TIMESTAMP}.csv"
TIMEFRAMES = ['1h', '4h', '1d']
EMAs = [5, 13, 21, 50, 200]
# ===================================


def detect_stack(ema_values):
    """Check if EMAs are stacked in bullish or bearish order and return status and breaker."""
    ema_names = list(ema_values.keys())
    ema_array = np.array(list(ema_values.values()))

    # Bullish: EMA5 < EMA13 < EMA21 < EMA50 < EMA200
    bullish = np.all(np.diff(ema_array) > 0)
    # Bearish: EMA5 > EMA13 > EMA21 > EMA50 > EMA200
    bearish = np.all(np.diff(ema_array) < 0)

    if bullish:
        return 'Bullish Stack', None
    elif bearish:
        return 'Bearish Stack', None
    else:
        # Find the first place where the stack breaks
        for i in range(len(ema_array) - 1):
            if (ema_array[i] > ema_array[i+1]) and (ema_array[0] < ema_array[-1]):
                return 'Bullish Broken', ema_names[i]
            elif (ema_array[i] < ema_array[i+1]) and (ema_array[0] > ema_array[-1]):
                return 'Bearish Broken', ema_names[i]
        return 'Mixed/Choppy', None


def analyze_emas_for_tf(tf):
    path = INPUT_DIR / f"ohlcv_{tf}.parquet"
    if not path.exists():
        print(f"⚠️ Missing file for {tf}: {path}")
        return []

    df = pd.read_parquet(path)
    df = df.reset_index()  # Ensure columns: symbol, timestamp, open, high, low, close, volume

    results = []
    for symbol in df['symbol'].unique():
        df_symbol = df[df['symbol'] == symbol].sort_values('timestamp')
        if len(df_symbol) < max(EMAs):
            continue

        # Compute EMAs
        ema_values = {}
        for ema in EMAs:
            df_symbol[f'ema_{ema}'] = df_symbol['close'].ewm(span=ema, adjust=False).mean()
            ema_values[f'EMA{ema}'] = df_symbol[f'ema_{ema}'].iloc[-1]

        stack_status, broken_level = detect_stack(ema_values)

        results.append({
            'symbol': symbol,
            'timeframe': tf,
            'stack_status': stack_status,
            'broken_level': broken_level if broken_level else '-',
            **ema_values
        })

    return results


def main():
    all_results = []
    for tf in TIMEFRAMES:
        print(f"📊 Analyzing timeframe: {tf}")
        results = analyze_emas_for_tf(tf)
        all_results.extend(results)

    df_out = pd.DataFrame(all_results)
    df_out.to_csv(OUTPUT_FILE, index=False)
    print(f"✅ Trend Radar Stack Report saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()