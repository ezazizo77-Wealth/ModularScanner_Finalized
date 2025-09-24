
# Pseudocode for Multi-TF Trend Agreement Score
# This assumes MA values are already computed and passed in

def evaluate_trend(ma_values):
    # Expecting ma_values = [ma1, ma2, ma3, ma4, ma5]
    if ma_values == sorted(ma_values):
        return 1.0  # Fully aligned
    elif ma_values[0] < ma_values[1] and ma_values[2] < ma_values[3]:
        return 0.5  # Partially aligned
    else:
        return 0.0  # No alignment

def compute_agreement_score(data):
    total_score = 0
    for tf, values in data.items():  # tf = timeframe, values = MA list
        tf_score = evaluate_trend(values['mas'])
        total_score += tf_score * values['weight']
    return total_score
