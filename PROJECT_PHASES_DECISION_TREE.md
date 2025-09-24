# 🎯 P004 Coil Spring Scanner - Project Phases Decision Tree

## 📊 **Current Status Overview**
- **Phase 1**: ✅ COMPLETED - MA Slopes Scanner Enhancement
- **Phase 2**: ✅ COMPLETED - Amy's v2 Pipeline Implementation  
- **Phase 3**: 🔄 IN PROGRESS - P004 Pattern Reverse Engineering
- **Phase 4**: ⏳ PENDING - Production Readiness

---

## 🌳 **DECISION TREE**

```
START: P004 Coil Spring Scanner Project
│
├── PHASE 1: MA Slopes Scanner Enhancement ✅ COMPLETED
│   ├── 1.1 Top Performers Filter (150+ days data) ✅
│   ├── 1.2 Excel Header Color Coding ✅
│   ├── 1.3 Binance Import File Generation ✅
│   ├── 1.4 SMA40 → EMA40 Migration ✅
│   └── 1.5 Documentation (README, Requirements) ✅
│
├── PHASE 2: Amy's v2 Pipeline Implementation ✅ COMPLETED
│   ├── 2.1 YAML Restructuring ✅
│   ├── 2.2 Core Functions (fast3_width_pct, bars_in_coil, slope_pct) ✅
│   ├── 2.3 Multi-Timeframe Data Loading (1h, 4h, 1d) ✅
│   ├── 2.4 Pipeline Stages (coil_1h, match_4h, confirm_1d) ✅
│   ├── 2.5 Watchlist Generation ✅
│   └── 2.6 User Guide & Example Configs ✅
│
├── PHASE 3: P004 Pattern Reverse Engineering 🔄 IN PROGRESS
│   ├── 3.1 Data Backfill ✅
│   │   ├── Historical data for GNSUSDT ✅
│   │   ├── 1h data: Feb 2025 → Sep 2025 ✅
│   │   ├── 4h data: Dec 2024 → Sep 2025 ✅
│   │   └── 1d data: Feb 2023 → Sep 2025 ✅
│   │
│   ├── 3.2 1h Pipeline Analysis ✅
│   │   ├── Dial 1: FAST3_WIDTH_PCT (≤1.8%) ✅
│   │   ├── Dial 2: TR_RANGE_ATR (≤1.3) ✅
│   │   ├── Dial 3: SMA150_SLOPE_BPS (≥-1.0%) ✅ OPTIMIZED
│   │   └── Combined: 63/96 periods (65.6%) ✅
│   │
│   ├── 3.3 4h Pipeline Analysis ✅
│   │   ├── Width filter: 24/24 (100%) ✅
│   │   ├── TR/ATR filter: 23/24 (95.8%) ✅
│   │   └── Combined: 23/24 periods (95.8%) ✅
│   │
│   ├── 3.4 1d Pipeline Analysis ⏳ NEXT
│   │   ├── Need more historical data
│   │   ├── Test SMA150 availability
│   │   └── Validate 1d coil detection
│   │
│   └── 3.5 Multi-Symbol Validation ⏳ PENDING
│       ├── Test DATAUSDT, ASRUSDT, GPSUSDT, CTKUSDT
│       ├── Validate pattern consistency
│       └── Refine parameters if needed
│
└── PHASE 4: Production Readiness ⏳ PENDING
    ├── 4.1 Complete Pipeline Testing
    │   ├── All 3 timeframes working
    │   ├── End-to-end validation
    │   └── Performance optimization
    │
    ├── 4.2 Live Market Testing
    │   ├── Current market data
    │   ├── Real-time pattern detection
    │   └── Watchlist generation
    │
    ├── 4.3 Documentation & Deployment
    │   ├── Final user guide
    │   ├── Deployment instructions
    │   └── Monitoring setup
    │
    └── 4.4 Maintenance & Updates
        ├── Parameter tuning
        ├── Pattern refinement
        └── Performance monitoring
```

---

## 🎯 **CURRENT DECISION POINT**

**Where are we now?**
- ✅ **Phase 3.2**: 1h pipeline analysis completed
- ✅ **Phase 3.3**: 4h pipeline analysis completed  
- 🔄 **Phase 3.4**: 1d pipeline analysis - **NEXT STEP**

**What are our options?**

### **Option A: Complete 1d Pipeline (Phase 3.4)**
```
3.4.1 → Fetch more 1d historical data
3.4.2 → Test SMA150 availability for 1d
3.4.3 → Validate 1d coil detection
3.4.4 → Test complete 3-stage pipeline
```

### **Option B: Test Updated Configuration (Phase 3.2)**
```
3.2.1 → Run scanner with -1.0% SMA150 slope
3.2.2 → Verify improved precision
3.2.3 → Compare before/after results
3.2.4 → Document optimization impact
```

### **Option C: Multi-Symbol Validation (Phase 3.5)**
```
3.5.1 → Test DATAUSDT P004 pattern
3.5.2 → Test ASRUSDT P004 pattern  
3.5.3 → Test GPSUSDT P004 pattern
3.5.4 → Test CTKUSDT P004 pattern
3.5.5 → Refine parameters based on results
```

### **Option D: Production Testing (Phase 4.1)**
```
4.1.1 → Test complete pipeline on current data
4.1.2 → Generate live watchlists
4.1.3 → Validate real-time detection
4.1.4 → Performance optimization
```

---

## 🤔 **RECOMMENDATION**

**Suggested Path: Option A → Option B → Option C → Option D**

1. **Complete 1d Pipeline** (Phase 3.4) - Finish the technical foundation
2. **Test Updated Config** (Phase 3.2) - Validate our optimization
3. **Multi-Symbol Validation** (Phase 3.5) - Ensure robustness
4. **Production Testing** (Phase 4.1) - Move to live deployment

---

## 📋 **QUICK REFERENCE**

**Current Configuration:**
- `max_fast3_width_pct: 1.8%`
- `max_tr_range_atr: 1.3`
- `require_sma150_slope_bps_min: -1.0%` ⭐ **OPTIMIZED**

**Current Results:**
- 1h: 63/96 periods (65.6%) pass all dials
- 4h: 23/24 periods (95.8%) pass all dials
- 1d: ⏳ **PENDING**

**Next Action:** Complete 1d pipeline analysis
