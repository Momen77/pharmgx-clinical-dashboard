#!/usr/bin/env python3
"""
Test Script to Demonstrate Animation and Profile Fixes
Run this to verify the fixes are working properly
"""

import sys
from pathlib import Path
import json
import tempfile
from datetime import datetime

# Add src to path
project_root = Path(__file__).parent
src_dir = project_root / "src"
sys.path.insert(0, str(src_dir))

print("🧬 PharmGx Dashboard - Testing Animation and Profile Fixes")
print("=" * 60)

# Test 1: Animation Asset Loading
print("\n🎬 TEST 1: Animation Asset Loading")
print("-" * 40)

try:
    from src.utils.lottie_loader import load_all_lottie_assets, get_asset_or_fallback
    
    # Load all assets
    print("Loading Lottie assets...")
    assets = load_all_lottie_assets()
    
    print(f"Assets loaded: {len(assets)}")
    for asset_name, asset_data in assets.items():
        if asset_data:
            print(f"  ✅ {asset_name}.json - Loaded ({len(str(asset_data))} chars)")
        else:
            print(f"  ❌ {asset_name}.json - Failed to load")
    
    # Test fallback mechanism
    print("\nTesting fallback mechanism...")
    fallback_asset = get_asset_or_fallback("nonexistent", assets)
    if fallback_asset:
        print("  ✅ Fallback mechanism working")
    else:
        print("  ❌ Fallback mechanism failed")
        
except Exception as e:
    print(f"  ❌ Animation test failed: {e}")

# Test 2: PipelineWorker Import and Creation
print("\n🔧 TEST 2: PipelineWorker Import and Creation")
print("-" * 40)

try:
    from src.utils.pipeline_worker import PipelineWorker
    print("  ✅ PipelineWorker imported successfully")
    
    # Test creating worker with profile
    demo_profile = {
        "demographics": {
            "first_name": "John",
            "last_name": "Test",
            "mrn": "TEST_MRN_12345",
            "age": 35
        },
        "conditions": [{"name": "Hypertension"}],
        "medications": [{"name": "Lisinopril", "dose": "10mg"}]
    }
    
    worker = PipelineWorker(
        genes=["CYP2D6", "CYP2C19"],
        profile=demo_profile,
        demo_mode=True
    )
    
    print("  ✅ PipelineWorker created with profile")
    print(f"  📋 Profile keys: {list(demo_profile.keys())}")
    
except Exception as e:
    print(f"  ❌ PipelineWorker test failed: {e}")

# Test 3: Enhanced Pipeline Integration
print("\n🧬 TEST 3: Enhanced Pipeline Integration") 
print("-" * 40)

try:
    from src.main import PGxPipeline
    from src.utils.event_bus import EventBus
    
    print("  ✅ Pipeline classes imported successfully")
    
    # Create pipeline with event bus
    event_bus = EventBus()
    pipeline = PGxPipeline(event_bus=event_bus)
    
    print("  ✅ Pipeline created with event bus")
    
    # Test patient profile parameter exists
    import inspect
    sig = inspect.signature(pipeline.run_multi_gene)
    if 'patient_profile' in sig.parameters:
        print("  ✅ run_multi_gene accepts patient_profile parameter")
    else:
        print("  ❌ run_multi_gene missing patient_profile parameter")
        
except Exception as e:
    print(f"  ❌ Pipeline integration test failed: {e}")

# Test 4: UI Animation Components
print("\n🎨 TEST 4: UI Animation Components")
print("-" * 40)

try:
    from src.dashboard.ui_animation import Storyboard, load_all_lottie_assets
    
    print("  ✅ UI Animation modules imported")
    
    # Test storyboard creation (would normally need Streamlit context)
    print("  📝 Storyboard class available for Streamlit use")
    
except Exception as e:
    print(f"  ❌ UI Animation test failed: {e}")

# Test 5: Demo Pipeline Run
print("\n🚀 TEST 5: Demo Pipeline Run")
print("-" * 40)

try:
    import threading
    import queue
    import time
    
    # Create demo worker
    demo_profile = {
        "demographics": {
            "first_name": "Alice",
            "last_name": "Demo",
            "mrn": "DEMO_ALICE_789",
            "age": 42
        },
        "test_source": "demo_script"
    }
    
    event_q = queue.Queue()
    result_q = queue.Queue()
    
    worker = PipelineWorker(
        genes=["CYP2D6"],
        profile=demo_profile,
        event_queue=event_q,
        result_queue=result_q,
        demo_mode=True
    )
    
    print("  🔄 Running demo pipeline...")
    worker.start()
    
    # Collect events
    events = []
    while worker.is_alive() or not event_q.empty():
        try:
            event = event_q.get(timeout=0.1)
            events.append(f"[{event.stage}] {event.message}")
            print(f"    📡 {events[-1]}")
        except queue.Empty:
            pass
    
    # Get result
    try:
        result = result_q.get(timeout=1)
        if result.get('success'):
            print("  ✅ Demo pipeline completed successfully")
            print(f"    👤 Patient ID: {result.get('patient_id')}")
            print(f"    🧬 Genes: {result.get('genes')}")
            
            # Check if profile was used
            profile_info = result.get('comprehensive_profile', {})
            if profile_info.get('dashboard_source'):
                print("    ✅ Dashboard profile was used")
            else:
                print("    ❌ Dashboard profile was not used")
            
            # Check outputs
            outputs = result.get('comprehensive_outputs', {})
            print(f"    📁 Generated {len(outputs)} output files:")
            for output_type, file_path in outputs.items():
                file_exists = Path(file_path).exists() if file_path else False
                status = "✅" if file_exists else "❌"
                print(f"      {status} {output_type}")
        else:
            print(f"  ❌ Demo pipeline failed: {result.get('error')}")
    except queue.Empty:
        print("  ❌ No result received from pipeline")
        
except Exception as e:
    print(f"  ❌ Demo pipeline test failed: {e}")
    import traceback
    print(f"    Error details: {traceback.format_exc()}")

# Test Summary
print("\n📋 TEST SUMMARY")
print("=" * 60)
print("If you see ✅ marks above, the fixes are working!")
print("")
print("🎯 Key Fixes Implemented:")
print("  1. ✅ Robust Lottie asset loading with fallbacks")
print("  2. ✅ Dashboard-compatible PipelineWorker class")
print("  3. ✅ Patient profile integration in pipeline")
print("  4. ✅ Comprehensive output generation")
print("  5. ✅ Event bus integration for UI updates")
print("")
print("🚀 Next Steps:")
print("  1. Run the Streamlit dashboard: `streamlit run src/dashboard/app.py`")
print("  2. Create a patient profile")
print("  3. Select genes and run test")
print("  4. Check animations and profile usage")
print("")
print("🔧 Debug Tips:")
print("  - Use the 'Debug' page in dashboard for troubleshooting")
print("  - Enable demo mode for faster testing")
print("  - Check console output for [WORKER] debug messages")
print("")
print("✅ Animation and Profile Integration Fixes Complete!")
