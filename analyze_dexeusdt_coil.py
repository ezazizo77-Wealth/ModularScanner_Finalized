#!/usr/bin/env python3
"""
Detailed analysis of DEXEUSDT coil formation for Sep 13-17, 2024
"""

import pandas as pd
import sys
import os
import yaml

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from indicators import compute_features
from coil_spring import pipeline

def analyze_dexeusdt_coil():
    """Analyze DEXEUSDT coil formation in detail."""
    
    print("🔍 DEXEUSDT Coil Analysis - Sep 13-17, 2024")
    print("=" * 60)
    
    # Load configuration
    with open('coil_spring_p004_optimized.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    print(f"📊 Configuration loaded")
    print(f"   Min bars in coil: {config['coil_1h']['min_bars_in_coil']}")
    print(f"   Max TR range ATR: {config['match_4h']['max_tr_range_atr']}")
    print(f"   Min SMA150 slope: {config['confirm_1d']['min_sma150_slope_pct']}")
    print()
    
    # Load data
    print("📈 Loading DEXEUSDT data...")
    
    # Load 1h data
    df_1h = pd.read_parquet('ohlcv_parquet/ohlcv_1h.parquet')
    dexe_1h = df_1h[(df_1h['symbol'] == 'DEXEUSDT') & 
                    (df_1h['ts'] >= '2024-09-13') & 
                    (df_1h['ts'] <= '2024-09-17')].copy()
    
    # Load 4h data
    df_4h = pd.read_parquet('ohlcv_parquet/ohlcv_4h.parquet')
    dexe_4h = df_4h[(df_4h['symbol'] == 'DEXEUSDT') & 
                    (df_4h['ts'] >= '2024-09-13') & 
                    (df_4h['ts'] <= '2024-09-17')].copy()
    
    # Load 1d data
    df_1d = pd.read_parquet('ohlcv_parquet/ohlcv_1d.parquet')
    dexe_1d = df_1d[(df_1d['symbol'] == 'DEXEUSDT') & 
                    (df_1d['ts'] >= '2024-09-13') & 
                    (df_1d['ts'] <= '2024-09-17')].copy()
    
    print(f"✅ 1h data: {len(dexe_1h)} bars")
    print(f"✅ 4h data: {len(dexe_4h)} bars") 
    print(f"✅ 1d data: {len(dexe_1d)} bars")
    print()
    
    if dexe_1h.empty or dexe_4h.empty or dexe_1d.empty:
        print("❌ Missing data for analysis")
        return
    
    # Sort data by timestamp
    dexe_1h = dexe_1h.sort_values('ts').reset_index(drop=True)
    dexe_4h = dexe_4h.sort_values('ts').reset_index(drop=True)
    dexe_1d = dexe_1d.sort_values('ts').reset_index(drop=True)
    
    # Compute features for each timeframe
    print("🧮 Computing technical indicators...")
    
    # Add timeframe column
    dexe_1h['timeframe'] = '1h'
    dexe_4h['timeframe'] = '4h'
    dexe_1d['timeframe'] = '1d'
    
    # Compute features
    dexe_1h = compute_features(dexe_1h, config)
    dexe_4h = compute_features(dexe_4h, config)
    dexe_1d = compute_features(dexe_1d, config)
    
    print("✅ Technical indicators computed")
    print()
    
    # Analyze 1h coil formation
    print("🕐 1H COIL ANALYSIS:")
    print("-" * 30)
    
    # Check if we have enough data
    min_bars = config['coil_1h']['min_bars_in_coil']
    if len(dexe_1h) < min_bars:
        print(f"❌ Insufficient 1h data: {len(dexe_1h)} bars < {min_bars} required")
    else:
        print(f"✅ Sufficient 1h data: {len(dexe_1h)} bars ≥ {min_bars} required")
        
        # Check FAST3_WIDTH_PCT
        if 'FAST3_WIDTH_PCT' in dexe_1h.columns:
            max_width = dexe_1h['FAST3_WIDTH_PCT'].max()
            print(f"   FAST3_WIDTH_PCT: {max_width:.2f}%")
            
            if max_width <= 2.0:  # Assuming 2% max width threshold
                print(f"   ✅ Width criteria met: {max_width:.2f}% ≤ 2.0%")
            else:
                print(f"   ❌ Width criteria failed: {max_width:.2f}% > 2.0%")
        
        # Check TR_RANGE_ATR
        if 'TR_RANGE_ATR' in dexe_1h.columns:
            max_tr_atr = dexe_1h['TR_RANGE_ATR'].max()
            print(f"   TR_RANGE_ATR: {max_tr_atr:.3f}")
            
            if max_tr_atr <= 1.2:  # Assuming 1.2 max TR/ATR threshold
                print(f"   ✅ Volatility criteria met: {max_tr_atr:.3f} ≤ 1.2")
            else:
                print(f"   ❌ Volatility criteria failed: {max_tr_atr:.3f} > 1.2")
        
        # Check SMA150_SLOPE_BPS
        if 'SMA150_SLOPE_BPS' in dexe_1h.columns:
            min_slope = dexe_1h['SMA150_SLOPE_BPS'].min()
            print(f"   SMA150_SLOPE_BPS: {min_slope:.2f}")
            
            if min_slope >= -3.0:  # Assuming -3% min slope threshold
                print(f"   ✅ Slope criteria met: {min_slope:.2f} ≥ -3.0%")
            else:
                print(f"   ❌ Slope criteria failed: {min_slope:.2f} < -3.0%")
    
    print()
    
    # Analyze 4h matching
    print("🕐 4H MATCHING ANALYSIS:")
    print("-" * 30)
    
    if len(dexe_4h) < 5:  # Assuming minimum bars needed
        print(f"❌ Insufficient 4h data: {len(dexe_4h)} bars")
    else:
        print(f"✅ Sufficient 4h data: {len(dexe_4h)} bars")
        
        # Check TR_RANGE_ATR for 4h
        if 'TR_RANGE_ATR' in dexe_4h.columns:
            max_tr_atr_4h = dexe_4h['TR_RANGE_ATR'].max()
            max_threshold = config['match_4h']['max_tr_range_atr']
            print(f"   TR_RANGE_ATR: {max_tr_atr_4h:.3f}")
            
            if max_tr_atr_4h <= max_threshold:
                print(f"   ✅ 4h volatility criteria met: {max_tr_atr_4h:.3f} ≤ {max_threshold}")
            else:
                print(f"   ❌ 4h volatility criteria failed: {max_tr_atr_4h:.3f} > {max_threshold}")
    
    print()
    
    # Analyze 1d confirmation
    print("🕐 1D CONFIRMATION ANALYSIS:")
    print("-" * 30)
    
    if len(dexe_1d) < 5:  # Assuming minimum bars needed
        print(f"❌ Insufficient 1d data: {len(dexe_1d)} bars")
    else:
        print(f"✅ Sufficient 1d data: {len(dexe_1d)} bars")
        
        # Check SMA150_SLOPE_BPS for 1d
        if 'SMA150_SLOPE_BPS' in dexe_1d.columns:
            min_slope_1d = dexe_1d['SMA150_SLOPE_BPS'].min()
            min_threshold = config['confirm_1d']['min_sma150_slope_pct']
            print(f"   SMA150_SLOPE_BPS: {min_slope_1d:.2f}")
            
            if min_slope_1d >= min_threshold:
                print(f"   ✅ 1d slope criteria met: {min_slope_1d:.2f} ≥ {min_threshold}")
            else:
                print(f"   ❌ 1d slope criteria failed: {min_slope_1d:.2f} < {min_threshold}")
    
    print()
    
    # Run the actual pipeline
    print("🔄 RUNNING P004 PIPELINE:")
    print("-" * 30)
    
    symbol_data = {
        '1h': dexe_1h,
        '4h': dexe_4h,
        '1d': dexe_1d
    }
    
    try:
        result = pipeline(symbol_data, config)
        print(f"Pipeline result: {result}")
        
        if result:
            print("✅ DEXEUSDT PASSED the P004 coil criteria!")
        else:
            print("❌ DEXEUSDT FAILED the P004 coil criteria")
            
    except Exception as e:
        print(f"❌ Pipeline error: {e}")
    
    print()
    print("📊 PRICE ACTION SUMMARY:")
    print("-" * 30)
    
    # Show price action
    print("1h timeframe (last 5 bars):")
    if not dexe_1h.empty:
        last_5 = dexe_1h.tail(5)[['ts', 'open', 'high', 'low', 'close', 'volume']]
        print(last_5.to_string(index=False))
    
    print()
    print("4h timeframe (all bars):")
    if not dexe_4h.empty:
        print(dexe_4h[['ts', 'open', 'high', 'low', 'close', 'volume']].to_string(index=False))
    
    print()
    print("1d timeframe (all bars):")
    if not dexe_1d.empty:
        print(dexe_1d[['ts', 'open', 'high', 'low', 'close', 'volume']].to_string(index=False))

if __name__ == "__main__":
    analyze_dexeusdt_coil()
