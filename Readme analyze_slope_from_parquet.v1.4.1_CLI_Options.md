# analyze_slope_from_parquet.v1.4.1 – CLI Options & Usage Guide

This document explains how to use the `analyze_slope_from_parquet.v1.4.1.py` script, including all available CLI (Command-Line Interface) options.

---

## 📌 Basic Usage

Run the script with **default settings** (default lookback = 30):

```bash
python analyze_slope_from_parquet.v1.4.1.py
```

This will:
- Analyze all available symbols in the parquet dataset
- Use the default lookback period of 30
- Output a CSV named like: `slope_summary_YYYY-MM-DD___HH-MM.csv`
- Include a breakdown by timeframe in the console

---

## ⚙️ CLI Options

### `--lookback`
Specify a **single lookback period** (applies to all timeframes).

```bash
python analyze_slope_from_parquet.v1.4.1.py --lookback 50
```
🔹 Example above applies a lookback of 50 bars to **all** timeframes.

---

### `--lookback-map`
Specify **different lookback values for each timeframe**.

✅ **Correct Format (space-separated, no commas):**
```bash
python analyze_slope_from_parquet.v1.4.1.py --lookback-map 1h:20 4h:40 1d:60
```

❌ **Invalid Format (will throw an error):**
```bash
python analyze_slope_from_parquet.v1.4.1.py --lookback-map "1h:20,4h:40,1d:60"
```

---

### `--timeframes`
Limit analysis to specific timeframes.

```bash
python analyze_slope_from_parquet.v1.4.1.py --timeframes 1h 4h
```

---

### `--parquet-dir`
Specify a custom directory for parquet files.

```bash
python analyze_slope_from_parquet.v1.4.1.py --parquet-dir /path/to/parquet/files
```

(Default: current directory)

---

### `--output-dir`
Specify where to save the generated CSV.

```bash
python analyze_slope_from_parquet.v1.4.1.py --output-dir /path/to/output
```

(Default: current directory)

---

### `--top-n`
Show only the **top N slopes** (sorted by absolute slope value).

```bash
python analyze_slope_from_parquet.v1.4.1.py --top-n 20
```

---

## 📂 Example Commands

**Run with default lookback (30) and all timeframes:**
```bash
python analyze_slope_from_parquet.v1.4.1.py
```

**Run with custom lookback for all timeframes:**
```bash
python analyze_slope_from_parquet.v1.4.1.py --lookback 50
```

**Run with different lookbacks per timeframe:**
```bash
python analyze_slope_from_parquet.v1.4.1.py --lookback-map 1h:20 4h:40 1d:60
```

**Run for only 1h and 4h timeframes:**
```bash
python analyze_slope_from_parquet.v1.4.1.py --timeframes 1h 4h
```

**Run with top 15 results only:**
```bash
python analyze_slope_from_parquet.v1.4.1.py --top-n 15
```

---

## 📝 Notes
- CSV filenames follow the format: `slope_summary_YYYY-MM-DD___HH-MM.csv`
- The selected lookback values are recorded **inside the CSV** for future reference.
- If no CLI arguments are provided, defaults are used.

---

**Author:** The A-Team (Aziz & Amy)  
**Version:** v1.4.1
