"""
Patient profile creator with comprehensive demographics form
"""
import streamlit as st
from datetime import datetime, timedelta
import random
from pathlib import Path
import sys

# Add paths for module resolution
dashboard_dir = Path(__file__).parent
src_dir = dashboard_dir.parent
sys.path.insert(0, str(dashboard_dir))
sys.path.insert(0, str(src_dir))

# Import from dashboard.utils for mock_patient
try:
    from dashboard.utils.mock_patient import generate_avatar, get_patient_initials, save_avatar_to_bytes
except ImportError:
    # Fallback: try relative import
    from .utils.mock_patient import generate_avatar, get_patient_initials, save_avatar_to_bytes

# Import from src.utils for dynamic_clinical_generator (this is in the parent utils directory)
try:
    from utils.dynamic_clinical_generator import DynamicClinicalGenerator
except ImportError:
    # Fallback: direct import
    import importlib.util
    utils_path = src_dir.parent / "utils" / "dynamic_clinical_generator.py"
    if utils_path.exists():
        spec = importlib.util.spec_from_file_location("dynamic_clinical_generator", utils_path)
        gen_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gen_module)
        DynamicClinicalGenerator = gen_module.DynamicClinicalGenerator
    else:
        # Define a minimal fallback
        class DynamicClinicalGenerator:
            def __init__(self, bioportal_api_key=None):
                pass


class PatientCreator:
    """Creates virtual patient profiles for PGx testing"""
    
    def __init__(self, bioportal_api_key: str = None):
        """Initialize patient creator"""
        self.clinical_generator = DynamicClinicalGenerator(bioportal_api_key=bioportal_api_key)
    
    def render_patient_form(self):
        """Render comprehensive patient demographics form"""
        st.header("📋 Create Patient Profile")
        
        with st.form("patient_form"):
            col1, col2 = st.columns(2)
            
            # Basic Information
            with col1:
                first_name = st.text_input("First Name *", value="")
                middle_name = st.text_input("Middle Name", value="")
                last_name = st.text_input("Last Name *", value="")
                preferred_name = st.text_input("Preferred Name", value="")
            
            with col2:
                date_of_birth = st.date_input(
                    "Date of Birth *",
                    value=datetime.now() - timedelta(days=365*45),
                    max_value=datetime.now()
                )
                age = (datetime.now().date() - date_of_birth).days // 365
                st.info(f"Age: {age} years")
                
                gender = st.selectbox(
                    "Gender *",
                    ["Male", "Female", "Other", "Prefer not to say"]
                )
                
                biological_sex = st.selectbox(
                    "Biological Sex at Birth (for clinical purposes)",
                    ["Male", "Female"],
                    index=0 if gender in ["Male", "Other"] else 1
                )
            
            # Ethnicity
            st.subheader("Ethnicity & Race")
            ethnicity_options = [
                "African", "Asian", "Caucasian/European", "Hispanic/Latino",
                "Middle Eastern", "Native American", "Pacific Islander", "Mixed", "Other"
            ]
            ethnicity = st.multiselect(
                "Select Ethnicity/Race (important for PGx variant frequencies)",
                ethnicity_options
            )
            
            # Birthplace and Location
            col1, col2 = st.columns(2)
            with col1:
                birth_city = st.text_input("Birth City", value="")
                birth_country = st.text_input("Birth Country", value="Belgium")
            with col2:
                current_city = st.text_input("Current City", value="Ghent")
                current_country = st.text_input("Current Country", value="Belgium")
            
            address = st.text_input("Street Address", value="")
            postal_code = st.text_input("Postal Code", value="")
            
            # Contact Information
            st.subheader("Contact Information")
            col1, col2 = st.columns(2)
            with col1:
                phone = st.text_input("Phone Number", value="")
                email = st.text_input("Email", value="")
            with col2:
                emergency_contact = st.text_input("Emergency Contact Name", value="")
                emergency_phone = st.text_input("Emergency Contact Phone", value="")
            
            # Physical Measurements
            st.subheader("Physical Measurements")
            col1, col2, col3 = st.columns(3)
            with col1:
                weight_unit = st.radio("Weight Unit", ["kg", "lbs"], horizontal=True)
                weight = st.number_input(f"Weight ({weight_unit})", min_value=0.0, value=70.0, step=0.1)
            with col2:
                height_unit = st.radio("Height Unit", ["cm", "inches"], horizontal=True)
                height = st.number_input(f"Height ({height_unit})", min_value=0.0, value=170.0, step=0.1)
            with col3:
                # Calculate BMI
                if weight_unit == "lbs":
                    weight_kg = weight * 0.453592
                else:
                    weight_kg = weight
                
                if height_unit == "inches":
                    height_m = height * 0.0254
                else:
                    height_m = height / 100
                
                bmi = weight_kg / (height_m ** 2) if height_m > 0 else 0
                st.metric("BMI", f"{bmi:.1f}")
            
            # Medical Record Number
            col1, col2 = st.columns(2)
            with col1:
                mrn_auto = st.checkbox("Auto-generate MRN", value=True)
                mrn = st.text_input("Medical Record Number (MRN)", 
                                   value=f"MRN-{datetime.now().strftime('%Y%m%d%H%M%S')}" if mrn_auto else "")
            with col2:
                language = st.selectbox("Primary Language", 
                                       ["English", "Dutch", "French", "German", "Spanish", "Other"])
                interpreter_needed = st.checkbox("Interpreter needed", value=False)
            
            # Insurance (Optional)
            st.subheader("Insurance Information (Optional)")
            col1, col2 = st.columns(2)
            with col1:
                insurance_provider = st.text_input("Insurance Provider", value="")
            with col2:
                insurance_policy = st.text_input("Policy Number", value="")
            
            # Primary Care Physician
            pcp_name = st.text_input("Primary Care Physician Name", value="")
            pcp_contact = st.text_input("PCP Contact", value="")
            
            # Patient Photo
            st.subheader("Patient Photo")
            photo_option = st.radio("Photo Option", ["Generate Avatar", "Upload Photo"], horizontal=True)
            
            patient_photo = None
            if photo_option == "Generate Avatar":
                initials = get_patient_initials(first_name, last_name)
                avatar = generate_avatar(initials, size=(200, 200))
                patient_photo = save_avatar_to_bytes(avatar)
                st.image(patient_photo, width=200, caption=f"Avatar: {initials}")
            else:
                uploaded_file = st.file_uploader("Upload Patient Photo", type=['png', 'jpg', 'jpeg'])
                if uploaded_file:
                    patient_photo = uploaded_file.read()
                    st.image(uploaded_file, width=200)
            
            # Submit button
            submitted = st.form_submit_button("✅ Create Patient Profile", type="primary", use_container_width=True)
            
            if submitted:
                if not first_name or not last_name:
                    st.error("Please fill in required fields (First Name, Last Name)")
                    return None
                
                # Create patient profile
                patient_profile = {
                    "demographics": {
                        "first_name": first_name,
                        "middle_name": middle_name,
                        "last_name": last_name,
                        "preferred_name": preferred_name or first_name,
                        "date_of_birth": date_of_birth.isoformat(),
                        "age": age,
                        "gender": gender,
                        "biological_sex": biological_sex,
                        "ethnicity": ethnicity,
                        "birthplace": {
                            "city": birth_city,
                            "country": birth_country
                        },
                        "current_location": {
                            "address": address,
                            "city": current_city,
                            "country": current_country,
                            "postal_code": postal_code
                        },
                        "contact": {
                            "phone": phone,
                            "email": email,
                            "emergency_contact": emergency_contact,
                            "emergency_phone": emergency_phone
                        },
                        "physical_measurements": {
                            "weight": weight,
                            "weight_unit": weight_unit,
                            "height": height,
                            "height_unit": height_unit,
                            "bmi": round(bmi, 1)
                        },
                        "mrn": mrn,
                        "language": language,
                        "interpreter_needed": interpreter_needed,
                        "insurance": {
                            "provider": insurance_provider,
                            "policy_number": insurance_policy
                        },
                        "pcp": {
                            "name": pcp_name,
                            "contact": pcp_contact
                        }
                    },
                    "photo": patient_photo,
                    "photo_format": "avatar" if photo_option == "Generate Avatar" else "upload",
                    "created_at": datetime.now().isoformat()
                }
                
                # Generate additional clinical data
                with st.spinner("Generating clinical information..."):
                    try:
                        # Generate lifestyle factors
                        lifestyle = self._generate_lifestyle()
                        patient_profile["lifestyle"] = lifestyle
                        
                        # Generate organ function
                        organ_function = self._generate_organ_function()
                        patient_profile["organ_function"] = organ_function
                        
                        # Get conditions and medications (simplified for now)
                        patient_profile["conditions"] = []
                        patient_profile["medications"] = []
                        
                    except Exception as e:
                        st.warning(f"Could not generate all clinical data: {e}")
                
                # Store in session state
                st.session_state['patient_profile'] = patient_profile
                st.session_state['patient_created'] = True
                
                st.success(f"✅ Patient profile created: {first_name} {last_name} (MRN: {mrn})")
                return patient_profile
        
        return None
    
    def _generate_lifestyle(self):
        """Generate lifestyle factors"""
        return {
            "smoking": random.choice(["Never", "Former", "Current"]),
            "alcohol": random.choice(["None", "Occasional", "Regular"]),
            "grapefruit_consumption": random.choice(["None", "Occasional", "Regular"]),
            "exercise_frequency": random.choice(["None", "Low", "Moderate", "High"])
        }
    
    def _generate_organ_function(self):
        """Generate organ function test results"""
        return {
            "kidney": {
                "creatinine_clearance": round(random.uniform(60, 120), 1),
                "egfr": round(random.uniform(60, 120), 1),
                "serum_creatinine": round(random.uniform(0.6, 1.2), 2)
            },
            "liver": {
                "alt": round(random.uniform(10, 50), 0),
                "ast": round(random.uniform(15, 40), 0),
                "bilirubin": round(random.uniform(0.3, 1.0), 2)
            },
            "test_date": (datetime.now() - timedelta(days=random.randint(1, 90))).isoformat()
        }
