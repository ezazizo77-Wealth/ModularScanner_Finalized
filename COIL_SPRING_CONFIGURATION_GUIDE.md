# Coil Spring Scanner Configuration Guide

## Overview

The Coil Spring Scanner is a modular trading pattern detection system that identifies "coil spring" formations across multiple timeframes. This guide covers the complete configuration spectrum from ultra-selective to ultra-permissive criteria.

## Configuration Spectrum

### 🎯 Conservative (Tight) - `coil_spring_conservative.yaml`
**Purpose**: High-conviction trades with very selective criteria

**Key Settings**:
- **1h Max Width**: 2.0% (very tight bundle)
- **1h Max TR/ATR**: 1.0 (low volatility only)
- **1h Min Bars**: 12 (high persistence)
- **1h Min Slope**: 0.0% (flat or up bias)
- **4h Max Width**: 6.0% (4h coil tightness)
- **4h Min Bars**: 6 (4h persistence)
- **1d Min Slope**: 0.1% (strong daily uptrend)
- **Stages**: All 3 enabled (1h + 4h + 1d)

**Use Case**: Traditional markets, low risk tolerance, high-conviction trades

---

### ⚡ Aggressive (Loose) - `coil_spring_aggressive.yaml`
**Purpose**: More signals for research and screening

**Key Settings**:
- **1h Max Width**: 5.0% (loose bundle)
- **1h Max TR/ATR**: 1.5 (allow higher volatility)
- **1h Min Bars**: 5 (short persistence)
- **1h Min Slope**: -0.2% (allow slight down bias)
- **4h Max Width**: 12.0% (very loose 4h coil)
- **4h Min Bars**: 3 (very short persistence)
- **4h Mode**: "either" (either condition)
- **Stages**: 2 enabled (1h + 4h, skips 1d)

**Use Case**: Research and screening, moderate risk tolerance

---

### 🔓 Loose (DEXEUSDT Optimized) - `coil_spring_loose.yaml`
**Purpose**: Volatile crypto assets with higher risk tolerance

**Key Settings**:
- **1h Max Width**: 6.0% (loose bundle)
- **1h Max TR/ATR**: 3.0 (high volatility allowed)
- **1h Min Bars**: 1 (minimal persistence)
- **1h Min Slope**: -5.0% (allow significant down bias)
- **4h Max TR/ATR**: 2.5 (high volatility allowed)
- **1d Min Slope**: -8.0% (very permissive daily trend)
- **Stages**: All 3 enabled (1h + 4h + 1d)

**Use Case**: Volatile crypto assets, higher risk tolerance, reverse-engineered for DEXEUSDT

---

### 🚀 Very Loose (Max Signals) - `coil_spring_very_loose.yaml`
**Purpose**: Maximum signal detection for research only

**Key Settings**:
- **1h Max Width**: 10.0% (very loose bundle)
- **1h Max TR/ATR**: 5.0 (very high volatility allowed)
- **1h Min Bars**: 1 (minimal persistence)
- **1h Min Slope**: -10.0% (allow major down bias)
- **4h Max TR/ATR**: 4.0 (very high volatility allowed)
- **4h Mode**: "either" (either condition)
- **Stages**: 2 enabled (1h + 4h, skips 1d)

**Use Case**: Maximum signal detection, research purposes only, extreme market conditions

---

## Usage Examples

### Basic Usage
```bash
python3 coil_spring.py --cfg [config_file] --symbols [symbol_list]
```

### Specific Examples
```bash
# Conservative - High Quality Signals
python3 coil_spring.py --cfg coil_spring_conservative.yaml --symbols BTCUSDT ETHUSDT

# Aggressive - More Signals
python3 coil_spring.py --cfg coil_spring_aggressive.yaml --symbols DEXEUSDT

# Loose - Volatile Assets
python3 coil_spring.py --cfg coil_spring_loose.yaml --symbols DEXEUSDT

# Very Loose - Research Only
python3 coil_spring.py --cfg coil_spring_very_loose.yaml --symbols DEXEUSDT
```

### Advanced Usage
```bash
# Verbose output
python3 coil_spring.py --cfg coil_spring_loose.yaml --symbols DEXEUSDT --verbose

# Custom output directory
python3 coil_spring.py --cfg coil_spring_conservative.yaml --symbols BTCUSDT --output custom_results
```

---

## Configuration Parameters Explained

### 1H Coil Stage Parameters
- **`max_fast3_width_pct`**: Maximum width between EMA21, EMA40, and SMA50 (lower = tighter coil)
- **`max_tr_range_atr`**: Maximum True Range divided by ATR (lower = less volatile)
- **`min_bars_in_coil`**: Minimum consecutive bars meeting coil criteria (higher = more persistent)
- **`min_ma21_slope_pct`**: Minimum EMA21 slope percentage (higher = more bullish bias)

### 4H Matching Stage Parameters
- **`max_fast3_width_pct`**: 4h timeframe coil width tolerance
- **`min_bars_in_coil`**: 4h timeframe persistence requirement
- **`max_tr_range_atr`**: 4h timeframe volatility tolerance
- **`mode`**: "and" (both conditions) vs "either" (either condition)

### 1D Confirmation Stage Parameters
- **`min_sma150_slope_pct`**: Minimum SMA150 slope for trend confirmation
- **`tolerance_pct`**: Allowable deviation from perfect trend

---

## Output Files

Each scan generates three output files:

1. **`out/coil_spring_[config]_[timestamp].csv`**
   - Detailed results with all technical indicators
   - Columns: symbol, timeframe, price data, technical indicators, pass/fail status

2. **`out/coil_spring_[config]_[timestamp]_binance_list.csv`**
   - Simple symbol list for easy import
   - Format: One symbol per line

3. **`out/coil_spring_[config]_[timestamp].txt`**
   - Human-readable summary report
   - Includes pass/fail counts and key statistics

---

## Selection Guide

### When to Use Conservative
- ✅ Traditional markets (stocks, forex)
- ✅ Low risk tolerance
- ✅ High-conviction trades only
- ✅ Stable market conditions

### When to Use Aggressive
- ✅ Research and screening
- ✅ Moderate risk tolerance
- ✅ Need more signals for analysis
- ✅ Mixed market conditions

### When to Use Loose
- ✅ Volatile crypto assets
- ✅ Higher risk tolerance
- ✅ Assets like DEXEUSDT, altcoins
- ✅ Volatile market conditions

### When to Use Very Loose
- ✅ Maximum signal detection
- ✅ Research purposes only
- ✅ Extreme market conditions
- ✅ Pattern discovery and analysis

---

## Troubleshooting

### Common Issues

1. **No symbols found**
   - Check if symbol exists in parquet files
   - Verify date range has sufficient data
   - Ensure symbol is not in exclusion list

2. **Insufficient data for SMA150**
   - Extend historical data range
   - Use configurations that skip 1d confirmation
   - Check data quality and completeness

3. **Too many/few signals**
   - Adjust configuration parameters
   - Switch to more/less permissive config
   - Check market conditions match criteria

### Data Requirements

- **1h data**: Minimum 150 hours for SMA150 calculation
- **4h data**: Minimum 150 periods for SMA150 calculation  
- **1d data**: Minimum 150 days for SMA150 calculation

---

## Best Practices

1. **Start Conservative**: Begin with tight criteria and loosen as needed
2. **Validate Results**: Cross-check signals with manual analysis
3. **Monitor Performance**: Track success rates across different configurations
4. **Adjust for Market**: Use appropriate config for current market conditions
5. **Regular Updates**: Refresh data regularly for accurate analysis

---

## Configuration Customization

### Creating Custom Configs

1. Copy an existing configuration file
2. Modify parameters based on requirements
3. Test with known examples
4. Validate results before production use

### Parameter Tuning Guidelines

- **Width**: Start with 2-3% for tight, 5-6% for loose
- **Volatility**: Start with 1.0-1.5 for tight, 2.0-3.0 for loose
- **Persistence**: Start with 5-12 bars for tight, 1-3 bars for loose
- **Slope**: Start with 0% for tight, -5% to -10% for loose

---

## Version History

- **v1.0**: Initial implementation with basic criteria
- **v2.0**: Added multi-timeframe analysis
- **v3.0**: Introduced configuration spectrum
- **v4.0**: DEXEUSDT optimization and loose criteria
- **v5.0**: Very loose configuration for maximum signal detection

---

## Support

For questions or issues:
1. Check this guide first
2. Review configuration examples
3. Test with known working examples
4. Verify data quality and completeness

---

*Last Updated: September 24, 2025*
*Version: 5.0*
