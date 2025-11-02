#!/usr/bin/env python3
"""
Simple test to verify Asian ethnicity split configuration
"""
import sys
from pathlib import Path

# Add src to path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

def test_patient_creator_config():
    """Test patient_creator.py ethnicity configuration"""
    print("Testing patient_creator.py Asian ethnicity split...\n")

    # Read the file and check for ethnicity options
    patient_creator_path = src_dir / "dashboard" / "patient_creator.py"
    with open(patient_creator_path, 'r') as f:
        content = f.read()

    # Check that split Asian categories are present
    asian_categories = ["South Asian", "East Asian", "Southeast Asian"]
    all_found = all(f'"{cat}"' in content for cat in asian_categories)

    # Check that generic "Asian" is NOT used as an option
    # (it might appear in comments or strings, but not as '"Asian",' in ethnicity_options)
    has_generic_asian = '"Asian",' in content or "'Asian'," in content

    print("Ethnicity options in patient_creator.py:")
    print("=" * 50)

    for cat in asian_categories:
        found = f'"{cat}"' in content
        status = "✅" if found else "❌"
        print(f"{status} {cat}")

    if has_generic_asian:
        # Check if it's in a comment or the actual ethnicity list
        lines = content.split('\n')
        in_ethnicity_list = False
        for i, line in enumerate(lines):
            if 'ethnicity_options = [' in line:
                in_ethnicity_list = True
            if in_ethnicity_list and ('"Asian"' in line or "'Asian'" in line):
                if not line.strip().startswith('#'):
                    print(f"\n❌ FAIL: Generic 'Asian' still in ethnicity_options at line {i+1}")
                    print(f"   Line: {line.strip()}")
                    return False
            if in_ethnicity_list and ']' in line:
                in_ethnicity_list = False

    if all_found:
        print("\n✅ SUCCESS: All Asian subcategories present in patient_creator.py")
        return True
    else:
        print("\n❌ FAIL: Some Asian subcategories missing")
        return False

def test_population_frequencies_config():
    """Test population_frequencies.py configuration"""
    print("\n\nTesting population_frequencies.py Asian ethnicity split...\n")

    try:
        from utils.population_frequencies import _category_template, _POPULATION_MAP

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

        # Check population map
        print("\n\nPopulation map (1000G/gnomAD -> our categories):")
        print("=" * 50)

        eas_mapped = _POPULATION_MAP.get("1000GENOMES:phase_3:EAS")
        sas_mapped = _POPULATION_MAP.get("1000GENOMES:phase_3:SAS")

        print(f"  EAS (East Asian) -> {eas_mapped}")
        print(f"  SAS (South Asian) -> {sas_mapped}")

        if eas_mapped != "East Asian" or sas_mapped != "South Asian":
            print("\n❌ FAIL: EAS/SAS not properly mapped to split categories")
            return False

        print("\n✅ SUCCESS: All split Asian categories present in frequency template")
        return True

    except Exception as e:
        print(f"\n❌ FAIL: Error loading population_frequencies: {e}")
        return False

def test_ai_photo_generator_config():
    """Test AI photo generator configuration"""
    print("\n\nTesting ai_photo_generator.py Asian ethnicity handling...\n")

    ai_gen_path = src_dir / "utils" / "ai_photo_generator.py"
    with open(ai_gen_path, 'r') as f:
        content = f.read()

    print("Checking ethnicity_map:")
    print("=" * 50)

    # Check for split Asian categories in ethnicity_map
    asian_categories = {
        "South Asian": "South Asian descent",
        "East Asian": "East Asian descent",
        "Southeast Asian": "Southeast Asian descent"
    }

    all_found = True
    for cat, desc_fragment in asian_categories.items():
        found = f"'{cat}'" in content or f'"{cat}"' in content
        status = "✅" if found else "❌"
        print(f"{status} {cat}")
        if not found:
            all_found = False

    # Check face_block logic
    print("\nChecking face_block logic:")
    print("=" * 50)

    face_block_checks = {
        "east asian": "'east asian' in ethn",
        "south asian": "'south asian' in ethn",
        "southeast asian": "'southeast asian' in ethn"
    }

    for cat, check in face_block_checks.items():
        found = check in content
        status = "✅" if found else "❌"
        print(f"{status} {cat}: {check}")
        if not found:
            all_found = False

    if all_found:
        print("\n✅ SUCCESS: AI photo generator handles all Asian subcategories")
        return True
    else:
        print("\n❌ FAIL: AI photo generator missing some Asian subcategories")
        return False

def test_dosing_adjustments_config():
    """Test dosing adjustments configuration"""
    print("\n\nTesting dosing_adjustments.py Asian ethnicity handling...\n")

    try:
        dosing_path = src_dir / "utils" / "dosing_adjustments.py"
        with open(dosing_path, 'r') as f:
            content = f.read()

        print("Checking for split Asian population handling:")
        print("=" * 50)

        # Check for East Asian specific handling (CYP2C19 is particularly important)
        has_east_asian = '"East Asian"' in content or "'East Asian'" in content
        has_south_asian = '"South Asian"' in content or "'South Asian'" in content
        has_southeast_asian = '"Southeast Asian"' in content or "'Southeast Asian'" in content

        print(f"{'✅' if has_east_asian else '❌'} East Asian")
        print(f"{'✅' if has_south_asian else '❌'} South Asian")
        print(f"{'✅' if has_southeast_asian else '❌'} Southeast Asian")

        # Check that generic "Asian" is not used in ethnicity checks
        # Look for patterns like: eth == "Asian"
        has_generic = 'eth == "Asian"' in content or "eth == 'Asian'" in content

        if has_generic:
            print('\n❌ FAIL: Generic eth == "Asian" still present')
            return False

        if has_east_asian and has_south_asian:
            print("\n✅ SUCCESS: Dosing adjustments use split Asian categories")
            return True
        else:
            print("\n❌ FAIL: Dosing adjustments missing Asian subcategories")
            return False

    except Exception as e:
        print(f"\n❌ FAIL: Error checking dosing_adjustments: {e}")
        return False

if __name__ == "__main__":
    print("=" * 70)
    print("ASIAN ETHNICITY SPLIT CONFIGURATION TEST")
    print("=" * 70)

    results = []

    results.append(("Patient Creator Config", test_patient_creator_config()))
    results.append(("Population Frequencies Config", test_population_frequencies_config()))
    results.append(("AI Photo Generator Config", test_ai_photo_generator_config()))
    results.append(("Dosing Adjustments Config", test_dosing_adjustments_config()))

    print("\n\n" + "=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:35s}: {status}")

    all_passed = all(result for _, result in results)

    print("=" * 70)

    if all_passed:
        print("\n🎉 ALL TESTS PASSED! Asian ethnicity split is working correctly.\n")
        sys.exit(0)
    else:
        print("\n⚠️  SOME TESTS FAILED. Please review the output above.\n")
        sys.exit(1)
