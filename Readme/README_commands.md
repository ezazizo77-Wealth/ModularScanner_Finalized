# 🧪 Lucid Engine CLI Usage Guide

This guide explains how to run the `slope_and_coil_scanner.py` script using different modes and flags.

---
Command List:

python3 slope_and_coil_scanner.py test.config.yaml

python3 slope_and_coil_scanner.py arnold.config.yaml

python3 slope_and_coil_scanner.py test.config.yaml --fetch-live


python fetch_ohlcv_to_parquet.py fetch.config.yaml

python fetch_ohlcv_to_parquet_v3.0.0.py --top-n 0

## Health Check After Fetch Command
python post_fetch_health_check.py

## Run this daily
python fetch_ohlcv_to_parquet_v3.0.0.py --top-n 0; python post_fetch_health_check.py
or 
Python fetch_ohlcv_to_parquet_v4.0.0.py --top-n 0; python post_fetch_health_check.py


## 🧵 1. Basic Test Scan (Top 10 Coins)

```bash
python3 slope_and_coil_scanner.py test.config.yaml
```

🔹 Uses `test.config.yaml`  
🔹 Scans only the top 10 coins specified in the config  
🔹 Useful for fast debugging and benchmarking

---

## 🌐 2. Full Market Scan (Live Fetch)

```bash
python3 slope_and_coil_scanner.py arnold.config.yaml --fetch-live
```

🔹 Fetches all live USDT spot coins directly from Binance  
🔹 Ignores `test_symbols` in the config  
🔹 Best used for full benchmarking or production scans

---

## 🧠 3. Hybrid Control

You can also force any YAML file (even test configs) to fetch live data:

```bash
python3 slope_and_coil_scanner.py test.config.yaml --fetch-live
```

🔹 Overrides the test list  
🔹 Scans full market even from test config

---

## ⚠️ Notes

- Make sure you have a virtual environment activated or dependencies installed globally.
- Use `--fetch-live` **only** if you want to override test mode.
- If neither `--fetch-live` nor `use_test_symbols: true` is set, it will **default to scanning full market**.

Here’s a clean and structured entry you can copy into your README_commands.md or commands.txt:

⸻

## 🔹 python fetch_ohlcv_to_parquet.py fetch.config.yaml

🧠 Purpose:
Fetches OHLCV (Open, High, Low, Close, Volume) data from Binance for a list of crypto symbols and timeframes defined in fetch.config.yaml, and saves the results to optimized .parquet files for fast and efficient local analysis.

📦 What it does:
	•	Reads config from fetch.config.yaml
	•	Iterates over all symbols × timeframes
	•	Fetches data using the Binance API
	•	Skips any coins with insufficient data
	•	Combines valid data and saves to:

/ohlcv_parquet/ohlcv_1h.parquet
/ohlcv_parquet/ohlcv_4h.parquet
/ohlcv_parquet/ohlcv_1d.parquet


	•	Uses Parquet format for fast I/O and efficient storage
	•	Prints summary of saved rows and skipped coins

📎 Example:

python fetch_ohlcv_to_parquet.py fetch.config.yaml

✅ Best for:
	•	Preloading historical OHLCV datasets
	•	Preparing data for local slope/coil analysis
	•	Fast, repeatable benchmarking without re-fetching

⸻

Let me know when you’d like to create a CLI switch to toggle between test mode and full mode!
---

## 📌 Future Flags (Planned)

| Flag | Description |
|------|-------------|
| `--coil-only` | Will limit scan to only coil conditions (coming soon) |
| `--export-json` | Export results as JSON (planned) |
| `--debug` | Show raw OHLCV and indicators in logs |

---

🔁 Keep this file updated as new flags or tools are introduced.




### Commands to Use
python coil_spring.py --input-dir ./ohlcv_parquet --cfg ./coil_spring.yaml --verbose

cat out/coil_spring_watchlist_2025-09-13___20-32.csv 

* Change this part: _2025-09-13___20-32.csv when using the cat command
