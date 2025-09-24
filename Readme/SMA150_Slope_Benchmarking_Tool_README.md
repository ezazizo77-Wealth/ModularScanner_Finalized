# 📈 SP004 – SMA150 Slope Benchmarking Tool

**Author:** A-Team (Aziz + Amy)  
**Purpose:** Scan Binance USDT spot markets across multiple timeframes and identify assets with strong positive SMA150 slope trends.

---

## 🔧 Description  
This tool evaluates the **slope of the 150-period SMA** for all active USDT spot pairs on Binance over specified timeframes (`1h`, `4h`, `1d` by default). It highlights coins whose SMA slope exceeds a defined threshold, saving results and generating watchlists.

---

## 🚀 Features
- Multi-timeframe SMA slope analysis (`--timeframes`)
- Configurable slope threshold (`--threshold`)
- Auto-generated `.csv` report with slope % and absolute diff
- Green-listed watchlists per timeframe in `.txt` format (`BINANCE:<SYMBOL>USDT`)
- Runtime statistics: start, end, and duration
- Effectiveness summary: scanned coins, matching coins per timeframe
- Optional verbose mode for deeper logging and failure inspection (`--verbose`)

---

## ⚙️ Usage

```bash
python3 SP004_slope_scanner.py [--timeframes 1h 4h 1d] [--threshold 0.005] [--verbose]
```

### 📌 Example:
```bash
python3 SP004_slope_scanner.py --timeframes 1h 4h 1d --threshold 0.007 --verbose
```

---

## 📝 Output Files

- `slope_summary_<timestamp>.csv`: Full list of matching symbols with slope data
- `green_list_<timeframe>_<timestamp>.txt`: Binance-format list of strong slope assets
- Console logs: Scan progress, match info, effectiveness, duration

---

## 📦 Dependencies
- `ccxt` – fetch Binance data
- `pandas` – data manipulation
- `ta` – technical indicators
- `argparse`, `datetime`, `time`, `pathlib` – built-in utilities

Install with:

```bash
pip install ccxt pandas ta
```

---

## 📈 Slope Calculation Logic
- **SMA150** is computed on `close` prices
- **Slope %** = `(SMA_now - SMA_past) / SMA_past`
- If slope > `threshold`, the symbol is marked as a potential bullish trend

---

## 📊 Example Output

### ✅ CSV Output:
| symbol   | timeframe | slope_pct | sma_now | sma_past | abs_diff |
|----------|-----------|-----------|---------|----------|----------|
| BTC/USDT | 4h        | 0.67      | 112390  | 111642   | 748.48   |

### 📄 Green List (4h):
```txt
BINANCE:BTCUSDT,BINANCE:ETHUSDT,BINANCE:XRPUSDT
```

---

## 🔍 Notes
- The script **avoids leveraged tokens** (`UP`, `DOWN`, `BULL`, `BEAR`)
- Verbose mode may slow down the scan slightly—use when debugging
- Plots are disabled for performance; can be re-enabled if needed
