# Amy's v2 Coil & Spring Pipeline - User Guide

## 🎯 **Overview**

Amy's v2 pipeline is a **modular, multi-timeframe coil detection system** that provides high-quality trading signals through a 3-stage filtering process. The system is designed to be **highly configurable** and **testable** - you can enable/disable stages and adjust parameters to find the optimal settings for your trading strategy.

---

## 🏗️ **Pipeline Architecture**

### **3-Stage Pipeline:**
1. **Stage 1: `coil_1h`** - Detect tight coil formation on 1h timeframe
2. **Stage 2: `match_4h`** - Confirm with 4h timeframe (either coiled OR turning up)
3. **Stage 3: `confirm_1d`** - Final confirmation with daily trend bias

### **Key Features:**
- **Modular**: Enable/disable any stage independently
- **Multi-timeframe**: Uses 1h, 4h, and 1d data
- **Flexible**: "Either" mode for 4h matching (coiled OR turning up)
- **Testable**: Benchmark mode shows all symbols with pipeline results

---

## ⚙️ **Configuration Guide**

### **1. Stage Control**

#### **Enable/Disable Stages:**
```yaml
control:
  enabled_stages: ["coil_1h", "match_4h", "confirm_1d"]  # All stages
  # enabled_stages: ["coil_1h"]                           # Only 1h coil detection
  # enabled_stages: ["coil_1h", "match_4h"]              # Skip daily confirmation
  # enabled_stages: ["coil_1h", "confirm_1d"]            # Skip 4h matching
```

#### **Benchmark Mode:**
```yaml
control:
  benchmark: true   # Shows ALL symbols with pipeline results (no filtering)
  benchmark: false  # Only shows symbols passing all enabled stages
```

### **2. Stage 1: 1h Coil Detection (`coil_1h`)**

#### **Core Parameters:**
```yaml
coil_1h:
  max_fast3_width_pct: 3.0      # Tightness threshold (lower = more restrictive)
  min_bars_in_coil: 10          # Persistence requirement (higher = more restrictive)
  max_tr_range_atr: 1.2         # Volatility guard (lower = more restrictive)
  min_ma21_slope_pct: -0.10     # EMA21 slope bias (optional)
```

#### **Parameter Tuning Guide:**

**`max_fast3_width_pct`** - Bundle Tightness:
- **Tight (1.0-2.0%)**: Very selective, only extremely tight coils
- **Moderate (2.0-4.0%)**: Balanced selection, good for most markets
- **Loose (4.0-8.0%)**: More inclusive, catches wider formations
- **Very Loose (8.0%+)**: Catches most coil-like formations

**`min_bars_in_coil`** - Persistence:
- **Short (5-8 bars)**: Catches brief coil formations
- **Medium (8-12 bars)**: Balanced persistence requirement
- **Long (12-20 bars)**: Requires sustained coil formation
- **Very Long (20+ bars)**: Only very persistent coils

**`max_tr_range_atr`** - Volatility Guard:
- **Low (0.8-1.0)**: Only very quiet periods
- **Medium (1.0-1.5)**: Normal volatility tolerance
- **High (1.5-2.0)**: Allows more volatile periods
- **Very High (2.0+)**: Minimal volatility filtering

### **3. Stage 2: 4h Matching (`match_4h`)**

#### **Core Parameters:**
```yaml
match_4h:
  mode: "either"                # "either" = OR logic, "and" = AND logic
  
  # Option A: Also coiled on 4h
  max_fast3_width_pct: 8.0     # 4h coil tightness (usually looser than 1h)
  min_bars_in_coil: 4          # 4h persistence (usually shorter than 1h)
  
  # Option B: Alignment/turn-up on 4h
  min_ma21_slope_pct: 0.0      # EMA21 slope requirement
  min_ma50_slope_pct: 0.0      # SMA50 slope requirement
```

#### **Mode Selection:**

**`mode: "either"`** (Recommended):
- Symbol passes if **EITHER**:
  - 4h is also coiled (Option A), **OR**
  - 4h shows upward momentum (Option B)
- **More inclusive**, catches different market conditions
- **Better for trending markets**

**`mode: "and"`** (Restrictive):
- Symbol passes if **BOTH**:
  - 4h is also coiled (Option A), **AND**
  - 4h shows upward momentum (Option B)
- **Very selective**, only perfect setups
- **Better for range-bound markets**

#### **Parameter Tuning:**

**4h Coil Parameters** (Option A):
- **`max_fast3_width_pct`**: Usually 2-3x looser than 1h (6.0-12.0%)
- **`min_bars_in_coil`**: Usually shorter than 1h (3-8 bars)

**Slope Parameters** (Option B):
- **`min_ma21_slope_pct`**: 0.0% = flat or up, -0.5% = allow slight down
- **`min_ma50_slope_pct`**: 0.0% = flat or up, -0.2% = allow slight down

### **4. Stage 3: Daily Confirmation (`confirm_1d`)**

#### **Core Parameters:**
```yaml
confirm_1d:
  min_sma150_slope_pct: 0.0     # Daily trend requirement
  tolerance_pct: 0.0            # Tolerance for slope requirement
```

#### **Parameter Tuning:**

**`min_sma150_slope_pct`** - Daily Trend:
- **Bullish (0.0%+)**: Only uptrending daily charts
- **Neutral (-0.1% to 0.1%)**: Flat or slightly up
- **Permissive (-0.5% to 0.0%)**: Allows slight downtrends
- **Very Permissive (-1.0%+)**: Allows significant downtrends

**`tolerance_pct`** - Flexibility:
- **Strict (0.0%)**: Exact slope requirement
- **Moderate (0.1-0.2%)**: Small tolerance
- **Flexible (0.3-0.5%)**: Significant tolerance

---

## 🎛️ **Optimization Strategies**

### **Strategy 1: Conservative (High Quality)**
```yaml
control:
  enabled_stages: ["coil_1h", "match_4h", "confirm_1d"]

coil_1h:
  max_fast3_width_pct: 2.0      # Very tight
  min_bars_in_coil: 12         # High persistence
  max_tr_range_atr: 1.0        # Low volatility

match_4h:
  mode: "and"                  # Both conditions required
  max_fast3_width_pct: 6.0
  min_bars_in_coil: 6
  min_ma21_slope_pct: 0.2      # Strong upward bias
  min_ma50_slope_pct: 0.1

confirm_1d:
  min_sma150_slope_pct: 0.1    # Strong daily uptrend
  tolerance_pct: 0.0
```
**Result**: Very few signals, but extremely high quality

### **Strategy 2: Balanced (Moderate Quality)**
```yaml
control:
  enabled_stages: ["coil_1h", "match_4h", "confirm_1d"]

coil_1h:
  max_fast3_width_pct: 3.0      # Moderate tightness
  min_bars_in_coil: 8          # Moderate persistence
  max_tr_range_atr: 1.2        # Normal volatility

match_4h:
  mode: "either"               # Either condition
  max_fast3_width_pct: 8.0
  min_bars_in_coil: 4
  min_ma21_slope_pct: 0.0      # Flat or up
  min_ma50_slope_pct: 0.0

confirm_1d:
  min_sma150_slope_pct: 0.0    # Flat or up
  tolerance_pct: 0.1
```
**Result**: Good balance of quality and quantity

### **Strategy 3: Aggressive (More Signals)**
```yaml
control:
  enabled_stages: ["coil_1h", "match_4h"]  # Skip daily confirmation

coil_1h:
  max_fast3_width_pct: 5.0      # Loose tightness
  min_bars_in_coil: 5          # Short persistence
  max_tr_range_atr: 1.5        # High volatility

match_4h:
  mode: "either"
  max_fast3_width_pct: 12.0
  min_bars_in_coil: 3
  min_ma21_slope_pct: -0.2     # Allow slight down
  min_ma50_slope_pct: -0.1
```
**Result**: More signals, but lower quality

### **Strategy 4: Testing Individual Stages**
```yaml
# Test only 1h coil detection
control:
  enabled_stages: ["coil_1h"]

# Test only 4h matching
control:
  enabled_stages: ["match_4h"]

# Test only daily confirmation
control:
  enabled_stages: ["confirm_1d"]
```
**Result**: Understand each stage's impact

---

## 📊 **Usage Examples**

### **Example 1: Market Scanning**
```bash
# Scan all symbols with balanced settings
python3 coil_spring.py --cfg coil_spring.yaml

# Scan with verbose output to see pipeline results
python3 coil_spring.py --cfg coil_spring.yaml --verbose

# Benchmark mode to see all symbols with pipeline results
python3 coil_spring.py --cfg coil_spring_benchmark.yaml
```

### **Example 2: Parameter Testing**
```bash
# Test conservative settings
python3 coil_spring.py --cfg conservative_config.yaml

# Test aggressive settings  
python3 coil_spring.py --cfg aggressive_config.yaml

# Compare results
ls -la out/ | grep coil_spring
```

### **Example 3: Stage Analysis**
```bash
# Test only 1h coil detection
python3 coil_spring.py --cfg coil_1h_only.yaml

# Test 1h + 4h (skip daily)
python3 coil_spring.py --cfg coil_1h_4h.yaml

# Test all stages
python3 coil_spring.py --cfg coil_all_stages.yaml
```

---

## 🔍 **Interpreting Results**

### **Output Columns:**
- **`coil_pass`**: Did Stage 1 (1h coil) pass?
- **`match_pass`**: Did Stage 2 (4h matching) pass?
- **`confirm_pass`**: Did Stage 3 (1d confirmation) pass?
- **`fast3_width_pct`**: Current bundle width percentage
- **`bars_in_coil`**: Consecutive bars in coil state
- **`tr_range_atr`**: Current volatility ratio
- **`sma150_slope_bps`**: Daily trend slope

### **Result Analysis:**
```bash
# Count symbols passing each stage
python3 -c "
import pandas as pd
df = pd.read_csv('out/coil_spring_benchmark_*.csv')
print('Stage 1 (coil_1h):', df['coil_pass'].sum())
print('Stage 2 (match_4h):', df['match_pass'].sum())  
print('Stage 3 (confirm_1d):', df['confirm_pass'].sum())
print('All stages:', ((df['coil_pass']) & (df['match_pass']) & (df['confirm_pass'])).sum())
"
```

---

## 🎯 **Best Practices**

### **1. Start with Benchmark Mode**
Always run benchmark mode first to understand the market:
```bash
python3 coil_spring.py --cfg coil_spring_benchmark.yaml --verbose
```

### **2. Test Individual Stages**
Understand each stage's impact:
```yaml
# Test each stage individually
enabled_stages: ["coil_1h"]     # Only 1h
enabled_stages: ["match_4h"]   # Only 4h  
enabled_stages: ["confirm_1d"] # Only 1d
```

### **3. Gradual Parameter Adjustment**
Start loose and tighten:
```yaml
# Start loose
max_fast3_width_pct: 8.0
min_bars_in_coil: 5

# Gradually tighten
max_fast3_width_pct: 5.0
min_bars_in_coil: 8

# Final tight
max_fast3_width_pct: 3.0
min_bars_in_coil: 10
```

### **4. Market Condition Adaptation**
Adjust for market conditions:
- **Bull Market**: Looser daily confirmation
- **Bear Market**: Stricter daily confirmation
- **Range-bound**: Focus on coil tightness
- **Trending**: Focus on momentum alignment

### **5. Regular Monitoring**
- Run daily to track pipeline performance
- Monitor pass rates for each stage
- Adjust parameters based on results
- Keep logs of successful configurations

---

## 🚀 **Quick Start Checklist**

1. **✅ Run benchmark mode** to see all pipeline results
2. **✅ Test individual stages** to understand impact
3. **✅ Start with balanced parameters** (Strategy 2)
4. **✅ Adjust based on results** (loosen if too few, tighten if too many)
5. **✅ Monitor performance** over time
6. **✅ Adapt to market conditions** as needed

---

## 📈 **Expected Results**

### **Conservative Settings:**
- **Signals**: 0-5 per day
- **Quality**: Very high
- **Use case**: High-conviction trades

### **Balanced Settings:**
- **Signals**: 5-20 per day  
- **Quality**: High
- **Use case**: Regular trading

### **Aggressive Settings:**
- **Signals**: 20-50 per day
- **Quality**: Moderate
- **Use case**: Screening and research

---

**Amy's v2 pipeline gives you complete control over signal quality vs quantity. Experiment with different configurations to find what works best for your trading style! 🎯**
