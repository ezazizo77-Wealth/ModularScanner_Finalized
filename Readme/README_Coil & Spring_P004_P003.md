# Coil & Spring (P004/P003) – CLI-first Scanner

Runs like your `analyze_slope_from_parquet.py`: CLI-first, single command in your parquet directory.
- Reads Parquet OHLCV (1h + 1d) from `--input-dir`.
- Computes TBO ribbon (EMA21, SMA40/50/150), ATR(14), VOL20.
- 1h Coil detection + 1d Confluence + optional breakout flag.
- Outputs ranked CSV/JSON to `out/` with timestamp (unless --no-timestamp).
