"""
TTR (Trained Trend Radar) Scanner
Version: 1.0.0
Author: A-Team (Aziz + Sonny)

🔍 Description:
Analyzes EMA stacking patterns across multiple timeframes with RSI confirmation
and pullback detection to identify optimal entry points in trending markets.

✨ Features:
- EMA stack analysis (5, 13, 21, 50, 200) across 4h and 1d timeframes
- RSI 14 confirmation for oversold/overbought conditions
- Recent pullback detection for optimal entry timing
- Trend strength scoring (0-1 scale)
- Buy/Sell signal generation
- YAML configuration for easy parameter adjustment
"""

import pandas as pd
import numpy as np
import yaml
from pathlib import Path
from datetime import datetime
import sys
import os

# Add src directory to path for indicators import
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from indicators import ema, rsi, detect_pullback, trend_strength_score, detect_ema_stack, compute_mtfa_score, classify_mtfa_strength, apply_mtfa_multiplier

# ========== CONFIGURATION LOADING ==========
def load_config(config_path: str = "ttr_config.yaml"):
    """Load TTR configuration from YAML file."""
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        return config
    except FileNotFoundError:
        print(f"❌ Configuration file not found: {config_path}")
        return None
    except yaml.YAMLError as e:
        print(f"❌ Error parsing YAML configuration: {e}")
        return None

# ========== DATA LOADING ==========
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

# ========== TTR ANALYSIS ==========
def analyze_symbol_ttr(df_symbol: pd.DataFrame, config: dict):
    """Analyze TTR for a single symbol."""
    if len(df_symbol) < max(config['emas']):
        return None
    
    # Calculate EMAs
    ema_values = {}
    for ema_period in config['emas']:
        df_symbol[f'ema_{ema_period}'] = ema(df_symbol['close'], ema_period)
        ema_values[f'EMA{ema_period}'] = df_symbol[f'ema_{ema_period}'].iloc[-1]
    
    # Calculate RSI
    df_symbol['rsi'] = rsi(df_symbol['close'], config['rsi_period'])
    current_rsi = df_symbol['rsi'].iloc[-1]
    
    # Detect EMA stack
    stack_status, broken_level, trend_direction = detect_ema_stack(ema_values)
    
    # Calculate trend strength
    trend_strength = trend_strength_score(ema_values)
    
    # Detect pullback
    pullback_pct, has_pullback = detect_pullback(
        df_symbol['close'], 
        ema_values, 
        config['pullback_lookback']
    )
    
    # Generate signals
    buy_signal = False
    sell_signal = False
    signal_strength = 0.0
    
    if config.get('enable_signals', True):
        # Buy signal: Bullish trend + RSI oversold + Recent pullback
        if (trend_direction == 'Bullish' and 
            current_rsi < config['rsi_oversold'] and 
            has_pullback and
            trend_strength >= config['min_trend_strength']):
            buy_signal = True
            signal_strength = trend_strength * (1 - current_rsi/100)
        
        # Sell signal: Bearish trend + RSI overbought + Recent pullback
        elif (trend_direction == 'Bearish' and 
              current_rsi > config['rsi_overbought'] and 
              has_pullback and
              trend_strength >= config['min_trend_strength']):
            sell_signal = True
            signal_strength = trend_strength * (current_rsi/100)
    
    # Filter by signal strength
    if signal_strength < config.get('min_signal_strength', 0.7):
        buy_signal = False
        sell_signal = False
    
    return {
        'symbol': df_symbol['symbol'].iloc[0],
        'timeframe': df_symbol.get('timeframe', 'unknown').iloc[0] if 'timeframe' in df_symbol.columns else 'unknown',
        'close': df_symbol['close'].iloc[-1],
        'stack_status': stack_status,
        'broken_level': broken_level if broken_level else '-',
        'trend_direction': trend_direction,
        'trend_strength': trend_strength,
        'rsi': current_rsi,
        'pullback_pct': pullback_pct * 100,  # Convert to percentage
        'has_pullback': has_pullback,
        'buy_signal': buy_signal,
        'sell_signal': sell_signal,
        'signal_strength': signal_strength,
        **ema_values
    }

# ========== MAIN TTR SCANNER ==========
def run_ttr_scanner(config_path: str = "ttr_config.yaml"):
    """Run the TTR scanner with given configuration."""
    print("🚀 TTR (Trained Trend Radar) Scanner Starting...")
    print("=" * 50)
    
    # Load configuration
    config = load_config(config_path)
    if not config:
        return
    
    print(f"📊 Configuration loaded: {config_path}")
    print(f"⏰ Timeframes: {config['timeframes']}")
    print(f"📈 EMAs: {config['emas']}")
    print(f"🎯 RSI Period: {config['rsi_period']}")
    print()
    
    all_results = []
    
    # Analyze each timeframe
    for timeframe in config['timeframes']:
        print(f"📊 Analyzing timeframe: {timeframe}")
        
        # Load data
        df = load_ohlcv_data(timeframe)
        if df is None:
            continue
        
        # Add timeframe column
        df['timeframe'] = timeframe
        
        # Filter symbols if specified
        if config.get('include_symbols'):
            df = df[df['symbol'].isin(config['include_symbols'])]
        elif config.get('exclude_symbols'):
            df = df[~df['symbol'].isin(config['exclude_symbols'])]
        
        # Filter by price range
        df = df[(df['close'] >= config.get('min_price', 0.001)) & 
                (df['close'] <= config.get('max_price', 1000000))]
        
        symbols_analyzed = 0
        signals_found = 0
        
        # Analyze each symbol
        for symbol in df['symbol'].unique():
            df_symbol = df[df['symbol'] == symbol].sort_values('ts')
            
            result = analyze_symbol_ttr(df_symbol, config)
            if result:
                all_results.append(result)
                symbols_analyzed += 1
                
                if result['buy_signal'] or result['sell_signal']:
                    signals_found += 1
        
        print(f"   ✅ Analyzed: {symbols_analyzed} symbols")
        print(f"   🎯 Signals found: {signals_found}")
        print()
    
    # Create output DataFrame
    if not all_results:
        print("❌ No results to output")
        return
    
    df_out = pd.DataFrame(all_results)
    
    # Calculate MTFA scores for all symbols
    mtfa_results = {}
    for symbol in df_out['symbol'].unique():
        symbol_data = {}
        for timeframe in config['timeframes']:
            tf_data = df_out[(df_out['symbol'] == symbol) & (df_out['timeframe'] == timeframe)]
            if not tf_data.empty:
                # Create a mock DataFrame with EMA columns for MTFA calculation
                mock_df = pd.DataFrame({
                    'ema5': [tf_data.iloc[0].get('EMA5', 0)],
                    'ema13': [tf_data.iloc[0].get('EMA13', 0)],
                    'ema21': [tf_data.iloc[0].get('EMA21', 0)],
                    'ema50': [tf_data.iloc[0].get('EMA50', 0)],
                    'ema200': [tf_data.iloc[0].get('EMA200', 0)]
                })
                symbol_data[timeframe] = mock_df
        
        if symbol_data:
            mtfa_score, mtfa_direction, mtfa_breakdown = compute_mtfa_score(symbol_data, config)
            mtfa_results[symbol] = {
                'mtfa_score': mtfa_score,
                'mtfa_direction': mtfa_direction,
                'mtfa_strength': classify_mtfa_strength(mtfa_score, config.get('mtfa', {}).get('thresholds', {})),
                'breakdown': mtfa_breakdown
            }
    
    # Add MTFA data to results
    df_out['mtfa_score'] = df_out['symbol'].map(lambda x: mtfa_results.get(x, {}).get('mtfa_score', 0.0))
    df_out['mtfa_direction'] = df_out['symbol'].map(lambda x: mtfa_results.get(x, {}).get('mtfa_direction', 'neutral'))
    df_out['mtfa_strength'] = df_out['symbol'].map(lambda x: mtfa_results.get(x, {}).get('mtfa_strength', 'none'))
    
    # Add per-timeframe MTFA scores
    df_out['mtfa_1h_score'] = df_out['symbol'].map(lambda x: mtfa_results.get(x, {}).get('breakdown', {}).get('1h', {}).get('raw_score', 0.0))
    df_out['mtfa_4h_score'] = df_out['symbol'].map(lambda x: mtfa_results.get(x, {}).get('breakdown', {}).get('4h', {}).get('raw_score', 0.0))
    df_out['mtfa_1d_score'] = df_out['symbol'].map(lambda x: mtfa_results.get(x, {}).get('breakdown', {}).get('1d', {}).get('raw_score', 0.0))
    
    # Add MTFA weights
    mtfa_weights = config.get('mtfa', {}).get('weights', {})
    df_out['mtfa_1h_weight'] = mtfa_weights.get('1h', 0.25)
    df_out['mtfa_4h_weight'] = mtfa_weights.get('4h', 0.35)
    df_out['mtfa_1d_weight'] = mtfa_weights.get('1d', 0.40)
    
    # Apply direction-aware MTFA multiplier to signal strength
    df_out['enhanced_signal_strength'] = df_out.apply(
        lambda row: apply_mtfa_multiplier(
            row['signal_strength'], 
            row['mtfa_score'], 
            row['mtfa_direction'], 
            config
        ), axis=1
    )
    
    # Rename base signal strength for clarity
    df_out['base_signal_strength'] = df_out['signal_strength']
    
    # Sort by MTFA score (primary), then enhanced signal strength (secondary), then symbol (tertiary)
    df_out = df_out.sort_values(['mtfa_score', 'enhanced_signal_strength', 'symbol'], ascending=[False, False, True])
    
    # Generate output filename
    timestamp = datetime.now().strftime(config.get('timestamp_format', "%Y%m%d_%H%M"))
    output_file = f"out/ttr_report_{timestamp}.csv"
    
    # Ensure output directory exists
    Path("out").mkdir(exist_ok=True)
    
    # Reorder columns to match Amy's approved format
    column_order = [
        'symbol', 'timeframe', 'close',
        'EMA5', 'EMA13', 'EMA21', 'EMA50', 'EMA200',
        'trend_direction',
        'base_signal_strength', 'mtfa_score', 'mtfa_direction', 'mtfa_strength',
        'mtfa_1h_score', 'mtfa_4h_score', 'mtfa_1d_score',
        'mtfa_1h_weight', 'mtfa_4h_weight', 'mtfa_1d_weight',
        'enhanced_signal_strength',
        'stack_status', 'broken_level', 'trend_strength', 'rsi', 
        'pullback_pct', 'has_pullback', 'buy_signal', 'sell_signal'
    ]
    
    # Only include columns that exist in the DataFrame
    available_columns = [col for col in column_order if col in df_out.columns]
    df_out_ordered = df_out[available_columns]
    
    # Save results with ordered columns
    df_out_ordered.to_csv(output_file, index=False)
    
    # Print summary
    print("📊 TTR SCAN RESULTS SUMMARY")
    print("=" * 30)
    print(f"Total symbols analyzed: {len(df_out)}")
    print(f"Buy signals: {df_out['buy_signal'].sum()}")
    print(f"Sell signals: {df_out['sell_signal'].sum()}")
    print(f"Bullish trends: {(df_out['trend_direction'] == 'Bullish').sum()}")
    print(f"Bearish trends: {(df_out['trend_direction'] == 'Bearish').sum()}")
    print(f"Mixed/Choppy: {(df_out['trend_direction'] == 'Mixed').sum()}")
    print()
    
    # Enhanced per-timeframe breakdown with detailed analysis
    print("📊 DETAILED RESULTS BY TIMEFRAME:")
    print("=" * 50)
    
    # Print MTFA summary
    print(f"\n🧠 MTFA (Multi-Timeframe Trend Agreement) Analysis:")
    print(f"   📊 Symbols with MTFA data: {len(mtfa_results)}")
    mtfa_threshold = config.get('mtfa', {}).get('min_threshold', 0.4)
    print(f"   🎯 MTFA threshold: {mtfa_threshold}")
    print(f"   ✅ Symbols passing MTFA: {(df_out['mtfa_score'] >= mtfa_threshold).sum()}")
    print(f"   📈 Average MTFA score: {df_out['mtfa_score'].mean():.3f}")
    
    # MTFA strength distribution
    strength_counts = df_out['mtfa_strength'].value_counts()
    print(f"   🏆 MTFA Strength Distribution:")
    for strength, count in strength_counts.items():
        print(f"      {strength}: {count} symbols")
    
    for timeframe in config['timeframes']:
        tf_data = df_out[df_out['timeframe'] == timeframe]
        if len(tf_data) > 0:
            buy_signals = tf_data['buy_signal'].sum()
            sell_signals = tf_data['sell_signal'].sum()
            bullish_trends = (tf_data['trend_direction'] == 'Bullish').sum()
            bearish_trends = (tf_data['trend_direction'] == 'Bearish').sum()
            mixed_trends = (tf_data['trend_direction'] == 'Mixed').sum()
            
            # Calculate average metrics
            avg_rsi = tf_data['rsi'].mean()
            avg_trend_strength = tf_data['trend_strength'].mean()
            avg_pullback = tf_data['pullback_pct'].mean()
            
            print(f"\n🕐 {timeframe.upper()} TIMEFRAME ANALYSIS:")
            print(f"   📊 Symbols Analyzed: {len(tf_data)}")
            print(f"   🎯 Buy Signals: {buy_signals}")
            print(f"   🎯 Sell Signals: {sell_signals}")
            print(f"   📈 Bullish Trends: {bullish_trends} ({bullish_trends/len(tf_data)*100:.1f}%)")
            print(f"   📉 Bearish Trends: {bearish_trends} ({bearish_trends/len(tf_data)*100:.1f}%)")
            print(f"   🔄 Mixed/Choppy: {mixed_trends} ({mixed_trends/len(tf_data)*100:.1f}%)")
            print(f"   📊 Average RSI: {avg_rsi:.1f}")
            print(f"   💪 Average Trend Strength: {avg_trend_strength:.2f}")
            print(f"   📉 Average Pullback: {avg_pullback:.1f}%")
            
            # Show top signals for this timeframe
            tf_signals = tf_data[(tf_data['buy_signal']) | (tf_data['sell_signal'])]
            if len(tf_signals) > 0:
                print(f"   🎯 Top {timeframe} Signals:")
                for _, row in tf_signals.head(5).iterrows():
                    signal_type = "BUY" if row['buy_signal'] else "SELL"
                    mtfa_indicator = f"MTFA:{row['mtfa_strength'][:3]}" if row['mtfa_score'] > 0 else "No MTFA"
                    print(f"      {signal_type:4} | {row['symbol']:12} | "
                          f"Strength: {row['enhanced_signal_strength']:.2f} | RSI: {row['rsi']:.1f} | "
                          f"Pullback: {row['pullback_pct']:.1f}% | {mtfa_indicator}")
            else:
                print(f"   🎯 No signals found for {timeframe}")
        else:
            print(f"\n🕐 {timeframe.upper()} TIMEFRAME: No data available")
    
    print(f"\n📁 Report saved to: {output_file}")
    
    # Show overall top signals
    signals_df = df_out[(df_out['buy_signal']) | (df_out['sell_signal'])]
    if len(signals_df) > 0:
        print()
        print("🎯 OVERALL TOP SIGNALS (All Timeframes) - MTFA Enhanced:")
        print("-" * 60)
        for _, row in signals_df.head(15).iterrows():
            signal_type = "BUY" if row['buy_signal'] else "SELL"
            mtfa_indicator = f"MTFA:{row['mtfa_strength'][:3]}" if row['mtfa_score'] > 0 else "No MTFA"
            print(f"{signal_type:4} | {row['symbol']:12} | {row['timeframe']:2} | "
                  f"Strength: {row['enhanced_signal_strength']:.2f} | RSI: {row['rsi']:.1f} | "
                  f"Pullback: {row['pullback_pct']:.1f}% | {mtfa_indicator}")
    
    print()
    print("✅ TTR Scanner completed successfully!")

# ========== MAIN EXECUTION ==========
if __name__ == "__main__":
    run_ttr_scanner()
