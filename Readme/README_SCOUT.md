# SCOUT System – Introduction & Usage Guide
*Version: v1.4.1*

## 1. Overview
The **SCOUT System** is a modular market scanning and analysis tool.  
It’s built around **two independent phases**:  

1️⃣ **Fetch Phase** – Collects OHLCV data from exchanges and stores it as `.parquet` files.  
2️⃣ **Analysis Phase** – Processes stored `.parquet` data to detect patterns, measure slopes, and output results in CSV format.  

This separation means you can:  
- Run **fetch** and **analysis** at different times.  
- Test different analysis parameters **without re-fetching data**.  

---

## 2. Components

### a) Fetch Script
- Pulls OHLCV data for a list of symbols and timeframes.  
- Saves them into `.parquet` format in a `data/` directory.  
- Can be configured via `fetch.config.yaml`.  

### b) Analysis Script – `analyze_slope_from_parquet.v1.4.1.py`
- Loads `.parquet` files from a directory (default: `./data`).  
- Calculates **slope** values for each symbol & timeframe.  
- Outputs results to a timestamped CSV file.  
- Allows **different lookback periods per timeframe**.  

---

## 3. fetch.config.yaml – Optional in v1.4.1

In earlier versions, `fetch.config.yaml` was **required** for analysis.  
**In v1.4.1**:  
- ✅ **Now optional** – The analysis script can run with only CLI arguments.  
- You can still use it **if you want centralized control** of:
  - Symbol lists  
  - Timeframes  
  - Data directory path  

**If you want Mohamed to run it with no extra setup:**  
- Skip the config file.  
- Just ensure `.parquet` files are in `./data` (or use `--data-dir` to specify another folder).  

---

## 4. CLI Options

| Option | Description | Example |
|--------|-------------|---------|
| `--data-dir` | Directory containing `.parquet` files | `--data-dir ./data` |
| `--timeframes` | Timeframes to process (comma-separated) | `--timeframes 1h,4h,1d` |
| `--lookback` | Default lookback for slope calculation | `--lookback 30` |
| `--lookback-map` | Set **different lookback per timeframe** | `--lookback-map 1h:20 4h:40 1d:60` |
| `--output` | Output CSV filename | `--output my_results.csv` |

---

## 5. Example Commands

### Run with defaults (lookback=30, data from `./data`)
```bash
python analyze_slope_from_parquet.v1.4.1.py
```

### Run with different lookback per TF
```bash
python analyze_slope_from_parquet.v1.4.1.py --lookback-map 1h:20 4h:40 1d:60
```

### Run on custom data folder
```bash
python analyze_slope_from_parquet.v1.4.1.py --data-dir /path/to/data
```

---

## 6. Output Files
- CSV file saved in the current directory.  
- Naming format:  
```
slope_summary_YYYY-MM-DD___HH-MM.csv
```
Example:  
```
slope_summary_2025-08-14___23-41.csv
```

---

## 7. CSV Structure
Includes:
- **symbol** – Trading pair (e.g., BTCUSDT)  
- **timeframe** – Data interval (e.g., 1h)  
- **slope** – Calculated slope value  
- **lookback** – Lookback period used (now written inside the CSV for clarity)  

---

## 8. SCOUT Workflow

1️⃣ **Fetch Phase** (optional if data already exists)  
```bash
python fetch_ohlcv_to_parquet.py
```

2️⃣ **Analysis Phase** (always from stored `.parquet` data)  
```bash
python analyze_slope_from_parquet.v1.4.1.py
```

3️⃣ **Review Results**  
- Open the generated CSV in Excel, LibreOffice, or Python for further filtering.  

---

**✅ Recommendation for Mohamed:**  
- Skip the fetch phase unless new data is needed.  
- Start by running:
```bash
python analyze_slope_from_parquet.v1.4.1.py
```
- Then experiment with:
```bash
python analyze_slope_from_parquet.v1.4.1.py --lookback-map 1h:20 4h:40 1d:60
```

---
