import argparse, os, sys, yaml, pandas as pd
from datetime import datetime
from src.pipeline import run_for_universe

def build_cfg_from_cli(args, yaml_cfg):
    cfg = yaml_cfg.copy() if yaml_cfg else {}
    cfg.setdefault("io", {})
    cfg["io"]["path_1h"] = os.path.join(args.input_dir, "1h")
    cfg["io"]["path_1d"] = os.path.join(args.input_dir, "1d")
    if args.cfg and "io" in yaml_cfg:
        for k, v in yaml_cfg["io"].items():
            cfg["io"][k] = v
    if args.symbols:
        cfg["symbols"] = args.symbols
    if args.universe_regex:
        cfg["universe_regex"] = args.universe_regex
    return cfg

def save_output(rows, output_name, fmt):
    ts = datetime.utcnow().strftime("%Y-%m-%d___%H-%M")
    os.makedirs("out", exist_ok=True)
    out_fn = os.path.join("out", f"{output_name}_{ts}.{fmt}")
    df = pd.DataFrame(rows)
    if fmt == "csv":
        df.to_csv(out_fn, index=False)
    elif fmt == "parquet":
        df.to_parquet(out_fn, index=False)
    else:
        raise ValueError(f"Unsupported format {fmt}")
    return out_fn, len(df)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", required=True, help="Folder with ohlcv parquet files")
    ap.add_argument("--cfg", help="YAML config path")
    ap.add_argument("--symbols", nargs="*", help="Explicit list of symbols to scan")
    ap.add_argument("--universe-regex", help="Regex filter for symbols")
    ap.add_argument("--output", default="coil_spring_watchlist")
    ap.add_argument("--format", default="csv", choices=["csv","parquet"])
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    yaml_cfg = None
    if args.cfg:
        with open(args.cfg) as f:
            yaml_cfg = yaml.safe_load(f)

    cfg = build_cfg_from_cli(args, yaml_cfg)

    if args.verbose:
        print("[CFG] mode:", cfg.get("io", {}).get("mode", "per-file"))
        if cfg.get("io", {}).get("mode") == "monolithic":
            print("[CFG] 1h file:", cfg["io"].get("file_1h"))
            print("[CFG] 1d file:", cfg["io"].get("file_1d"))
        else:
            print("[CFG] 1h path:", cfg["io"].get("path_1h"))
            print("[CFG] 1d path:", cfg["io"].get("path_1d"))
        if cfg.get("symbols"):
            preview = cfg["symbols"][:10]
            print("[CFG] symbols (explicit):", preview, "..." if len(cfg["symbols"])>10 else "")
        else:
            print("[CFG] universe_regex:", cfg.get("universe_regex"))

    rows, scanned = run_for_universe(cfg, return_scanned_count=True)
    out_fn, nrows = save_output(rows, args.output, args.format)

    print(f"Scanned {scanned} symbols (TF: 1h + 1d)")
    print(f"Detected {nrows} coil rows")
    print(f"[OK] Wrote: {out_fn}  (rows={nrows})")

if __name__ == "__main__":
    main()