# MA Slopes Scanner - Documentation

## Overview

The **MA Slopes Scanner** is a powerful technical analysis tool that identifies cryptocurrency trading opportunities by analyzing moving average slopes across multiple timeframes. It ranks coins based on their momentum strength and generates comprehensive Excel reports with color-coded visualizations.

## 🎯 What It Does

- **Analyzes 3 timeframes**: 1h, 4h, and 1d
- **Calculates slopes** for 4 moving averages: EMA21, SMA40, SMA50, SMA150
- **Ranks coins** by overall momentum strength
- **Filters quality coins** (≥150 days of data to exclude new/pump-and-dump coins)
- **Generates Excel reports** with color-coded headers and trend analysis
- **Creates Binance import files** for easy portfolio integration

## 📊 How "Top Performers" Are Determined

### Strength Calculation
The system ranks coins using a **"strength" score** calculated as:
```
Total Strength = Sum of absolute values of all 12 slopes
(3 timeframes × 4 moving averages)
```

### Key Features
- **Multi-timeframe analysis**: Combines short-term (1h, 4h) and long-term (1d) momentum
- **Multi-MA analysis**: Uses different moving average periods for comprehensive coverage
- **Absolute values**: Captures both bullish AND bearish momentum (high volatility)
- **Quality filtering**: Only includes coins with ≥150 days of historical data

### Moving Averages Analyzed
- **EMA21**: 21-period Exponential Moving Average (fast trend)
- **EMA40**: 40-period Exponential Moving Average (mid-fast trend)
- **SMA50**: 50-period Simple Moving Average (mid-slow trend)
- **SMA150**: 150-period Simple Moving Average (slow trend)

## 🚀 Basic Usage

### Simple Run (Default Configuration)
```bash
python ma_slopes_scan.py slopes_benchmark.yaml
```

### With Custom Config File
```bash
python ma_slopes_scan.py my_config.yaml
```

## ⚙️ Command Line Arguments

### Required Arguments
- **`yaml`** (optional): Path to YAML configuration file
  - Default: `slopes_benchmark.yaml`
  - Example: `python ma_slopes_scan.py my_config.yaml`

### Timeframe Lookback Overrides
Override the default slope window for specific timeframes:

- **`--lb-1h N`**: Set lookback bars for 1h slopes
  - Example: `--lb-1h 50` (analyze last 50 hours for 1h slopes)
- **`--lb-4h N`**: Set lookback bars for 4h slopes  
  - Example: `--lb-4h 25` (analyze last 100 hours for 4h slopes)
- **`--lb-1d N`**: Set lookback bars for 1d slopes
  - Example: `--lb-1d 30` (analyze last 30 days for 1d slopes)

### Symbol Filtering
Limit analysis to specific symbols:

- **`--symbols "SYMBOL1,SYMBOL2"`**: Comma-separated symbol list
  - Example: `--symbols "BTC/USDT,ETH/USDT,ADA/USDT"`
- **`--symbols-file path/to/file`**: Load symbols from file
  - Supports `.txt` (one per line) or `.csv` (with 'symbol' column)
  - Example: `--symbols-file my_watchlist.txt`

### Slope Filtering
Filter results by slope strength:

- **`--min-slope N`**: Minimum slope percentage to include
  - Example: `--min-slope 2.0` (only show coins with ≥2% slope)
- **`--max-slope N`**: Maximum slope percentage to include
  - Example: `--max-slope 10.0` (only show coins with ≤10% slope)
- **`--top-n N`**: Show only top N symbols by strength
  - Example: `--top-n 50` (show only top 50 strongest coins)

## 📝 Command Examples

### Basic Examples
```bash
# Default run with benchmark config
python ma_slopes_scan.py slopes_benchmark.yaml

# Custom config file
python ma_slopes_scan.py my_custom_config.yaml
```

### Symbol Filtering Examples
```bash
# Analyze only specific coins
python ma_slopes_scan.py slopes_benchmark.yaml --symbols "BTC/USDT,ETH/USDT,ADA/USDT"

# Load symbols from file
python ma_slopes_scan.py slopes_benchmark.yaml --symbols-file watchlist.txt

# Mix both methods
python ma_slopes_scan.py slopes_benchmark.yaml --symbols "BTC/USDT" --symbols-file altcoins.txt
```

### Timeframe Override Examples
```bash
# Use shorter lookback for more sensitive analysis
python ma_slopes_scan.py slopes_benchmark.yaml --lb-1h 50 --lb-4h 25 --lb-1d 30

# Use longer lookback for more stable signals
python ma_slopes_scan.py slopes_benchmark.yaml --lb-1h 200 --lb-4h 100 --lb-1d 150
```

### Slope Filtering Examples
```bash
# Only show coins with strong momentum (≥3%)
python ma_slopes_scan.py slopes_benchmark.yaml --min-slope 3.0

# Only show moderate momentum (1-5%)
python ma_slopes_scan.py slopes_benchmark.yaml --min-slope 1.0 --max-slope 5.0

# Show only top 30 strongest coins
python ma_slopes_scan.py slopes_benchmark.yaml --top-n 30

# Combine filters: top 20 coins with ≥2% slope
python ma_slopes_scan.py slopes_benchmark.yaml --min-slope 2.0 --top-n 20
```

### Complex Examples
```bash
# Analyze specific coins with custom timeframe settings and filtering
python ma_slopes_scan.py slopes_benchmark.yaml \
  --symbols "BTC/USDT,ETH/USDT" \
  --lb-1h 75 --lb-4h 40 --lb-1d 60 \
  --min-slope 1.5 --max-slope 8.0 \
  --top-n 15

# Load from file with custom settings
python ma_slopes_scan.py slopes_benchmark.yaml \
  --symbols-file my_portfolio.txt \
  --lb-1d 90 \
  --min-slope 2.5 \
  --top-n 25
```

## 📁 Output Files

### Excel File (`out/slopes_summary_YYYY-MM-DD___HH-MM.xlsx`)
Contains 4 sheets:

1. **Main_Data**: Complete analysis with color-coded headers
   - Headers color-coded by timeframe (1h=orange, 4h=purple, 1d=blue)
   - Slope values as percentages
   - Direction indicators (UP/DOWN/FLAT) with color coding

2. **Top_Performers**: Top 20 coins with ≥150 days data
   - Filtered for established coins only
   - Includes 1d_data_count column
   - Formatted for easy analysis

3. **Trend_Summary**: Statistical overview
   - Per-timeframe trend counts
   - Overall market sentiment
   - Percentage breakdowns

4. **Configuration**: Settings used
   - All parameters and filters applied
   - Per-timeframe lookback values
   - Symbol filtering details

### Binance Import File (`out/slopes_summary_YYYY-MM-DD___HH-MM_top_performers.txt`)
- Contains top performers in `binance:symbolname` format
- Ready for direct import into Binance
- Only includes coins with ≥150 days of data
- Example format:
  ```
  binance:ogusdt
  binance:penguusdt
  binance:tutusdt
  ...
  ```

## 🔧 Configuration File (YAML)

### Basic Structure
```yaml
control:
  benchmark: true              # Compute slopes for all symbols
  deadzone_pct: 0.25           # Flat threshold (0.25%)

universe:
  regex: ".*"                  # Symbol pattern (.* = all)
  exclude_symbols:             # Symbols to exclude
    - USDCUSDT
    - BUSDUSDT

# Moving Average Periods
ema_fast: 21
sma_mid_fast: 40
sma_mid_slow: 50
sma_slow: 150

# Feature Windows
slope_window: 100              # Default lookback period
```

### Key Parameters
- **`benchmark`**: If true, processes all symbols regardless of filters
- **`deadzone_pct`**: Threshold below which slopes are considered "FLAT"
- **`regex`**: Pattern to match symbols (use ".*" for all)
- **`exclude_symbols`**: List of symbols to skip (typically stablecoins)
- **`slope_window`**: Default lookback period (can be overridden via CLI)

## 🎨 Visual Features

### Color Coding
- **Headers**: Timeframe-based colors (1h=orange, 4h=purple, 1d=blue)
- **Directions**: UP=green, DOWN=red, FLAT=gray
- **Excel formatting**: Percentage formatting for slopes

### Quality Filtering
- **Minimum data requirement**: ≥150 days of 1d data
- **Excludes**: New listings and pump-and-dump coins
- **Focuses on**: Established, liquid cryptocurrencies

## 🚨 Troubleshooting

### Common Issues
1. **"Parquet not found"**: Ensure OHLCV data files exist in `ohlcv_parquet/`
2. **"No symbols found"**: Check regex pattern and exclude lists
3. **"Warning: 1d data count not available"**: Should be fixed in current version

### Performance Tips
- Use `--symbols` or `--symbols-file` to limit analysis scope
- Adjust `--lb-*` parameters for faster processing
- Use `--top-n` to limit output size

## 📈 Use Cases

### Trading Strategies
- **Momentum trading**: Find coins with strong directional movement
- **Volatility trading**: Identify high-movement opportunities
- **Portfolio screening**: Filter watchlist by technical criteria
- **Market analysis**: Understand overall market momentum

### Research Applications
- **Market structure analysis**: Study slope patterns across timeframes
- **MA effectiveness**: Compare different moving average periods
- **Market sentiment**: Analyze bullish vs bearish momentum distribution

---

*Generated for MA Slopes Scanner - A comprehensive technical analysis tool for cryptocurrency markets.*
