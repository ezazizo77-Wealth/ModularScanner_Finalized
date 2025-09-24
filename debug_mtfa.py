#!/usr/bin/env python3
"""
MTFA Debug Script
Debug the EMA stack direction logic to identify the inversion issue.
"""

import pandas as pd
import numpy as np
import sys
import os
from pathlib import Path

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from indicators import calculate_current_ema_stack_score, compute_mtfa_score, classify_mtfa_strength
import yaml

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

def debug_ema_stack_logic():
    """Debug EMA stack logic with known examples."""
    print("🔍 MTFA EMA Stack Logic Debug")
    print("=" * 50)
    
    # Load configuration
    with open('ttr_config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Test symbols from CSV that show incorrect results
    test_symbols = ['PSGUSDT', 'RSRUSDT', 'KAVAUSDT']
    
    for symbol in test_symbols:
        print(f"\n📊 Debugging {symbol}:")
        print("-" * 30)
        
        # Load data for all timeframes
        symbol_data = {}
        for timeframe in ['1h', '4h', '1d']:
            df = load_ohlcv_data(timeframe)
            if df is not None:
                df_symbol = df[df['symbol'] == symbol].sort_values('ts')
                if not df_symbol.empty:
                    # Calculate EMAs
                    from indicators import ema
                    ema_periods = config['emas']
                    for ema_period in ema_periods:
                        df_symbol[f'ema{ema_period}'] = ema(df_symbol['close'], ema_period)
                    
                    symbol_data[timeframe] = df_symbol
                    print(f"   ✅ {timeframe}: {len(df_symbol)} bars")
                else:
                    print(f"   ❌ {timeframe}: No data")
        
        if symbol_data:
            # Debug EMA stack for each timeframe
            for timeframe, df in symbol_data.items():
                print(f"\n   🕐 {timeframe} EMA Stack Analysis:")
                current_row = df.iloc[-1]
                
                # Get EMA values
                ema_values = {}
                ema_periods = config['emas']
                for ema_period in ema_periods:
                    ema_col = f'ema{ema_period}'
                    if ema_col in current_row.index:
                        ema_values[f'EMA{ema_period}'] = current_row[ema_col]
                        print(f"      {ema_col}: {current_row[ema_col]:.6f}")
                
                # Manual stack analysis
                print(f"\n   📈 Manual Stack Analysis:")
                ema_array = list(ema_values.values())
                ema_names = list(ema_values.keys())
                
                # Check if EMAs are in ascending order (bullish)
                ascending = all(ema_array[i] < ema_array[i+1] for i in range(len(ema_array)-1))
                # Check if EMAs are in descending order (bearish)
                descending = all(ema_array[i] > ema_array[i+1] for i in range(len(ema_array)-1))
                
                print(f"      Ascending order (short < long): {ascending}")
                print(f"      Descending order (short > long): {descending}")
                
                if ascending:
                    print(f"      → This should be BEARISH (short EMAs below long EMAs = downtrend)")
                elif descending:
                    print(f"      → This should be BULLISH (short EMAs above long EMAs = uptrend)")
                else:
                    print(f"      → This should be MIXED (no clear stack)")
                
                # Test current EMA stack score function
                ema_cols = [f'ema{period}' for period in ema_periods]
                current_score, current_direction = calculate_current_ema_stack_score(current_row, ema_cols)
                print(f"      Current function score: ({current_score}, '{current_direction}')")
                
                # Expected score and direction based on manual analysis
                expected_score = 1.0 if (ascending or descending) else 0.0
                expected_direction = 'Bearish' if ascending else ('Bullish' if descending else 'Mixed')
                print(f"      Expected score: ({expected_score}, '{expected_direction}')")
                
                if current_score != expected_score or current_direction != expected_direction:
                    print(f"      🚨 MISMATCH DETECTED!")
                else:
                    print(f"      ✅ Score and direction match expectation")

def main():
    """Main debug function."""
    debug_ema_stack_logic()

if __name__ == "__main__":
    main()
