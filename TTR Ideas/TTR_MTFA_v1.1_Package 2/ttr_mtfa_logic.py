# === ttr.py additions for MTFA ===

from indicators import calculate_ema_stack_score

def calculate_mtfa_score(parquet_data, emas, weights):
    """Calculate MTFA weighted score from EMA stack scores across timeframes."""
    mtfa_score = 0
    total_weight = 0
    breakdown = {}

    for tf, weight in weights.items():
        df = parquet_data[tf]
        score = calculate_ema_stack_score(df, emas)
        mtfa_score += score * weight
        breakdown[tf] = score
        total_weight += weight

    mtfa_score /= total_weight
    return mtfa_score, breakdown