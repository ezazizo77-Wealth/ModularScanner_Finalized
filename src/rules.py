import pandas as pd
from .indicators import sma, ema, atr, bb_width, pct_slope

def compute_features(df, cfg):
    df = df.copy()
    df['EMA21']  = ema(df['close'], cfg['ma']['ema_fast'])
    df['SMA40']  = sma(df['close'], cfg['ma']['sma_mid_fast'])
    df['SMA50']  = sma(df['close'], cfg['ma']['sma_mid_slow'])
    df['SMA150'] = sma(df['close'], cfg['ma']['sma_slow'])
    df['ATR14']  = atr(df['high'], df['low'], df['close'], 14)
    df['VOL20']  = sma(df['volume'], 20)
    return df

def atr_percentile(series, window=100):
    return series.rolling(window).apply(lambda w: (w <= w.iloc[-1]).mean()*100, raw=False)

def coil_mask_1h(df, cfg):
    c = cfg['coil_1h']
    price = df['close']
    mid_band = 0.5*(df['SMA40'] + df['SMA50'])

    fast_vs_mid = (df['EMA21'] - mid_band).abs()/price*100
    mid_pair    = (df['SMA40'] - df['SMA50']).abs()/price*100

    mx = pd.concat([df['EMA21'], df['SMA40'], df['SMA50']], axis=1).max(axis=1)
    mn = pd.concat([df['EMA21'], df['SMA40'], df['SMA50']], axis=1).min(axis=1)
    ribbon_width = (mx - mn)/price*100

    ribbon_vs_slow = pd.concat([
        (df['EMA21']-df['SMA150']).abs(),
        (df['SMA40']-df['SMA150']).abs(),
        (df['SMA50']-df['SMA150']).abs()
    ], axis=1).max(axis=1)/price*100

    atr_pctl = atr_percentile(df['ATR14'], 100)

    if 'TBO_SQUEEZE' in df.columns and cfg['coil_1h']['require_squeeze']:
        squeeze_ok = df['TBO_SQUEEZE'].astype(bool)
    else:
        bbw = bb_width(df['close']).rolling(100).apply(lambda w: (w <= w.iloc[-1]).mean()*100)
        squeeze_ok = (bbw <= c['atr_min_percentile'])

    mask = (
        (fast_vs_mid <= c['max_fast_vs_mid_pct']) &
        (mid_pair    <= c['max_mid_pair_spread_pct']) &
        (ribbon_width<= c['max_ribbon_width_pct']) &
        (ribbon_vs_slow <= c['max_ribbon_vs_slow_pct']) &
        (atr_pctl <= c['atr_min_percentile']) &
        (squeeze_ok.fillna(False))
    )
    return mask

def coil_box(df, i, lookback=6):
    lo = df['low'].iloc[max(0, i-lookback+1):i+1].min()
    hi = df['high'].iloc[max(0, i-lookback+1):i+1].max()
    return float(lo), float(hi)

def confluence_mask_1d(df_d, cfg):
    c = cfg['confluence_1d']
    price = df_d['close']
    slow_flat = (pct_slope(df_d['SMA150'], 5).abs() <= c['slow_slope_max_pct'])
    mid_tight = ((df_d[['SMA40','SMA50']].max(axis=1) - df_d[['SMA40','SMA50']].min(axis=1)) / price * 100 <= c['mid_band_tight_pct'])
    fast_near = ((df_d['EMA21'] - 0.5*(df_d['SMA40']+df_d['SMA50'])).abs()/price*100 <= c['fast_near_mid_pct'])

    look = int(c['daily_range_lookback'])
    hi = df_d['high'].rolling(look).max()
    lo = df_d['low'].rolling(look).min()
    range_pct = (hi - lo)/price*100
    range_ok = (range_pct <= c['daily_range_max_pct'])

    return (slow_flat & mid_tight & fast_near & range_ok)

def breakout_flag(df, i, coil_hi, cfg):
    if not cfg['breakout']['enabled']:
        return False
    buf = 1.0 + cfg['breakout']['above_coil_buffer_pct']/100.0
    vol_mult = cfg['breakout']['vol_spike_mult']
    price_ok = df['close'].iloc[i] > coil_hi * buf
    vol_ok   = df['volume'].iloc[i] > vol_mult * df['VOL20'].iloc[i]
    return bool(price_ok and vol_ok)

def coil_tightness_score(df, i):
    mx = max(df['EMA21'].iloc[i], df['SMA40'].iloc[i], df['SMA50'].iloc[i])
    mn = min(df['EMA21'].iloc[i], df['SMA40'].iloc[i], df['SMA50'].iloc[i])
    width_pct = (mx - mn) / df['close'].iloc[i] * 100.0
    return float(1.0 / (1e-6 + width_pct))

def rank_row(coil_score, confluence, liquidity, cfg):
    w = cfg['ranking']
    return (
        w['weight_coil_tightness'] * coil_score +
        w['weight_daily_confluence'] * (1.0 if confluence else 0.0) +
        w['weight_liquidity'] * (float(liquidity) if pd.notna(liquidity) else 0.0)
    )
