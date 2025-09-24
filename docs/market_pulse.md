# Market Pulse System

## What it is
The Market Pulse System generates daily market overview reports with executive summaries, trend analysis, and top performer identification across multiple timeframes (1h, 4h, 1d).

## How to run
```bash
python3 market_pulse.py
```

Common flags:
- `--config`: Specify custom config file (default: market_pulse.yaml)
- `--symbols`: Limit to specific symbols (comma-separated)

## Config knobs
Key YAML options in `market_pulse.yaml`:
- `exec_summary.trend_deadzone_pct`: Threshold for flat trend classification (default: 0.25%)
- `exec_summary.top20_count`: Number of top performers to highlight (default: 20)
- `exec_summary.timeframes`: Timeframes to analyze (default: ["1h", "4h", "1d"])
- `universe.exclude_symbols`: Symbols to exclude from analysis

## Outputs
Generated files in `out/` directory:
- `market_pulse_YYYY-MM-DD.xlsx`: Excel report with Executive Summary worksheet
- `market_pulse_top20_symbols.txt`: TradingView import format (symbols only)
- `market_pulse_top20_detailed.txt`: Human-readable performance list
- `market_pulse_exec_summary.txt`: Mobile/Speechify-friendly summary

## Quick sanity check
**What good console output looks like:**
```
🚀 Starting Market Pulse Analysis...
🔍 Running slopes benchmark...
📈 Found 404 symbols (excluded 14 stablecoins)
  📊 Processing 1h timeframe...
  📊 Processing 4h timeframe...
  📊 Processing 1d timeframe...
📊 Excel report saved: out/market_pulse_2024-12-19.xlsx
📄 Text files generated:
   • symbols: out/market_pulse_top20_symbols.txt
   • detailed: out/market_pulse_top20_detailed.txt
   • summary: out/market_pulse_exec_summary.txt
✅ Market Pulse Analysis Complete!
```

## Usage Example
```bash
# Run with default settings
python3 market_pulse.py

# Run with custom config
python3 market_pulse.py --config custom_pulse.yaml

# Run for specific symbols only
python3 market_pulse.py --symbols "BTCUSDT,ETHUSDT,SOLUSDT"
```

## Dependencies
- Requires existing `slopes_benchmark.yaml` and `coil_spring.yaml` configurations
- Uses OHLCV data from `ohlcv_parquet/` directory
- See main project README for installation requirements
