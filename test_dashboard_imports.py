#!/usr/bin/env python3
"""
Test script to verify dashboard imports work correctly
"""
import sys
from pathlib import Path

# Add the dashboard directory to path
dashboard_dir = Path(__file__).parent / "src" / "dashboard"
sys.path.insert(0, str(dashboard_dir))

print("Testing dashboard imports...")

try:
    # Test patient_creator import
    from patient_creator import PatientCreator
    print("✅ PatientCreator imported successfully")
except ImportError as e:
    print(f"❌ PatientCreator import failed: {e}")

try:
    # Test ui_profile import
    from ui_profile import render_profile_controls, render_manual_enrichment_forms
    print("✅ ui_profile functions imported successfully")
except ImportError as e:
    print(f"❌ ui_profile import failed: {e}")

try:
    # Test ui_animation import
    from ui_animation import Storyboard, consume_events
    print("✅ ui_animation classes imported successfully")
except ImportError as e:
    print(f"❌ ui_animation import failed: {e}")

try:
    # Test gene_panel_selector import
    from gene_panel_selector import GenePanelSelector
    print("✅ GenePanelSelector imported successfully")
except ImportError as e:
    print(f"❌ GenePanelSelector import failed: {e}")

try:
    # Test alert_classifier import
    from alert_classifier import AlertClassifier
    print("✅ AlertClassifier imported successfully")
except ImportError as e:
    print(f"❌ AlertClassifier import failed: {e}")

print("\nImport test completed!")
