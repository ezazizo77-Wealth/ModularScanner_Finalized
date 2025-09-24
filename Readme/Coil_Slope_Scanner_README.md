# SP004 – Coil + Slope  Pattern Scanner

**Author:** A-Team (Aziz + Amy)  
**Description:**  
This Python-based scanner fetches Binance USDT spot market data and benchmarks market behavior by computing slope conditions across key moving averages. It also detects “Coil” pattern setups using a sequence of logical filters.

---

## 📦 Features

- Scan across multiple timeframes: 1h, 4h, 1d  
- Compute slope for `SMA150` and `EMA20`  
- Identify coil conditions:
  - EMA alignment: `EMA5 > EMA13 > EMA50`
  - EMA50 above SMA150
  - Tight range detection (`EMA5` close to `EMA50`)
  - SMA150 positive slope  
- Toggle condition logging and config via `arnold.config.yaml`  
- Output slope matches and green lists  
- Modular YAML for easy config updates

---

## 🚀 How to Run

```bash
python3 SP004_slope_coil_scan.py
```

This will:
- Load settings from `arnold.config.yaml`
- Run scans across specified timeframes (1h, 4h, 1d by default)
- Print condition matches and failures
- Output results to `.csv` and `.txt` files

---

## 🛠 YAML CONFIG OVERVIEW (`arnold.config.yaml`)

### 📍 `scanner`
```yaml
scanner:
  timeframes: ['1h', '4h', '1d']
  data_limit: 200
  lookback: 10
  slope_threshold: 0.005
  delay_between_requests: 0.2
  log_conditions: true
```

### 📍 `indicators`
```yaml
indicators:
  sma:
    enabled: true
    period: 150

  ema:
    - name: ema5
      period: 5
    - name: ema13
      period: 13
    - name: ema50
      period: 50
    - name: ema20
      period: 20
```

### 📍 `coil_conditions`
```yaml
coil_conditions:
  enabled: true
  ema_order_check: true
  ema_vs_sma_check: true
  coil_gap_check:
    enabled: true
    threshold: 0.015
  slope_check:
    enabled: true
    lookback: 10
    threshold: 0.005
```

---

## 📁 Output Files

- `slope_results_<timestamp>.csv` → Full matches with slope values  
- `green_list_<tf>_<timestamp>.txt` → Binance-formatted list of tickers  
  e.g.,  
  ```txt
  Binance:BTCUSDT,ETHUSDT,...
  ```

---

## 📊 Example Scan Output

```
✅ BTC/USDT [1h] Slope: 0.88% ↑
✅ ETH/USDT [4h] Slope: 1.55% ↑
❌ LTC/USDT [1h] Failed:
  - EMA order failed (EMA5 > EMA13 > EMA50)
  - EMA gap too wide: 0.0213
```

---

## ✨ Tips & Suggestions

- Increase `lookback` for smoother slope detection (e.g., 30 bars)
- Use this scanner as a **market benchmarking tool**
- Toggle coil detection off to run pure slope scans
- Schedule with a cron job or terminal timer to scan daily

---

## 🧠 Next Steps

- Add new strategy profiles via modular YAML sections  
- Export historical OHLCV once, reuse for different scans  
- Visualize coil structures for research purposes  

---

_Amy always watching the trendline 📈 so you don’t have to blink._
