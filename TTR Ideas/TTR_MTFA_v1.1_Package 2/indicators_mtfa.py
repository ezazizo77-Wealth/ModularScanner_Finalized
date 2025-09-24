# === indicators.py additions for MTFA ===

def calculate_ema_stack_score(df, emas):
    """Calculate EMA stack score based on how many sequential EMAs are stacked bullish."""
    score = 0
    for i in range(len(emas) - 1):
        if df[f"EMA_{emas[i]}"].iloc[-1] > df[f"EMA_{emas[i+1]}"].iloc[-1]:
            score += 1
    return score / (len(emas) - 1)