#!/usr/bin/env python3
"""
DEXEUSDT Loose Config Analysis with Extended Data
"""

import pandas as pd
import sys
import os
import yaml

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from indicators import compute_features
from coil_spring import pipeline

def analyze_dexeusdt_with_loose_config():
    """Analyze DEXEUSDT with loose config and extended data"""
    
    print('🔍 DEXEUSDT Loose Config Analysis - Extended Data')
    print('=' * 60)
    
    # Load loose configuration
    with open('coil_spring_loose.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    print('📊 Loose Configuration:')
    print(f'   1h max width: {config["coil_1h"]["max_fast3_width_pct"]}%')
    print(f'   1h max TR/ATR: {config["coil_1h"]["max_tr_range_atr"]}')
    print(f'   1h min bars: {config["coil_1h"]["min_bars_in_coil"]}')
    print(f'   4h max TR/ATR: {config["match_4h"]["max_tr_range_atr"]}')
    print(f'   1d min slope: {config["confirm_1d"]["min_sma150_slope_pct"]}%')
    print()
    
    # Load extended data
    print('📈 Loading extended DEXEUSDT data...')
    
    # Load 1h data (extended)
    df_1h = pd.read_parquet('ohlcv_parquet/ohlcv_1h.parquet')
    dexe_1h = df_1h[(df_1h['symbol'] == 'DEXEUSDT') & 
                    (df_1h['ts'] >= '2024-09-13') & 
                    (df_1h['ts'] <= '2024-09-17')].copy()
    
    # Load 4h data (extended)
    df_4h = pd.read_parquet('ohlcv_parquet/ohlcv_4h.parquet')
    dexe_4h = df_4h[(df_4h['symbol'] == 'DEXEUSDT') & 
                    (df_4h['ts'] >= '2024-09-13') & 
                    (df_4h['ts'] <= '2024-09-17')].copy()
    
    # Load 1d data (extended)
    df_1d = pd.read_parquet('ohlcv_parquet/ohlcv_1d.parquet')
    dexe_1d = df_1d[(df_1d['symbol'] == 'DEXEUSDT') & 
                    (df_1d['ts'] >= '2024-09-13') & 
                    (df_1d['ts'] <= '2024-09-17')].copy()
    
    print(f'✅ 1h data: {len(dexe_1h)} bars')
    print(f'✅ 4h data: {len(dexe_4h)} bars') 
    print(f'✅ 1d data: {len(dexe_1d)} bars')
    print()
    
    if dexe_1h.empty or dexe_4h.empty or dexe_1d.empty:
        print('❌ Missing data for analysis')
        return
    
    # Sort data by timestamp
    dexe_1h = dexe_1h.sort_values('ts').reset_index(drop=True)
    dexe_4h = dexe_4h.sort_values('ts').reset_index(drop=True)
    dexe_1d = dexe_1d.sort_values('ts').reset_index(drop=True)
    
    # Compute features for each timeframe
    print('🧮 Computing technical indicators...')
    
    # Add timeframe column
    dexe_1h['timeframe'] = '1h'
    dexe_4h['timeframe'] = '4h'
    dexe_1d['timeframe'] = '1d'
    
    # Compute features
    dexe_1h = compute_features(dexe_1h, config)
    dexe_4h = compute_features(dexe_4h, config)
    dexe_1d = compute_features(dexe_1d, config)
    
    print('✅ Technical indicators computed')
    print()
    
    # Analyze 1h coil formation with loose criteria
    print('🕐 1H COIL ANALYSIS (LOOSE CRITERIA):')
    print('-' * 40)
    
    # Check if we have enough data
    min_bars = config['coil_1h']['min_bars_in_coil']
    if len(dexe_1h) < min_bars:
        print(f'❌ Insufficient 1h data: {len(dexe_1h)} bars < {min_bars} required')
    else:
        print(f'✅ Sufficient 1h data: {len(dexe_1h)} bars ≥ {min_bars} required')
        
        # Check FAST3_WIDTH_PCT
        if 'FAST3_WIDTH_PCT' in dexe_1h.columns:
            max_width = dexe_1h['FAST3_WIDTH_PCT'].max()
            max_threshold = config['coil_1h']['max_fast3_width_pct']
            print(f'   FAST3_WIDTH_PCT: {max_width:.2f}% (threshold: {max_threshold}%)')
            
            if max_width <= max_threshold:
                print(f'   ✅ Width criteria met: {max_width:.2f}% ≤ {max_threshold}%')
            else:
                print(f'   ❌ Width criteria failed: {max_width:.2f}% > {max_threshold}%')
        
        # Check TR_RANGE_ATR
        if 'TR_RANGE_ATR' in dexe_1h.columns:
            max_tr_atr = dexe_1h['TR_RANGE_ATR'].max()
            max_threshold = config['coil_1h']['max_tr_range_atr']
            print(f'   TR_RANGE_ATR: {max_tr_atr:.3f} (threshold: {max_threshold})')
            
            if max_tr_atr <= max_threshold:
                print(f'   ✅ Volatility criteria met: {max_tr_atr:.3f} ≤ {max_threshold}')
            else:
                print(f'   ❌ Volatility criteria failed: {max_tr_atr:.3f} > {max_threshold}')
        
        # Check SMA150_SLOPE_BPS
        if 'SMA150_SLOPE_BPS' in dexe_1h.columns:
            min_slope = dexe_1h['SMA150_SLOPE_BPS'].min()
            min_threshold = config['coil_1h']['require_sma150_slope_bps_min']
            print(f'   SMA150_SLOPE_BPS: {min_slope:.2f} (threshold: {min_threshold})')
            
            if min_slope >= min_threshold:
                print(f'   ✅ Slope criteria met: {min_slope:.2f} ≥ {min_threshold}')
            else:
                print(f'   ❌ Slope criteria failed: {min_slope:.2f} < {min_threshold}')
    
    print()
    
    # Analyze 4h matching with loose criteria
    print('🕐 4H MATCHING ANALYSIS (LOOSE CRITERIA):')
    print('-' * 40)
    
    if len(dexe_4h) < 5:
        print(f'❌ Insufficient 4h data: {len(dexe_4h)} bars')
    else:
        print(f'✅ Sufficient 4h data: {len(dexe_4h)} bars')
        
        # Check TR_RANGE_ATR for 4h
        if 'TR_RANGE_ATR' in dexe_4h.columns:
            max_tr_atr_4h = dexe_4h['TR_RANGE_ATR'].max()
            max_threshold = config['match_4h']['max_tr_range_atr']
            print(f'   TR_RANGE_ATR: {max_tr_atr_4h:.3f} (threshold: {max_threshold})')
            
            if max_tr_atr_4h <= max_threshold:
                print(f'   ✅ 4h volatility criteria met: {max_tr_atr_4h:.3f} ≤ {max_threshold}')
            else:
                print(f'   ❌ 4h volatility criteria failed: {max_tr_atr_4h:.3f} > {max_threshold}')
    
    print()
    
    # Analyze 1d confirmation with loose criteria
    print('🕐 1D CONFIRMATION ANALYSIS (LOOSE CRITERIA):')
    print('-' * 40)
    
    if len(dexe_1d) < 5:
        print(f'❌ Insufficient 1d data: {len(dexe_1d)} bars')
    else:
        print(f'✅ Sufficient 1d data: {len(dexe_1d)} bars')
        
        # Check SMA150_SLOPE_BPS for 1d
        if 'SMA150_SLOPE_BPS' in dexe_1d.columns:
            min_slope_1d = dexe_1d['SMA150_SLOPE_BPS'].min()
            min_threshold = config['confirm_1d']['min_sma150_slope_pct']
            print(f'   SMA150_SLOPE_BPS: {min_slope_1d:.2f} (threshold: {min_threshold})')
            
            if min_slope_1d >= min_threshold:
                print(f'   ✅ 1d slope criteria met: {min_slope_1d:.2f} ≥ {min_threshold}')
            else:
                print(f'   ❌ 1d slope criteria failed: {min_slope_1d:.2f} < {min_threshold}')
    
    print()
    
    # Run the actual pipeline
    print('🔄 RUNNING LOOSE P004 PIPELINE:')
    print('-' * 40)
    
    symbol_data = {
        '1h': dexe_1h,
        '4h': dexe_4h,
        '1d': dexe_1d
    }
    
    try:
        result = pipeline(symbol_data, config)
        print(f'Pipeline result: {result}')
        
        if result:
            print('✅ DEXEUSDT PASSED the loose P004 coil criteria!')
        else:
            print('❌ DEXEUSDT FAILED the loose P004 coil criteria')
            
    except Exception as e:
        print(f'❌ Pipeline error: {e}')
    
    print()
    print('📊 SUMMARY:')
    print('-' * 40)
    print('Loose config allows:')
    print('  • Higher volatility (3.0 vs 1.2 TR/ATR)')
    print('  • Wider coils (6.0% vs 2.0% width)')
    print('  • Lower persistence (1 vs 12 bars)')
    print('  • Bearish slopes (-10% vs 0%)')

if __name__ == "__main__":
    analyze_dexeusdt_with_loose_config()
