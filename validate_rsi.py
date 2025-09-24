#!/usr/bin/env python3
"""
RSI Validation Script
Randomly selects 5 symbols and shows their RSI values across 1h, 4h, 1d timeframes
for comparison with TradingView.
"""

import pandas as pd
import numpy as np
import random
import sys
import os
from pathlib import Path

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from indicators import rsi

def load_ohlcv_data(timeframe: str, input_dir: str = "ohlcv_parquet"):
    """Load OHLCV data for specified timeframe."""
    path = Path(input_dir) / f"ohlcv_{timeframe}.parquet"
    if not path.exists():
        print(f"⚠️ Missing file for {timeframe}: {path}")
        return None
    
    try:
        df = pd.read_parquet(path)
        df = df.reset_index()
        return df
    except Exception as e:
        print(f"❌ Error loading data for {timeframe}: {e}")
        return None

def get_rsi_for_symbol(df, symbol, timeframe):
    """Get RSI value for a specific symbol and timeframe."""
    df_symbol = df[df['symbol'] == symbol].sort_values('ts')
    if len(df_symbol) < 15:  # Need at least 15 bars for RSI(14)
        return None
    
    rsi_values = rsi(df_symbol['close'], 14)
    current_rsi = rsi_values.iloc[-1]
    current_close = df_symbol['close'].iloc[-1]
    
    return {
        'symbol': symbol,
        'timeframe': timeframe,
        'rsi': current_rsi,
        'close': current_close,
        'timestamp': df_symbol['ts'].iloc[-1]
    }

def main():
    print("🔍 RSI Validation - Random Symbol Selection")
    print("=" * 50)
    
    # Load data for all timeframes
    timeframes = ['1h', '4h', '1d']
    data = {}
    
    for tf in timeframes:
        df = load_ohlcv_data(tf)
        if df is not None:
            data[tf] = df
            print(f"✅ Loaded {tf} data: {len(df['symbol'].unique())} symbols")
        else:
            print(f"❌ Failed to load {tf} data")
            return
    
    # Get common symbols across all timeframes
    common_symbols = set(data['1h']['symbol'].unique())
    for tf in timeframes[1:]:
        common_symbols = common_symbols.intersection(set(data[tf]['symbol'].unique()))
    
    common_symbols = list(common_symbols)
    print(f"📊 Common symbols across all timeframes: {len(common_symbols)}")
    
    # Randomly select 5 symbols
    random.seed(42)  # For reproducible results
    selected_symbols = random.sample(common_symbols, min(5, len(common_symbols)))
    
    print(f"\n🎯 Selected symbols for RSI validation:")
    print(f"   {', '.join(selected_symbols)}")
    print()
    
    # Get RSI values for each symbol across all timeframes
    results = []
    
    for symbol in selected_symbols:
        print(f"📈 {symbol}")
        print("-" * 30)
        
        for tf in timeframes:
            result = get_rsi_for_symbol(data[tf], symbol, tf)
            if result:
                print(f"   {tf:2} | RSI: {result['rsi']:6.2f} | Close: ${result['close']:8.4f}")
                results.append(result)
            else:
                print(f"   {tf:2} | Insufficient data")
        print()
    
    # Create summary table
    print("📊 RSI VALIDATION SUMMARY")
    print("=" * 80)
    print(f"{'Symbol':<12} {'1H RSI':<8} {'4H RSI':<8} {'1D RSI':<8} {'1H Close':<10} {'4H Close':<10} {'1D Close':<10}")
    print("-" * 80)
    
    for symbol in selected_symbols:
        rsi_1h = None
        rsi_4h = None
        rsi_1d = None
        close_1h = None
        close_4h = None
        close_1d = None
        
        for result in results:
            if result['symbol'] == symbol:
                if result['timeframe'] == '1h':
                    rsi_1h = result['rsi']
                    close_1h = result['close']
                elif result['timeframe'] == '4h':
                    rsi_4h = result['rsi']
                    close_4h = result['close']
                elif result['timeframe'] == '1d':
                    rsi_1d = result['rsi']
                    close_1d = result['close']
        
        print(f"{symbol:<12} {rsi_1h:<8.2f} {rsi_4h:<8.2f} {rsi_1d:<8.2f} "
              f"{close_1h:<10.4f} {close_4h:<10.4f} {close_1d:<10.4f}")
    
    print()
    print("✅ RSI validation complete!")
    print("📋 Please check these values against TradingView to confirm accuracy.")

if __name__ == "__main__":
    main()
