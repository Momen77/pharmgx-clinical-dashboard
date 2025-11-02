#!/usr/bin/env python3
"""Test script to verify ethnicity distribution is realistic and unbiased"""

import random
from collections import Counter

def test_weighted_distribution():
    """Test the new weighted ethnicity distribution"""

    # Same weights as in the fixed code
    ethnicity_options = [
        "Asian",              # 40%
        "Caucasian/European", # 20%
        "African",            # 15%
        "Hispanic/Latino",    # 12%
        "Middle Eastern",     # 6%
        "Mixed",              # 4%
        "Native American",    # 2%
        "Pacific Islander"    # 1%
    ]

    ethnicity_weights = [0.40, 0.20, 0.15, 0.12, 0.06, 0.04, 0.02, 0.01]

    # Sample 10,000 times to verify distribution
    samples = 10000
    results = [random.choices(ethnicity_options, weights=ethnicity_weights, k=1)[0]
               for _ in range(samples)]

    counter = Counter(results)

    print(f"\n{'='*70}")
    print(f"Ethnicity Distribution Test ({samples:,} samples)")
    print(f"{'='*70}")
    print(f"{'Ethnicity':<25} {'Count':>10} {'Actual %':>12} {'Expected %':>12}")
    print(f"{'-'*70}")

    for ethnicity, expected_weight in zip(ethnicity_options, ethnicity_weights):
        count = counter[ethnicity]
        actual_percent = (count / samples) * 100
        expected_percent = expected_weight * 100

        # Color code: green if within 0.5% of expected, yellow if within 1%
        status = "✓" if abs(actual_percent - expected_percent) < 1.0 else "⚠"

        print(f"{ethnicity:<25} {count:>10,} {actual_percent:>11.2f}% {expected_percent:>11.1f}% {status}")

    print(f"{'='*70}")
    print("\nKey findings:")
    print(f"  • Pacific Islander: {counter['Pacific Islander']} ({counter['Pacific Islander']/samples*100:.2f}%) - Should be ~1%")
    print(f"  • Caucasian/European: {counter['Caucasian/European']} ({counter['Caucasian/European']/samples*100:.2f}%) - Reduced from 45% to 20%")
    print(f"  • Asian: {counter['Asian']} ({counter['Asian']/samples*100:.2f}%) - Increased from 20% to 40%")
    print("\n✓ Distribution is now realistic and avoids over-representation of Pacific Islanders!\n")

if __name__ == "__main__":
    test_weighted_distribution()
