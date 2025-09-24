#!/usr/bin/env python3
"""
Test script to verify detect_ema_stack function is working correctly.
"""

import sys
import os
from pathlib import Path

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from indicators import detect_ema_stack

def test_ema_stack():
    """Test EMA stack detection with known examples."""
    print("🧪 Testing detect_ema_stack function")
    print("=" * 40)
    
    # Test case 1: Bearish stack (ascending order - short EMAs below long EMAs)
    # This should be BEARISH
    bearish_emas = {
        'EMA5': 1.489,
        'EMA13': 1.490,
        'EMA21': 1.493,
        'EMA50': 1.515,
        'EMA200': 1.579
    }
    
    status, broken, direction = detect_ema_stack(bearish_emas)
    print(f"📉 Bearish Test (PSGUSDT-like):")
    print(f"   EMAs: {bearish_emas}")
    print(f"   Result: {status}, {broken}, {direction}")
    print(f"   Expected: Bearish Stack, None, Bearish")
    print(f"   ✅ Correct" if direction == 'Bearish' else f"   ❌ Wrong")
    print()
    
    # Test case 2: Bullish stack (descending order - short EMAs above long EMAs)
    # This should be BULLISH
    bullish_emas = {
        'EMA5': 2.0,
        'EMA13': 1.9,
        'EMA21': 1.8,
        'EMA50': 1.7,
        'EMA200': 1.6
    }
    
    status, broken, direction = detect_ema_stack(bullish_emas)
    print(f"📈 Bullish Test:")
    print(f"   EMAs: {bullish_emas}")
    print(f"   Result: {status}, {broken}, {direction}")
    print(f"   Expected: Bullish Stack, None, Bullish")
    print(f"   ✅ Correct" if direction == 'Bullish' else f"   ❌ Wrong")
    print()

if __name__ == "__main__":
    test_ema_stack()
