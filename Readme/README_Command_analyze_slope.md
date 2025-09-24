
# 📘 `analyze_slope_from_parquet.py` – CLI Usage Guide

**Author**: A-Team (Aziz + Amy)  
**Version**: `v1.3.0`  
**Purpose**: Analyze the **slope and angle** of price movement from OHLCV Parquet files across multiple timeframes.

---

## 🚀 Usage

```bash
python analyze_slope_from_parquet.py [options]
```

---

## 🧰 CLI Arguments Explained

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `-i`, `--input-dir` | `Path` | `ohlcv_parquet` | Folder containing `.parquet` files named like `ohlcv_1h.parquet`, etc. |
| `-l`, `--lookback` | `int` | `10` | Number of recent candles to use for slope/angle calculation. |
| `-t`, `--timeframes` | `List[str]` | `["1h", "4h", "1d"]` | Timeframes to include in the analysis (must match filenames). |
| `-s`, `--symbols` | `List[str]` | `None` (all symbols) | Filter to only include selected symbols. |
| `-p`, `--price-basis` | `str` | `"close"` | Price type used for slope: `close`, `open`, `hlc3`, or `ohlc4`. |
| `-f`, `--format` | `str` | `"csv"` | Output format: `csv` or `json`. |
| `-o`, `--output` | `str` | `None` (auto-named) | Optional custom output filename. |
| `--no-timestamp` | `flag` | `False` | Prevents adding timestamp to the output filename. |
| `-d`, `--direction` | `str` | `"all"` | Filter direction: `all`, `only_up`, `only_down`, `only_flat`. |
| `-v`, `--verbose` | `flag` | `False` | Print progress and filter/debug info during execution. |

---

## 🔍 Example Usages

### 1. **Basic run (default settings)**

```bash
python analyze_slope_from_parquet.py
```
➡ Analyzes slope/angle on `"close"` price for 1h, 4h, 1d using last 10 candles. Saves to `slope_summary_<timestamp>.csv`.

---

### 2. **Analyze only 1h + 4h, use HLC3 average, output JSON**

```bash
python analyze_slope_from_parquet.py -t 1h 4h -p hlc3 -f json
```

---

### 3. **Analyze with a custom lookback (20 bars) and restrict to BTCUSDT**

```bash
python analyze_slope_from_parquet.py -l 20 -s BTCUSDT
```

---

### 4. **Only show downtrending markets, verbose mode**

```bash
python analyze_slope_from_parquet.py -d only_down -v
```

---

### 5. **Save output with a custom name (no timestamp)**

```bash
python analyze_slope_from_parquet.py -o my_slope_report.csv --no-timestamp
```

---

### 6. **Use OHLC4 basis and filter for flat trends only**

```bash
python analyze_slope_from_parquet.py -p ohlc4 -d only_flat
```

---

## 📂 Output Columns (CSV/JSON)

| Column | Description |
|--------|-------------|
| `symbol` | Trading symbol analyzed |
| `timeframe` | Timeframe of the data |
| `slope_%` | Percent change per bar over the lookback window |
| `direction` | `Up`, `Down`, or `Flat` trend direction |
| `angle_deg` | Slope angle in degrees (geometric interpretation) |





From Cursor AI
### CLI guide: analyze_slope_from_parquet.py

Quickly compute slope and angle per symbol across parquet timeframes with flexible filters and output formats.

### Basic usage
```bash
python analyze_slope_from_parquet.py [options]
```

### Arguments
- **-i, --input-dir PATH**: Directory with parquet files named `ohlcv_{tf}.parquet`. Default: `ohlcv_parquet`
- **-l, --lookback INT**: Number of bars used for slope calculation. Default: 10
- **-t, --timeframes LIST**: Timeframes to analyze (order preserved for sorting). Default: `1h 4h 1d`
- **-s, --symbols LIST**: Optional symbol filter (e.g., `BTC/USDT ETH/USDT`). Default: all symbols in file
- **-p, --price-basis {close,open,hlc3,ohlc4}**: Price basis per bar. Default: `close`
  - `hlc3 = (high+low+close)/3`
  - `ohlc4 = (open+high+low+close)/4`
- **-f, --format {csv,json}**: Output format. Default: `csv`
- **-o, --output PATH**: Output file path. If omitted, uses `slope_summary[_YYYYMMDD_HHMM].{csv|json}`
- **--no-timestamp**: When using the default output name, omit the timestamp suffix
- **-d, --direction {all,only_up,only_down,only_flat}**: Filter by direction. Default: `all`
- **-v, --verbose**: Print progress per timeframe and filtering notes

Output columns: `symbol, timeframe, slope_%, direction, angle_deg`
- `slope_%`: percent per bar (unit-agnostic)
- `angle_deg`: arctangent of percent-per-bar slope (degrees)

### Examples
- Run with defaults:
```bash
python analyze_slope_from_parquet.py
```

- Change lookback and timeframes:
```bash
python analyze_slope_from_parquet.py -l 20 -t 1h 1d
```

- Analyze only selected symbols:
```bash
python analyze_slope_from_parquet.py -s BTC/USDT ETH/USDT
```

- Use different price basis (HLC3) and JSON output:
```bash
python analyze_slope_from_parquet.py -p hlc3 -f json
```

- Fixed output filename without timestamp:
```bash
python analyze_slope_from_parquet.py -o my_slope.csv --no-timestamp
```

- Filter only rising slopes:
```bash
python analyze_slope_from_parquet.py -d only_up
```

- Custom input directory and verbose logs:
```bash
python analyze_slope_from_parquet.py -i ./data/ohlcv -v
```

- Combine filters and format:
```bash
python analyze_slope_from_parquet.py -t 4h 1d -s BTC/USDT -p ohlc4 -d only_down -f json
```

Notes:
- Timeframe sort follows the order you pass in `-t`.
- Parquet files must exist at `--input-dir/ohlcv_{tf}.parquet` and include columns: `symbol, timestamp, open, high, low, close`.

- Wrote a concise README-style guide covering all CLI args, defaults, and usage examples.