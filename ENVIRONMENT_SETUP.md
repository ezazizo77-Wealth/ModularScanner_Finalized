# Environment Setup Guide

## 📦 Current Environment Snapshot

**Created:** September 20, 2025  
**Python Version:** 3.9 (system Python)  
**Location:** `/usr/bin/python3`  
**Dependencies:** 47 packages installed

## 🚀 How to Recreate This Environment

### Method 1: Direct Installation (Current Setup)
```bash
# Navigate to your project directory
cd /Users/aziz/Projects/ModularScanner_Finalized

# Install all dependencies from requirements.txt
pip3 install -r requirements.txt
```

### Method 2: Virtual Environment (Recommended)
```bash
# Navigate to your project directory
cd /Users/aziz/Projects/ModularScanner_Finalized

# Create a new virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install all dependencies
pip install -r requirements.txt

# Verify installation
pip list
```

### Method 3: Conda Environment
```bash
# Navigate to your project directory
cd /Users/aziz/Projects/ModularScanner_Finalized

# Create conda environment
conda create -n modular_scanner python=3.9

# Activate environment
conda activate modular_scanner

# Install dependencies
pip install -r requirements.txt
```

## 📋 Key Dependencies

### Core Data Processing
- **pandas==2.3.0** - Data manipulation
- **numpy==2.0.2** - Numerical computing
- **pyarrow==21.0.0** - Parquet file support

### Technical Analysis
- **ta==0.11.0** - Technical indicators
- **ccxt==4.4.95** - Cryptocurrency exchange API

### File I/O
- **openpyxl==3.1.5** - Excel file support
- **PyYAML==6.0.2** - YAML configuration files

### Visualization
- **matplotlib==3.9.4** - Plotting and charts

### Cryptocurrency
- **python-binance==1.0.29** - Binance API client

## 🔧 Environment Management Commands

### Check Current Environment
```bash
# Check Python version
python3 --version

# Check installed packages
pip3 list

# Check specific package
pip3 show pandas
```

### Update Dependencies
```bash
# Update requirements.txt
pip3 freeze > requirements.txt

# Update specific package
pip3 install --upgrade pandas

# Update all packages
pip3 list --outdated
```

### Troubleshooting
```bash
# Reinstall specific package
pip3 uninstall pandas
pip3 install pandas

# Check for conflicts
pip3 check

# Clear pip cache
pip3 cache purge
```

## 📁 Project Structure
```
ModularScanner_Finalized/
├── requirements.txt          # ← Dependencies snapshot
├── ENVIRONMENT_SETUP.md      # ← This guide
├── ma_slopes_scan.py         # ← Main scanner
├── coil_spring.py            # ← Coil scanner
├── ohlcv_parquet/            # ← Data files
│   ├── ohlcv_1h.parquet
│   ├── ohlcv_4h.parquet
│   └── ohlcv_1d.parquet
└── out/                      # ← Output files
```

## ⚠️ Important Notes

1. **System Python**: Currently using system Python (`/usr/bin/python3`)
2. **No Virtual Environment**: Dependencies installed globally
3. **macOS Specific**: Some packages are macOS-specific builds
4. **PyArrow Required**: Essential for parquet file reading

## 🎯 Quick Start Commands

### Test Environment
```bash
# Test data processing
python3 -c "import pandas as pd; print('Pandas OK')"

# Test parquet support
python3 -c "import pyarrow as pa; print('PyArrow OK')"

# Test technical analysis
python3 -c "import ta; print('TA OK')"
```

### Run Scanners
```bash
# MA Slopes Scanner
python3 ma_slopes_scan.py slopes_benchmark.yaml

# Coil Spring Scanner
python3 coil_spring.py --input-dir ./ohlcv_parquet --cfg coil_spring_benchmark.yaml
```

## 🔄 Future Environment Recreation

1. **Save this file** (`ENVIRONMENT_SETUP.md`)
2. **Keep requirements.txt** updated
3. **Use virtual environments** for new projects
4. **Test installation** with quick start commands

---
*Last updated: September 20, 2025*
