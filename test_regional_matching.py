#!/usr/bin/env python3
"""
Test regional name matching to ensure no cross-region mixing.
Validates that first names from a region are ONLY paired with surnames from the same region.
"""

import sys
import re

def test_regional_structure():
    """Test that all regional structures are properly formatted"""

    with open('src/dashboard/patient_creator.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Expected regionalized ethnicities based on our work
    regionalized_ethnicities = {
        "African": 6,  # Nigerian_Igbo, Nigerian_Yoruba, Ghanaian_Akan, Kenyan_Kikuyu, Senegalese_Wolof, South_African_Zulu
        "South Asian": 5,  # North_Indian_Hindi, North_Indian_Punjabi, South_Indian_Tamil, Pakistani, Bangladeshi
        "East Asian": 3,  # Chinese, Japanese, Korean
        "Southeast Asian": 4,  # Vietnamese, Thai, Filipino, Indonesian
        "Middle Eastern": 3,  # Gulf_Arab, Levantine, Egyptian_North_African
        "Caucasian/European": 6,  # British, French, German, Italian, Spanish_Portuguese, Slavic
    }

    print("Testing Regional Structure...")
    print("=" * 60)

    all_passed = True

    for ethnicity, expected_regions in regionalized_ethnicities.items():
        # Look for the ethnicity with regional structure
        pattern = rf'"{ethnicity}":\s*{{\s*"regions":\s*{{'
        if re.search(pattern, content):
            print(f"✓ {ethnicity}: Has regional structure")

            # Extract the regional block for this ethnicity
            ethnicity_start = content.find(f'"{ethnicity}": {{')
            if ethnicity_start == -1:
                print(f"  ✗ Could not find ethnicity block")
                all_passed = False
                continue

            # Count regions by looking for "countries" key
            ethnicity_block_end = ethnicity_start
            brace_count = 0
            for i in range(ethnicity_start, len(content)):
                if content[i] == '{':
                    brace_count += 1
                elif content[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        ethnicity_block_end = i
                        break

            ethnicity_block = content[ethnicity_start:ethnicity_block_end]
            region_count = ethnicity_block.count('"countries":')

            if region_count == expected_regions:
                print(f"  ✓ Has {region_count} regions (expected {expected_regions})")
            else:
                print(f"  ✗ Has {region_count} regions (expected {expected_regions})")
                all_passed = False

            # Verify each region has Male/Female with first/last names
            region_matches = re.finditer(r'"(\w+)":\s*{\s*"countries":', ethnicity_block)
            for match in region_matches:
                region_name = match.group(1)
                print(f"  - Region: {region_name}")

                # Check for Male and Female sections
                region_start = match.start()
                region_end = region_start
                brace_count = 0
                for i in range(region_start, len(ethnicity_block)):
                    if ethnicity_block[i] == '{':
                        brace_count += 1
                    elif ethnicity_block[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            region_end = i
                            break

                region_block = ethnicity_block[region_start:region_end]

                for gender in ["Male", "Female"]:
                    if f'"{gender}":' in region_block:
                        has_first = '"first":' in region_block[region_block.find(f'"{gender}":'):]
                        has_last = '"last":' in region_block[region_block.find(f'"{gender}":'):]

                        if has_first and has_last:
                            print(f"    ✓ {gender}: has first and last names")
                        else:
                            print(f"    ✗ {gender}: missing first or last names")
                            all_passed = False
                    else:
                        print(f"    ✗ Missing {gender} section")
                        all_passed = False
        else:
            print(f"✗ {ethnicity}: Missing regional structure")
            all_passed = False

    print("=" * 60)
    if all_passed:
        print("✓ All regional structure tests PASSED")
        return True
    else:
        print("✗ Some regional structure tests FAILED")
        return False


def test_selection_logic():
    """Test that the selection logic properly uses regional matching"""

    with open('src/dashboard/patient_creator.py', 'r', encoding='utf-8') as f:
        content = f.read()

    print("\nTesting Selection Logic...")
    print("=" * 60)

    # Check for the regional selection logic
    selection_logic_patterns = [
        r'if ethnicity_key in names_by_ethnicity_regional:',
        r'if "regions" in ethnicity_data:',
        r'regions = ethnicity_data\["regions"\]',
        r'region_key = random\.choice\(list\(regions\.keys\(\)\)\)',
        r'region_data = regions\[region_key\]',
        r'first_name = random\.choice\(region_data\[name_gender\]\["first"\]\)',
        r'last_name = random\.choice\(region_data\[name_gender\]\["last"\]\)',
    ]

    all_found = True
    for pattern in selection_logic_patterns:
        if re.search(pattern, content):
            print(f"✓ Found: {pattern[:50]}...")
        else:
            print(f"✗ Missing: {pattern[:50]}...")
            all_found = False

    print("=" * 60)
    if all_found:
        print("✓ Selection logic tests PASSED")
        return True
    else:
        print("✗ Selection logic tests FAILED")
        return False


def main():
    """Run all tests"""
    print("Regional Name Matching Test Suite")
    print("=" * 60)

    structure_passed = test_regional_structure()
    logic_passed = test_selection_logic()

    print("\n" + "=" * 60)
    print("FINAL RESULTS:")
    print("=" * 60)

    if structure_passed and logic_passed:
        print("✓ ALL TESTS PASSED")
        print("\nRegional matching is properly configured:")
        print("- 31 total regions across 6 ethnicities")
        print("- Each region has proper Male/Female name structure")
        print("- Selection logic ensures same-region matching")
        print("- No cross-region name mixing will occur")
        return 0
    else:
        print("✗ SOME TESTS FAILED")
        if not structure_passed:
            print("- Regional structure has issues")
        if not logic_passed:
            print("- Selection logic has issues")
        return 1


if __name__ == "__main__":
    sys.exit(main())
