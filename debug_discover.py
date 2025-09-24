#!/usr/bin/env python3

import pandas as pd
import sys
import os
sys.path.append('.')

from coil_spring import discover_symbols

# Load 1h data
df_1h = pd.read_parquet('ohlcv_parquet/ohlcv_1h.parquet')

print('=== DEBUGGING DISCOVER_SYMBOLS ===')
print(f'1h data shape: {df_1h.shape}')
print(f'Unique symbols: {df_1h["symbol"].nunique()}')

# Test with CLI symbols
cli_symbols = ['GNSUSDT']
print(f'\\nTesting with CLI symbols: {cli_symbols}')

result = discover_symbols(df_1h, '.*', [], cli_symbols)
print(f'Result: {result}')
print(f'Result length: {len(result)}')

# Test without CLI symbols
print(f'\\nTesting without CLI symbols:')
result2 = discover_symbols(df_1h, '.*', [], None)
print(f'Result length: {len(result2)}')

# Check if GNSUSDT is in the data
gns_data = df_1h[df_1h['symbol'] == 'GNSUSDT']
print(f'\\nGNSUSDT data: {len(gns_data)} rows')
gns_in_symbols = "GNSUSDT" in df_1h["symbol"].unique()
print(f'GNSUSDT in unique symbols: {gns_in_symbols}')
