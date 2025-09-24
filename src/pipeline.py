import os
import pandas as pd
from .io_load import (
    load_parquet, resample_to_day, list_symbols,
    monolithic_list_symbols, monolithic_load_symbol
)
from .rules import (
    compute_features, coil_mask_1h, coil_box, confluence_mask_1d,
    breakout_flag, coil_tightness_score, rank_row
)

def load_symbol_frames(sym, cfg):
    if cfg.get('io', {}).get('mode') == 'monolithic':
        f1h = cfg['io']['file_1h']
        f1d = cfg['io'].get('file_1d')
        df1h = monolithic_load_symbol(f1h, sym)
        if 'ts' not in df1h.columns:
            raise ValueError(f"{sym}: expected 'ts' column in 1h parquet")
        df1h['ts'] = pd.to_datetime(df1h['ts'], utc=True)

        if f1d and os.path.exists(f1d):
            df1d = monolithic_load_symbol(f1d, sym)
            df1d['ts'] = pd.to_datetime(df1d['ts'], utc=True)
        else:
            df1d = resample_to_day(df1h.copy())
        return df1h.sort_values('ts').reset_index(drop=True), df1d.sort_values('ts').reset_index(drop=True)

    # per-file mode
    p1h = os.path.join(cfg['io']['path_1h'], f'{sym}.parquet')
    p1d = os.path.join(cfg['io']['path_1d'], f'{sym}.parquet')

    df1h = load_parquet(p1h)
    if 'ts' not in df1h.columns:
        raise ValueError(f"{sym}: expected 'ts' column in 1h parquet")
    df1h['ts'] = pd.to_datetime(df1h['ts'], utc=True)

    if os.path.exists(p1d):
        df1d = load_parquet(p1d); df1d['ts'] = pd.to_datetime(df1d['ts'], utc=True)
    else:
        df1d = resample_to_day(df1h.copy())

    return df1h.sort_values('ts').reset_index(drop=True), df1d.sort_values('ts').reset_index(drop=True)

def run_symbol(sym, cfg):
    df1h, df1d = load_symbol_frames(sym, cfg)
    df1h = compute_features(df1h, cfg)
    df1d = compute_features(df1d, cfg)
    m_coil = coil_mask_1h(df1h, cfg)
    m_conf_d = confluence_mask_1d(df1d, cfg)
    df1d_idx = df1d.set_index('ts')
    out_rows = []
    for i in range(len(df1h)):
        if not bool(m_coil.iloc[i]):
            continue
        ts = df1h['ts'].iloc[i]
        try:
            idx_d = df1d_idx.index.get_loc(ts, method='pad')
            conf = bool(m_conf_d.iloc[idx_d])
        except KeyError:
            continue
        lo, hi = coil_box(df1h, i, lookback=6)
        brk = breakout_flag(df1h, i, hi, cfg)
        coil_score = coil_tightness_score(df1h, i)
        rank = rank_row(coil_score, conf, df1h['VOL20'].iloc[i], cfg)
        out_rows.append({
            'symbol': sym, 'ts_1h': ts,
            'close': float(df1h['close'].iloc[i]),
            'coil_low': float(lo), 'coil_high': float(hi),
            'daily_confluence': int(conf),
            'breakout_now': int(brk),
            'coil_score': round(coil_score, 6),
            'vol20': float(df1h['VOL20'].iloc[i]) if pd.notna(df1h['VOL20'].iloc[i]) else None,
            'rank': round(rank, 6),
        })
    return out_rows

def run_for_universe(cfg, return_scanned_count=False):
    if cfg.get('symbols'):
        syms = cfg['symbols']
    else:
        if cfg.get('io', {}).get('mode') == 'monolithic':
            syms = monolithic_list_symbols(cfg['io']['file_1h'], cfg.get('universe_regex', '.*'))
        else:
            syms = list_symbols(cfg['io']['path_1h'], cfg.get('universe_regex', '.*'))

    all_rows, scanned = [], 0
    for sym in syms:
        scanned += 1
        try:
            all_rows.extend(run_symbol(sym, cfg))
        except Exception as e:
            print(f"[WARN] {sym}: {e}")
    all_rows.sort(key=lambda r: r['rank'], reverse=True)
    return (all_rows, scanned) if return_scanned_count else all_rows