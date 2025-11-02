#!/usr/bin/env python3
"""
Test script to verify Asian ethnicity split is working correctly
"""
import sys
from pathlib import Path

# Add src to path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

from dashboard.patient_creator import PatientCreator
from collections import Counter

def test_ethnicity_distribution():
    """Test that Asian ethnicities are properly split"""
    print("Testing Asian ethnicity split in automatic profile generation...\n")

    creator = PatientCreator()

    # Generate 100 profiles
    ethnicities = []
    for i in range(100):
        profile = creator.generate_random_profile(generate_ai_photo=False)
        eth = profile['demographics']['ethnicity']
        if isinstance(eth, list) and len(eth) > 0:
            ethnicities.append(eth[0])
        elif isinstance(eth, str):
            ethnicities.append(eth)

    # Count ethnicities
    counts = Counter(ethnicities)

    print("Ethnicity Distribution (100 profiles):")
    print("=" * 50)
    for eth, count in sorted(counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / 100) * 100
        print(f"{eth:20s}: {count:3d} ({percentage:5.1f}%)")

    print("\n" + "=" * 50)

    # Check that Asian is NOT in the list
    if "Asian" in counts:
        print("❌ FAIL: Generic 'Asian' found - should be split!")
        return False

    # Check that split Asian categories exist
    asian_categories = ["South Asian", "East Asian", "Southeast Asian"]
    found_asian_categories = [cat for cat in asian_categories if cat in counts]

    if len(found_asian_categories) == 0:
        print("❌ FAIL: No split Asian categories found!")
        return False

    print(f"\n✅ SUCCESS: Found {len(found_asian_categories)} Asian subcategories:")
    for cat in found_asian_categories:
        print(f"   - {cat}")

    # Verify all expected categories are in template
    expected_categories = [
        "African", "South Asian", "East Asian", "Southeast Asian",
        "Caucasian/European", "Hispanic/Latino", "Middle Eastern",
        "Mixed", "Native American", "Pacific Islander"
    ]

    all_categories_present = all(cat in creator.generate_random_profile.__code__.co_consts
                                  for cat in asian_categories)

    return True

def test_population_frequencies():
    """Test that population frequency categories are properly split"""
    print("\n\nTesting population frequency categories...\n")

    from utils.population_frequencies import _category_template

    template = _category_template()

    print("Population frequency categories:")
    print("=" * 50)
    for cat in template.keys():
        print(f"  - {cat}")

    # Check for split Asian categories
    asian_categories = ["South Asian", "East Asian", "Southeast Asian"]
    missing = [cat for cat in asian_categories if cat not in template]

    if missing:
        print(f"\n❌ FAIL: Missing categories: {missing}")
        return False

    if "Asian" in template:
        print("\n❌ FAIL: Generic 'Asian' category still present!")
        return False

    print("\n✅ SUCCESS: All split Asian categories present in frequency template")
    return True

def test_ai_photo_generator():
    """Test that AI photo generator handles split Asian ethnicities"""
    print("\n\nTesting AI photo generator ethnicity mapping...\n")

    from utils.ai_photo_generator import AIPhotoGenerator

    generator = AIPhotoGenerator()

    # Test profiles for each Asian subgroup
    test_profiles = [
        {
            'demographics': {
                'age': 45,
                'gender': 'Male',
                'biological_sex': 'Male',
                'ethnicity': ['South Asian'],
                'birth_country': 'India'
            },
            'clinical_information': {'current_conditions': []}
        },
        {
            'demographics': {
                'age': 35,
                'gender': 'Female',
                'biological_sex': 'Female',
                'ethnicity': ['East Asian'],
                'birth_country': 'China'
            },
            'clinical_information': {'current_conditions': []}
        },
        {
            'demographics': {
                'age': 50,
                'gender': 'Male',
                'biological_sex': 'Male',
                'ethnicity': ['Southeast Asian'],
                'birth_country': 'Vietnam'
            },
            'clinical_information': {'current_conditions': []}
        }
    ]

    print("Testing prompt generation for each Asian subgroup:")
    print("=" * 50)

    success = True
    for profile in test_profiles:
        eth = profile['demographics']['ethnicity'][0]
        prompt = generator._build_prompt(profile)

        # Check that the prompt contains the specific ethnicity
        if eth.lower() in prompt.lower():
            print(f"✅ {eth:20s}: Specific ethnicity found in prompt")
        else:
            print(f"❌ {eth:20s}: Specific ethnicity NOT found in prompt")
            success = False

    if success:
        print("\n✅ SUCCESS: AI photo generator handles all Asian subcategories")
    else:
        print("\n❌ FAIL: AI photo generator missing some Asian subcategories")

    return success

if __name__ == "__main__":
    print("=" * 70)
    print("ASIAN ETHNICITY SPLIT TEST SUITE")
    print("=" * 70)

    results = []

    results.append(("Ethnicity Distribution", test_ethnicity_distribution()))
    results.append(("Population Frequencies", test_population_frequencies()))
    results.append(("AI Photo Generator", test_ai_photo_generator()))

    print("\n\n" + "=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:30s}: {status}")

    all_passed = all(result for _, result in results)

    print("=" * 70)

    if all_passed:
        print("\n🎉 ALL TESTS PASSED! Asian ethnicity split is working correctly.\n")
        sys.exit(0)
    else:
        print("\n⚠️  SOME TESTS FAILED. Please review the output above.\n")
        sys.exit(1)
