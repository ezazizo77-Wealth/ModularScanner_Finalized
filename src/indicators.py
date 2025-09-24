import pandas as pd
import numpy as np

# --------------------
# Basic building blocks
# --------------------
def sma(s: pd.Series, n: int):
    n = int(n)
    return s.rolling(n, min_periods=n).mean()

def ema(s: pd.Series, n: int):
    n = int(n)
    return s.ewm(span=n, adjust=False, min_periods=n).mean()

def atr(h: pd.Series, l: pd.Series, c: pd.Series, n: int = 14):
    """
    Wilder-style ATR (simple rolling mean of True Range).
    """
    n = int(n)
    prev_close = c.shift(1)
    tr = pd.concat(
        [(h - l).abs(), (h - prev_close).abs(), (l - prev_close).abs()],
        axis=1
    ).max(axis=1)
    return tr.rolling(n, min_periods=n).mean()

def bb_width(close: pd.Series, n: int = 20, k: float = 2.0):
    """
    Kept for backward compatibility (your existing helper).
    Returns Bollinger BAND WIDTH (upper - lower).
    """
    ma = sma(close, n)
    sd = close.rolling(n, min_periods=n).std()
    upper = ma + k * sd
    lower = ma - k * sd
    return (upper - lower)

def bbands(close: pd.Series, n: int = 20, k: float = 2.0):
    """
    Full Bollinger bands set: (upper, middle, lower, width_pct_of_price)
    """
    n = int(n)
    ma = sma(close, n)
    sd = close.rolling(n, min_periods=n).std()
    upper = ma + k * sd
    lower = ma - k * sd
    width_pct = (upper - lower) / close * 100.0
    return upper, ma, lower, width_pct

def rsi(close: pd.Series, period: int = 14):
    """
    Relative Strength Index (RSI) calculation using Wilder's smoothing.
    This matches TradingView's RSI calculation exactly.
    Returns RSI values between 0-100.
    """
    period = int(period)
    delta = close.diff()
    
    # Separate gains and losses
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    # Use Wilder's smoothing (exponential moving average with alpha = 1/period)
    # First value is simple average
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    
    # Apply Wilder's smoothing for subsequent values
    alpha = 1.0 / period
    for i in range(period, len(gain)):
        if not pd.isna(avg_gain.iloc[i-1]):
            avg_gain.iloc[i] = alpha * gain.iloc[i] + (1 - alpha) * avg_gain.iloc[i-1]
        if not pd.isna(avg_loss.iloc[i-1]):
            avg_loss.iloc[i] = alpha * loss.iloc[i] + (1 - alpha) * avg_loss.iloc[i-1]
    
    # Calculate RSI
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi

def detect_pullback(close: pd.Series, ema_values: dict, lookback: int = 5):
    """
    Detect recent pullback in trending market.
    Returns pullback percentage and whether pullback occurred.
    """
    lookback = int(lookback)
    if len(close) < lookback + 1:
        return 0.0, False
    
    # Get recent price action
    recent_close = close.iloc[-1]
    recent_high = close.tail(lookback).max()
    
    # Calculate pullback percentage
    pullback_pct = (recent_high - recent_close) / recent_high
    
    # Check if pullback occurred (price below recent high)
    has_pullback = recent_close < recent_high
    
    return pullback_pct, has_pullback

def trend_strength_score(ema_values: dict):
    """
    Quantify trend strength based on EMA stack.
    Returns score between 0-1 (0 = no trend, 1 = perfect trend).
    """
    if not ema_values or len(ema_values) < 2:
        return 0.0
    
    ema_array = np.array(list(ema_values.values()))
    
    # Check for perfect bullish stack
    bullish_perfect = np.all(np.diff(ema_array) > 0)
    # Check for perfect bearish stack
    bearish_perfect = np.all(np.diff(ema_array) < 0)
    
    if bullish_perfect or bearish_perfect:
        return 1.0
    
    # Calculate trend strength based on EMA separation
    ema_range = ema_array.max() - ema_array.min()
    ema_mean = ema_array.mean()
    
    if ema_mean == 0:
        return 0.0
    
    # Normalize by mean price
    normalized_range = ema_range / ema_mean
    
    # Convert to 0-1 scale (adjust threshold as needed)
    strength = min(normalized_range * 10, 1.0)  # Scale factor of 10
    
    return strength

def detect_ema_stack(ema_values: dict):
    """
    Detect EMA stacking pattern and return status with break point.
    Returns: (stack_status, broken_level, trend_direction)
    """
    if not ema_values or len(ema_values) < 2:
        return 'No Data', None, 'Unknown'
    
    ema_names = list(ema_values.keys())
    ema_array = np.array(list(ema_values.values()))
    
    # Check for perfect bullish stack (descending order: short EMAs above long EMAs)
    # EMA5 > EMA13 > EMA21 > EMA50 > EMA200 → diff should be negative
    bullish_perfect = np.all(np.diff(ema_array) < 0)
    # Check for perfect bearish stack (ascending order: short EMAs below long EMAs)
    # EMA5 < EMA13 < EMA21 < EMA50 < EMA200 → diff should be positive
    bearish_perfect = np.all(np.diff(ema_array) > 0)
    
    if bullish_perfect:
        return 'Bullish Stack', None, 'Bullish'
    elif bearish_perfect:
        return 'Bearish Stack', None, 'Bearish'
    else:
        # Find break point
        for i in range(len(ema_array) - 1):
            if (ema_array[i] > ema_array[i+1]) and (ema_array[0] < ema_array[-1]):
                return 'Bullish Broken', ema_names[i], 'Bullish'
            elif (ema_array[i] < ema_array[i+1]) and (ema_array[0] > ema_array[-1]):
                return 'Bearish Broken', ema_names[i], 'Bearish'
        
        return 'Mixed/Choppy', None, 'Mixed'

def pct_slope(series: pd.Series, lookback: int = 100, timeframe: str = None) -> pd.Series:
    """
    Percent change over 'lookback' bars, returned as percentage.
    Useful to judge 'flat vs. rising' for SMA150.
    
    NOTE: The default lookback parameter is 100, but we override this
    for P004 pattern detection to use timeframe-specific periods:
    - 1h timeframe: 72 periods (3 days × 24 hours)
    - 4h timeframe: 20 periods (80 hours = 3.3 days)  
    - 1d timeframe: 20 periods (20 days)
    
    This ensures consistent time horizons across timeframes while
    accounting for the different period lengths.
    """
    lookback = int(lookback)
    
    # Override lookback for P004 pattern detection
    # Original config uses slope_window: 100, but we override for better detection
    if lookback >= 100:  # Default long lookback from config
        if timeframe == "1h":
            lookback = 72  # 3 days × 24 hours = 72 hours
        elif timeframe == "4h":
            lookback = 20  # 80 hours = 3.3 days
        elif timeframe == "1d":
            lookback = 20  # 20 days
        else:
            # Default fallback
            lookback = 20  # Use 20 periods for recent trend detection
    
    base = series.shift(lookback)
    pct = (series - base) / base * 100.0
    return pct  # → percentage (not bps)

def calculate_current_ema_stack_score(row: pd.Series, ema_list: list) -> tuple:
    """
    Calculate EMA stack score and direction for current bar only.
    
    Args:
        row: Current bar data with EMA columns
        ema_list: List of EMA column names (e.g., ['ema5', 'ema13', 'ema21', 'ema50', 'ema200'])
    
    Returns:
        Tuple of (score, direction) where:
        - score: 1.0 if perfectly stacked, 0.0 otherwise
        - direction: 'Bullish', 'Bearish', or 'Mixed'
    """
    if len(ema_list) < 2:
        return 0.0, 'Mixed'
    
    # Check if all EMAs are available
    available_emas = [ema for ema in ema_list if ema in row.index and not pd.isna(row[ema])]
    if len(available_emas) < 2:
        return 0.0, 'Mixed'
    
    # Check for perfect bullish stack (descending order: short-term EMAs above long-term EMAs)
    # EMA5 > EMA13 > EMA21 > EMA50 > EMA200
    bullish = all(row[available_emas[i]] > row[available_emas[i + 1]] for i in range(len(available_emas) - 1))
    
    # Check for perfect bearish stack (ascending order: short-term EMAs below long-term EMAs)
    # EMA5 < EMA13 < EMA21 < EMA50 < EMA200
    bearish = all(row[available_emas[i]] < row[available_emas[i + 1]] for i in range(len(available_emas) - 1))
    
    if bullish:
        return 1.0, 'Bullish'
    elif bearish:
        return 1.0, 'Bearish'
    else:
        return 0.0, 'Mixed'

def compute_mtfa_score(symbol_dfs: dict, config: dict) -> tuple:
    """
    Compute Multi-Timeframe Trend Agreement (MTFA) score with direction.
    
    Args:
        symbol_dfs: Dictionary of {timeframe: DataFrame} for a symbol
        config: TTR configuration dictionary
    
    Returns:
        Tuple of (mtfa_score, mtfa_direction, breakdown_dict)
    """
    if not config.get("mtfa", {}).get("enabled", False):
        return 0.0, 'neutral', {}
    
    mtfa_config = config["mtfa"]
    weights = mtfa_config["weights"]
    ema_periods = mtfa_config["ema_periods"]
    
    # Convert EMA periods to column names
    ema_cols = [f"ema{e}" for e in ema_periods]
    
    scores = []
    directions = []
    breakdown = {}
    
    for tf, df in symbol_dfs.items():
        if tf not in weights or df.empty:
            continue
        
        # Get current bar
        current_row = df.iloc[-1]
        
        # Calculate EMA stack score and direction for this timeframe
        tf_score, tf_direction = calculate_current_ema_stack_score(current_row, ema_cols)
        
        # Weight the score
        weighted_score = tf_score * weights[tf]
        scores.append(weighted_score)
        directions.append(tf_direction)
        breakdown[tf] = {
            'raw_score': tf_score,
            'direction': tf_direction,
            'weight': weights[tf],
            'weighted_score': weighted_score
        }
    
    # Calculate final MTFA score
    mtfa_score = sum(scores) if scores else 0.0
    
    # Determine overall MTFA direction (majority vote)
    if directions:
        bullish_count = directions.count('Bullish')
        bearish_count = directions.count('Bearish')
        
        if bullish_count > bearish_count:
            mtfa_direction = 'bullish'
        elif bearish_count > bullish_count:
            mtfa_direction = 'bearish'
        else:
            mtfa_direction = 'neutral'
    else:
        mtfa_direction = 'neutral'
    
    return mtfa_score, mtfa_direction, breakdown

def apply_mtfa_multiplier(base_signal_strength: float, mtfa_score: float, mtfa_direction: str, config: dict) -> float:
    """
    Apply MTFA multiplier with direction awareness.
    
    Args:
        base_signal_strength: Base signal strength (positive = bullish, negative = bearish)
        mtfa_score: MTFA score (0.0 to 1.0)
        mtfa_direction: MTFA direction ('bullish', 'bearish', 'neutral')
        config: TTR configuration dictionary
    
    Returns:
        Enhanced signal strength
    """
    # Determine base signal direction
    base_trend = 'bullish' if base_signal_strength > 0 else 'bearish'
    
    # Get fallback multiplier from config
    fallback_multiplier = config.get('mtfa', {}).get('fallback_mismatch_multiplier', 0.1)
    
    # Apply conditional multiplier
    if base_trend == mtfa_direction:
        # Directions match → boost signal
        return base_signal_strength * mtfa_score
    else:
        # Directions mismatch → suppress signal
        return base_signal_strength * fallback_multiplier

def classify_mtfa_strength(mtfa_score: float, thresholds: dict) -> str:
    """
    Classify MTFA score into strength categories.
    
    Args:
        mtfa_score: MTFA score (0.0 to 1.0)
        thresholds: Dictionary with 'strong', 'moderate', 'weak' thresholds
    
    Returns:
        Strength category string
    """
    if mtfa_score >= thresholds.get("strong", 0.8):
        return "strong"
    elif mtfa_score >= thresholds.get("moderate", 0.6):
        return "moderate"
    elif mtfa_score >= thresholds.get("weak", 0.4):
        return "weak"
    else:
        return "none"

# --------------------
def compute_features(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """
    Adds derived columns the scanners expect.

    Expected df columns (typical): ts, open, high, low, close, volume, symbol, timeframe
    'cfg' can be the whole YAML dict (we'll look under 'coil_1h' if present),
    or a flat dict with the same keys.

    Adds columns:
      EMA21, SMA40, SMA50, SMA150
      FAST3_WIDTH_PCT, RIBBON_WIDTH_PCT
      SMA150_SLOPE_BPS
      ATR, TR_RANGE, TR_RANGE_ATR
      BB_UPPER, BB_MIDDLE, BB_LOWER, BB_WIDTH_PCT
    """
    out = df.copy()

    # allow params either at top-level or under "coil_1h"
    section = cfg.get("coil_1h", cfg)

    ema_fast       = int(section.get("ema_fast", 21))
    ema_mid_fast   = int(section.get("ema_mid_fast", 40))
    sma_mid_slow   = int(section.get("sma_mid_slow", 50))
    sma_slow       = int(section.get("sma_slow", 150))
    bb_window      = int(section.get("bb_window", 20))
    bb_k           = float(section.get("bb_k", 2.0))
    atr_window     = int(section.get("atr_window", 14))
    slope_window   = int(section.get("slope_window", 100))

    c = out["close"].astype(float)
    h = out["high"].astype(float)
    l = out["low"].astype(float)

    # --- Ribbon MAs ---
    out["EMA21"]  = ema(c, ema_fast)
    out["EMA40"]  = ema(c, ema_mid_fast)
    out["SMA50"]  = sma(c, sma_mid_slow)
    out["SMA150"] = sma(c, sma_slow)

    # --- Width metrics ---
    fast3 = pd.concat([out["EMA21"], out["EMA40"], out["SMA50"]], axis=1)
    # Calculate width only when at least 2 MAs are available
    fast3_width = pd.Series(index=fast3.index, dtype=float)
    for i in range(len(fast3)):
        row_values = fast3.iloc[i].dropna()
        if len(row_values) >= 2:
            fast3_width.iloc[i] = ((row_values.max() - row_values.min()) / c.iloc[i]) * 100.0
        else:
            fast3_width.iloc[i] = np.nan
    out["FAST3_WIDTH_PCT"] = fast3_width

    all4  = pd.concat([out["EMA21"], out["EMA40"], out["SMA50"], out["SMA150"]], axis=1)
    out["RIBBON_WIDTH_PCT"]  = (all4.max(axis=1)  - all4.min(axis=1))  / c * 100.0

    # --- Slope (bps) ---
    # Detect timeframe from data frequency for P004-specific lookback periods
    timeframe = None
    if "timeframe" in out.columns:
        timeframe = out["timeframe"].iloc[0] if len(out) > 0 else None
    
    if timeframe is None and len(out) > 1:
        # Infer timeframe from timestamp differences
        time_diff = (out["ts"].iloc[1] - out["ts"].iloc[0]).total_seconds() / 3600  # hours
        if abs(time_diff - 1.0) < 0.1:
            timeframe = "1h"
        elif abs(time_diff - 4.0) < 0.1:
            timeframe = "4h"
        elif abs(time_diff - 24.0) < 0.1:
            timeframe = "1d"
    
    # --- Slopes (bps) for all 4 ribbon MAs ---
    out["EMA21_SLOPE_BPS"]  = pct_slope(out["EMA21"], slope_window, timeframe)
    out["EMA40_SLOPE_BPS"]  = pct_slope(out["EMA40"], slope_window, timeframe)
    out["SMA50_SLOPE_BPS"]  = pct_slope(out["SMA50"], slope_window, timeframe)
    out["SMA150_SLOPE_BPS"] = pct_slope(out["SMA150"], slope_window, timeframe)

    # --- ATR & wick/noise guard ---
    out["ATR"]         = atr(h, l, c, atr_window)
    out["TR_RANGE"]    = (h - l).abs()
    out["TR_RANGE_ATR"] = out["TR_RANGE"] / out["ATR"]

    # --- Bollinger (for daily / optional checks) ---
    bb_u, bb_m, bb_l, bb_w_pct = bbands(c, bb_window, bb_k)
    out["BB_UPPER"]     = bb_u
    out["BB_MIDDLE"]    = bb_m
    out["BB_LOWER"]     = bb_l
    out["BB_WIDTH_PCT"] = bb_w_pct

    return out