import os, re
import pandas as pd

def load_parquet(path):
    return pd.read_parquet(path)

def resample_to_day(df):
    if 'ts' in df.columns:
        df = df.set_index('ts')
    out = df.resample('1D').agg({
        'open':'first','high':'max','low':'min','close':'last','volume':'sum'
    }).dropna().reset_index()
    return out

# ---------- per-file discovery ----------
def list_symbols(path_1h, universe_regex):
    rx = re.compile(universe_regex)
    syms = []
    if not os.path.exists(path_1h):
        print(f"[DISCOVERY] 1h path not found: {path_1h}")
        return syms
    for fn in os.listdir(path_1h):
        if fn.endswith('.parquet'):
            stem = fn[:-8]
            if rx.match(stem):
                syms.append(stem)
    syms = sorted(list(set(syms)))
    print(f"[DISCOVERY] Found {len(syms)} symbols under {path_1h}")
    return syms

# ---------- monolithic mode ----------
def monolithic_list_symbols(file_1h, universe_regex):
    if not os.path.exists(file_1h):
        print(f"[DISCOVERY] 1h file not found: {file_1h}")
        return []
    df = pd.read_parquet(file_1h, columns=['symbol'])
    syms = sorted(df['symbol'].dropna().unique().tolist())
    if universe_regex and universe_regex != ".*":
        rx = re.compile(universe_regex)
        syms = [s for s in syms if rx.match(s)]
    print(f"[DISCOVERY] Found {len(syms)} symbols in {file_1h}")
    return syms

def monolithic_load_symbol(file_path, symbol):
    return pd.read_parquet(file_path, filters=[('symbol','==',symbol)])