"""Test script to validate all imports work correctly"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    print("Testing imports...")
    
    # Test dashboard.utils.styling
    from dashboard.utils.styling import inject_css
    print("[OK] dashboard.utils.styling imported successfully")
    
    # Test dashboard.utils.mock_patient
    from dashboard.utils.mock_patient import generate_avatar, get_patient_initials
    print("[OK] dashboard.utils.mock_patient imported successfully")
    
    # Test utils.dynamic_clinical_generator (from src/utils)
    from utils.dynamic_clinical_generator import DynamicClinicalGenerator
    print("[OK] utils.dynamic_clinical_generator imported successfully")
    
    # Test patient creator imports
    from dashboard.patient_creator import PatientCreator
    print("[OK] PatientCreator imported successfully")
    
    # Test gene panel selector
    from dashboard.gene_panel_selector import GenePanelSelector
    print("[OK] GenePanelSelector imported successfully")
    
    # Test alert classifier
    from dashboard.alert_classifier import AlertClassifier
    print("[OK] AlertClassifier imported successfully")
    
    print("\n[SUCCESS] All imports successful!")
    
except ImportError as e:
    print("[ERROR] Import error:", str(e))
    import traceback
    traceback.print_exc()
except Exception as e:
    print("[ERROR] Error:", str(e))
    import traceback
    traceback.print_exc()
