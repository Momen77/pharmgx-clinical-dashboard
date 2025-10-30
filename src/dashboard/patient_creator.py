"""
Patient profile creator with comprehensive demographics form
"""
import streamlit as st
import os
from datetime import datetime, timedelta, date
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
    utils_path = src_dir / "utils" / "dynamic_clinical_generator.py"
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
        # Patient Picture: show final photo at top if already available; otherwise show picker
        patient_photo_top = None
        photo_option_top = None
        existing_profile = st.session_state.get('patient_profile')
        if existing_profile and existing_profile.get('photo'):
            photo_bytes_top = existing_profile.get('photo')
            photo_format_top = existing_profile.get('photo_format', 'unknown')
            caption_top = "Patient picture" if photo_format_top in ('captured', 'upload', 'ai_generated') else "Placeholder picture"
            st.image(photo_bytes_top, width=220, caption=caption_top)
            # Show name if present
            demo_ss = existing_profile.get('demographics', {})
            fn_ss = demo_ss.get('first_name', '')
            ln_ss = demo_ss.get('last_name', '')
            if fn_ss or ln_ss:
                st.subheader(f"{fn_ss} {ln_ss}".strip())
        else:
            st.subheader("📸 Patient Picture")
            photo_option_top = st.radio("Picture Option", ["Take patient picture", "Upload picture", "No picture"], horizontal=True, key="photo_option_top")
            if photo_option_top == "No picture":
                st.info("👤 A placeholder will be created from initials after submission")
            elif photo_option_top == "Upload picture":
                uploaded_file_top = st.file_uploader("Upload picture", type=['png', 'jpg', 'jpeg'], key="upload_picture_top")
                if uploaded_file_top:
                    patient_photo_top = uploaded_file_top.read()
                    st.image(uploaded_file_top, width=200)
            else:
                st.info("📷 The patient's picture will be taken automatically based on the details you provide")

        # Basic Information (top section)
        st.subheader("Basic Information")
        col_name1, col_name2 = st.columns(2)
        with col_name1:
            first_name = st.text_input("First Name *", value="", key="first_name_top")
            middle_name = st.text_input("Middle Name", value="", key="middle_name_top")
        with col_name2:
            last_name = st.text_input("Last Name *", value="", key="last_name_top")
            preferred_name = st.text_input("Preferred Name", value="", key="preferred_name_top")

        # Compact live DOB/Age and Measurements panel
        with st.container(border=True):
            col_dob, col_gap, col_meas = st.columns([2, 0.2, 3])
            with col_dob:
                dob_default = date.today() - timedelta(days=365*45)
                date_of_birth = st.date_input(
                    "Date of Birth",
                    value=dob_default,
                    min_value=date(1900, 1, 1),
                    max_value=date.today()
                )
                age = (date.today() - date_of_birth).days // 365
                st.caption(f"Age: {age} years")
            with col_meas:
                col_w, col_h, col_bmi = st.columns([1.2, 1.2, 1])
                with col_w:
                    weight_unit = st.radio("Weight Unit", ["kg", "lbs"], horizontal=True, key="weight_unit_live")
                    weight = st.number_input(f"Weight ({weight_unit})", min_value=0.0, value=70.0, step=0.1, key="weight_live")
                with col_h:
                    height_unit = st.radio("Height Unit", ["cm", "inches"], horizontal=True, key="height_unit_live")
                    height = st.number_input(f"Height ({height_unit})", min_value=0.0, value=170.0, step=0.1, key="height_live")
                with col_bmi:
                    # Calculate live BMI preview in standard units
                    weight_kg_preview = weight * 0.453592 if weight_unit == "lbs" else weight
                    height_m_preview = (height * 0.0254) if height_unit == "inches" else (height / 100 if height > 0 else 0)
                    bmi_preview = (weight_kg_preview / (height_m_preview ** 2)) if height_m_preview > 0 else 0.0
                    st.metric("BMI", f"{bmi_preview:.1f}")

        with st.form("patient_form"):
            # Picture option and preview are handled above; bind their values here
            photo_option = photo_option_top
            patient_photo = patient_photo_top

            st.divider()

            # Additional identity details (no empty columns; align inputs left)
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                gender = st.selectbox(
                    "Gender *",
                    ["Male", "Female", "Other", "Prefer not to say"]
                )
            with col_g2:
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
            
            # Physical measurements are selected above for live BMI; values will be used on submit
            
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

            # Generate avatar if needed (moved from later in form)
            if photo_option == "No picture" and not patient_photo:
                # Will generate after we have the name
                pass

            # Submit button
            submitted = st.form_submit_button("✅ Create Patient Profile", type="primary", width='stretch')
            
            if submitted:
                if not first_name or not last_name:
                    st.error("Please fill in required fields (First Name, Last Name)")
                    return None

                # Generate avatar if option selected
                if photo_option == "No picture" and not patient_photo:
                    initials = get_patient_initials(first_name, last_name)
                    avatar = generate_avatar(initials, size=(200, 200))
                    patient_photo = save_avatar_to_bytes(avatar)

                # Create patient profile with proper structure
                # Convert weight and height to standard units for clinical use
                if weight_unit == "lbs":
                    weight_kg = weight * 0.453592
                else:
                    weight_kg = weight
                
                if height_unit == "inches":
                    height_cm = height * 2.54
                else:
                    height_cm = height
                # Calculate BMI for submission
                bmi = (weight_kg / ((height_cm / 100) ** 2)) if height_cm > 0 else 0
                
                # Map gender to schema.org format
                gender_uri = f"http://schema.org/{gender}" if gender in ["Male", "Female"] else "http://schema.org/Male"

                # Use MRN directly as identifier (no transformation needed)
                patient_id = mrn

                patient_profile = {
                    "patient_id": patient_id,
                    "identifier": mrn,  # Use MRN as primary identifier
                    "mrn": mrn,  # Keep explicit MRN field too
                    "dashboard_source": True,  # Flag to indicate this came from dashboard
                    "created_at": datetime.now().isoformat(),
                    "photo": patient_photo,
                    "photo_format": "avatar" if photo_option == "No picture" else ("upload" if photo_option == "Upload picture" else "none"),
                    
                    # Clinical information (structure matches auto-generated profiles)
                    "clinical_information": {
                        "demographics": {
                            "@id": "http://ugent.be/person/demographics",
                            "foaf:firstName": first_name,
                            "foaf:familyName": last_name,
                            "schema:givenName": first_name,
                            "schema:familyName": last_name,
                            "schema:additionalName": middle_name,
                            "preferredName": preferred_name or first_name,
                            "schema:birthDate": date_of_birth.isoformat(),
                            "age": age,
                            "schema:gender": gender_uri,
                            "biological_sex": biological_sex,
                            "ethnicity": ethnicity,
                            "schema:birthPlace": {
                                "gn:name": birth_city,
                                "country": birth_country
                            },
                            "schema:weight": {
                                "@type": "schema:QuantitativeValue",
                                "schema:value": round(weight_kg, 1),
                                "schema:unitCode": "kg",
                                "schema:unitText": "kilograms",
                                "original_value": weight,
                                "original_unit": weight_unit
                            },
                            "schema:height": {
                                "@type": "schema:QuantitativeValue",
                                "schema:value": round(height_cm, 1),
                                "schema:unitCode": "cm",
                                "schema:unitText": "centimeters",
                                "original_value": height,
                                "original_unit": height_unit
                            },
                            "bmi": round(bmi, 1),
                            "mrn": mrn,
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
                            "language": language,
                            "interpreter_needed": interpreter_needed,
                            "insurance": {
                                "provider": insurance_provider,
                                "policy_number": insurance_policy
                            },
                            "pcp": {
                                "name": pcp_name,
                                "contact": pcp_contact
                            },
                            "note": "Patient profile created via dashboard"
                        },
                        "current_conditions": [],  # Will be populated below
                        "current_medications": [],  # Will be populated below
                        "organ_function": {},  # Will be populated below
                        "lifestyle_factors": {}  # Will be populated below
                    }
                }
                
                # Generate additional clinical data
                with st.spinner("Generating clinical information..."):
                    try:
                        # Generate lifestyle factors
                        lifestyle = self._generate_lifestyle()
                        patient_profile["clinical_information"]["lifestyle_factors"] = lifestyle
                        
                        # Generate organ function
                        organ_function = self._generate_organ_function()
                        patient_profile["clinical_information"]["organ_function"] = organ_function
                        
                        # Try to use DynamicClinicalGenerator for conditions and medications
                        if hasattr(self.clinical_generator, 'get_conditions_by_age_lifestyle'):
                            conditions = self.clinical_generator.get_conditions_by_age_lifestyle(age, lifestyle)
                            patient_profile["clinical_information"]["current_conditions"] = conditions
                            
                            # Get medications for conditions
                            medications = []
                            for condition in conditions:
                                snomed_code = condition.get("snomed:code")
                                condition_label = condition.get("rdfs:label", "")
                                if snomed_code:
                                    condition_meds = self.clinical_generator.get_drugs_for_condition(snomed_code, condition_label)
                                    medications.extend(condition_meds)
                            patient_profile["clinical_information"]["current_medications"] = medications
                        else:
                            # Fallback if DynamicClinicalGenerator not available
                            patient_profile["clinical_information"]["current_conditions"] = []
                            patient_profile["clinical_information"]["current_medications"] = []
                        
                    except Exception as e:
                        st.warning(f"Could not generate all clinical data: {e}")
                        # Ensure fields exist even if generation fails
                        patient_profile["clinical_information"].setdefault("current_conditions", [])
                        patient_profile["clinical_information"].setdefault("current_medications", [])
                
                # Add top-level demographics shortcut for compatibility with gene_panel_selector and other components
                # These components expect patient_profile['demographics']['first_name'] format
                patient_profile['demographics'] = {
                    'first_name': first_name,
                    'last_name': last_name,
                    'middle_name': middle_name,
                    'preferred_name': preferred_name or first_name,
                    'mrn': mrn,
                    'age': age,
                    'gender': gender,
                    'biological_sex': biological_sex,
                    'date_of_birth': date_of_birth.isoformat(),
                    'ethnicity': ethnicity,
                    'birth_city': birth_city,
                    'birth_country': birth_country
                }

                # Take patient picture (runs image generation under the hood)
                if photo_option == "Take patient picture":
                    try:
                        import sys
                        from pathlib import Path
                        sys.path.append(str(Path(__file__).parent.parent))
                        from utils.ai_photo_generator import AIPhotoGenerator

                        with st.spinner("📷 Taking patient picture..."):
                            # Load key from Streamlit secrets if available
                            # Prefer top-level, fallback to [api_keys] section
                            gemini_key = None
                            if "GOOGLE_API_KEY" in st.secrets:
                                gemini_key = st.secrets["GOOGLE_API_KEY"]
                            elif "api_keys" in st.secrets and "GOOGLE_API_KEY" in st.secrets["api_keys"]:
                                gemini_key = st.secrets["api_keys"]["GOOGLE_API_KEY"]
                            # Debug: surface detection info
                            try:
                                import sys as _sys
                                key_preview = (gemini_key[:6] + "…" + gemini_key[-4:]) if gemini_key else "<none>"
                                st.caption(f"Gemini key detected: {bool(gemini_key)} ({key_preview}); Python: {_sys.executable}")
                            except Exception:
                                pass
                            if not gemini_key:
                                st.error("GOOGLE_API_KEY not found in secrets. Add it in Streamlit Secrets or .streamlit/secrets.toml")
                                generator = AIPhotoGenerator()
                            else:
                                # Check required package
                                try:
                                    from google.genai import Client  # type: ignore
                                except Exception:
                                    st.error("Missing dependency: google-genai. Install with: pip install google-genai")
                                os.environ.setdefault("GOOGLE_API_KEY", gemini_key)  # for any downstream usage
                                generator = AIPhotoGenerator(api_key=gemini_key, service="gemini")
                            photo_bytes = generator.generate_patient_photo(patient_profile)

                            if photo_bytes:
                                patient_profile['photo'] = photo_bytes
                                patient_profile['photo_format'] = 'captured'
                                st.success("✅ Patient picture captured")
                            else:
                                if hasattr(generator, 'last_error') and generator.last_error:
                                    st.error(f"Picture capture error: {generator.last_error}")
                                # Fallback to avatar
                                initials = get_patient_initials(first_name, last_name)
                                avatar = generate_avatar(initials, size=(200, 200))
                                patient_profile['photo'] = save_avatar_to_bytes(avatar)
                                patient_profile['photo_format'] = 'avatar'
                                st.warning("⚠️ Using placeholder picture")
                    except Exception as e:
                        st.error(f"⚠️ Picture capture error: {e}")
                        # Fallback to avatar
                        initials = get_patient_initials(first_name, last_name)
                        avatar = generate_avatar(initials, size=(200, 200))
                        patient_profile['photo'] = save_avatar_to_bytes(avatar)
                        patient_profile['photo_format'] = 'avatar'

                # Store in session state and rerun to refresh top picture area
                st.session_state['patient_profile'] = patient_profile
                st.session_state['patient_created'] = True

                st.success(f"✅ Patient profile created: {first_name} {last_name} (MRN: {mrn})")
                st.rerun()

                # Show picture at the top with the patient's name underneath
                if patient_profile.get('photo'):
                    photo_format = patient_profile.get('photo_format', 'unknown')
                    caption = "Patient picture" if photo_format in ('captured', 'upload', 'ai_generated') else "Placeholder picture"
                    st.image(patient_profile['photo'], width=220, caption=caption)
                st.subheader(f"{first_name} {last_name}")

                return patient_profile

        return None

    def generate_random_profile(self, generate_ai_photo: bool = True):
        """Generate a random patient profile for testing

        Args:
            generate_ai_photo: Whether to generate AI photo (requires API key)
        """
        import random
        from datetime import datetime, timedelta

        # Random names
        first_names = ["John", "Jane", "Michael", "Sarah", "David", "Emma", "James", "Olivia", "Robert", "Sophia"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Martinez", "Anderson"]

        first_name = random.choice(first_names)
        last_name = random.choice(last_names)

        # Random demographics
        age = random.randint(25, 75)
        date_of_birth = datetime.now() - timedelta(days=365*age)
        gender = random.choice(["Male", "Female"])
        biological_sex = gender
        ethnicity = [random.choice(["African", "Asian", "Caucasian/European", "Hispanic/Latino", "Mixed"])]

        # Random MRN
        mrn = f"MRN-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Random measurements
        if gender == "Male":
            height_cm = random.uniform(165, 190)
            weight_kg = random.uniform(65, 95)
        else:
            height_cm = random.uniform(155, 175)
            weight_kg = random.uniform(50, 80)

        bmi = weight_kg / ((height_cm / 100) ** 2)
        gender_uri = f"http://schema.org/{gender}"

        # Use MRN directly as ID
        patient_id = mrn

        patient_profile = {
            "patient_id": patient_id,
            "identifier": mrn,
            "mrn": mrn,
            "dashboard_source": True,
            "created_at": datetime.now().isoformat(),
            "photo": None,
            "photo_format": "none",

            "clinical_information": {
                "demographics": {
                    "@id": "http://ugent.be/person/demographics",
                    "foaf:firstName": first_name,
                    "foaf:familyName": last_name,
                    "schema:givenName": first_name,
                    "schema:familyName": last_name,
                    "preferredName": first_name,
                    "schema:birthDate": date_of_birth.isoformat(),
                    "age": age,
                    "schema:gender": gender_uri,
                    "biological_sex": biological_sex,
                    "ethnicity": ethnicity,
                    "schema:weight": {
                        "@type": "schema:QuantitativeValue",
                        "schema:value": round(weight_kg, 1),
                        "schema:unitCode": "kg",
                        "schema:unitText": "kilograms"
                    },
                    "schema:height": {
                        "@type": "schema:QuantitativeValue",
                        "schema:value": round(height_cm, 1),
                        "schema:unitCode": "cm",
                        "schema:unitText": "centimeters"
                    },
                    "bmi": round(bmi, 1),
                    "mrn": mrn,
                    "note": "Auto-generated patient profile for testing"
                },
                "current_conditions": [],
                "current_medications": [],
                "organ_function": {},
                "lifestyle_factors": {}
            }
        }

        # Generate lifestyle factors
        lifestyle = self._generate_lifestyle()
        patient_profile["clinical_information"]["lifestyle_factors"] = lifestyle

        # Generate organ function
        organ_function = self._generate_organ_function()
        patient_profile["clinical_information"]["organ_function"] = organ_function

        # Try to generate conditions and medications
        try:
            if hasattr(self.clinical_generator, 'get_conditions_by_age_lifestyle'):
                conditions = self.clinical_generator.get_conditions_by_age_lifestyle(age, lifestyle)
                patient_profile["clinical_information"]["current_conditions"] = conditions

                # Get medications for conditions
                medications = []
                for condition in conditions:
                    snomed_code = condition.get("snomed:code")
                    condition_label = condition.get("rdfs:label", "")
                    if snomed_code:
                        condition_meds = self.clinical_generator.get_drugs_for_condition(snomed_code, condition_label)
                        medications.extend(condition_meds)
                patient_profile["clinical_information"]["current_medications"] = medications
        except Exception as e:
            # If generation fails, just use empty lists
            pass

        # Add top-level demographics shortcut
        patient_profile['demographics'] = {
            'first_name': first_name,
            'last_name': last_name,
            'preferred_name': first_name,
            'mrn': mrn,
            'age': age,
            'gender': gender,
            'biological_sex': biological_sex,
            'date_of_birth': date_of_birth.isoformat(),
            'ethnicity': ethnicity,
            'birth_country': 'USA'  # Default for random generation
        }

        # Generate AI photo if requested
        if generate_ai_photo:
            try:
                import sys
                from pathlib import Path
                sys.path.append(str(Path(__file__).parent.parent))
                from utils.ai_photo_generator import AIPhotoGenerator

                with st.spinner("📷 Generating AI photo from patient demographics..."):
                    # Load key from Streamlit secrets if available
                    # Prefer top-level, fallback to [api_keys] section
                    gemini_key = None
                    if "GOOGLE_API_KEY" in st.secrets:
                        gemini_key = st.secrets["GOOGLE_API_KEY"]
                    elif "api_keys" in st.secrets and "GOOGLE_API_KEY" in st.secrets["api_keys"]:
                        gemini_key = st.secrets["api_keys"]["GOOGLE_API_KEY"]

                    if not gemini_key:
                        st.warning("⚠️ GOOGLE_API_KEY not found in Streamlit secrets. Cannot generate AI photo.")
                        st.info("💡 Add GOOGLE_API_KEY to .streamlit/secrets.toml or Streamlit Cloud secrets to enable AI photo generation.")
                        # Generate placeholder avatar
                        initials = get_patient_initials(first_name, last_name)
                        avatar = generate_avatar(initials, size=(200, 200))
                        patient_profile['photo'] = save_avatar_to_bytes(avatar)
                        patient_profile['photo_format'] = 'avatar'
                    else:
                        try:
                            from google.genai import Client  # type: ignore
                        except ImportError:
                            st.warning("⚠️ google-genai package not installed. Cannot generate AI photo.")
                            st.info("💡 Install with: pip install google-genai")
                            initials = get_patient_initials(first_name, last_name)
                            avatar = generate_avatar(initials, size=(200, 200))
                            patient_profile['photo'] = save_avatar_to_bytes(avatar)
                            patient_profile['photo_format'] = 'avatar'
                        else:
                            os.environ.setdefault("GOOGLE_API_KEY", gemini_key)
                            generator = AIPhotoGenerator(api_key=gemini_key, service="gemini")
                            photo_bytes = generator.generate_patient_photo(patient_profile)

                            if photo_bytes:
                                patient_profile['photo'] = photo_bytes
                                patient_profile['photo_format'] = 'ai_generated'
                                st.success("✅ AI photo generated successfully!")
                            else:
                                error_msg = generator.last_error if hasattr(generator, 'last_error') else "Unknown error"
                                st.warning(f"⚠️ AI photo generation failed: {error_msg}")
                                st.info("💡 Using placeholder avatar instead.")
                                # Fallback to avatar
                                initials = get_patient_initials(first_name, last_name)
                                avatar = generate_avatar(initials, size=(200, 200))
                                patient_profile['photo'] = save_avatar_to_bytes(avatar)
                                patient_profile['photo_format'] = 'avatar'

            except Exception as e:
                st.warning(f"⚠️ AI photo generation error: {str(e)}")
                st.info("💡 Using placeholder avatar instead.")
                # Fallback to avatar
                initials = get_patient_initials(first_name, last_name)
                avatar = generate_avatar(initials, size=(200, 200))
                patient_profile['photo'] = save_avatar_to_bytes(avatar)
                patient_profile['photo_format'] = 'avatar'

        return patient_profile
    
    def _generate_lifestyle(self):
        """Generate lifestyle factors with SNOMED CT codes (matching auto-generated structure)"""
        factors = []
        
        # Smoking status
        smoking_choice = random.choice([
            {
                "@id": "http://snomed.info/id/228150001",
                "@type": "sdisco:LifestyleFactor",
                "snomed:code": "228150001",
                "rdfs:label": "Non-smoker",
                "skos:prefLabel": "Non-smoker",
                "factor_type": "smoking",
                "status": "never",
                "note": "No CYP1A2 induction from smoking"
            },
            {
                "@id": "http://snomed.info/id/8392000",
                "@type": "sdisco:LifestyleFactor",
                "snomed:code": "8392000",
                "rdfs:label": "Former smoker",
                "skos:prefLabel": "Former smoker",
                "factor_type": "smoking",
                "status": "former",
                "quit_date": (datetime.now() - timedelta(days=random.randint(365, 3650))).strftime("%Y-%m-%d"),
                "note": "CYP1A2 induction reverses after quitting"
            },
            {
                "@id": "http://snomed.info/id/77176002",
                "@type": "sdisco:LifestyleFactor",
                "snomed:code": "77176002",
                "rdfs:label": "Smoker",
                "skos:prefLabel": "Smoker",
                "factor_type": "smoking",
                "status": "current",
                "frequency": f"{random.randint(5, 30)} cigarettes/day",
                "note": "CYP1A2 induction from smoking"
            }
        ])
        factors.append(smoking_choice)
        
        # Alcohol consumption
        alcohol_choice = random.choice([
            {
                "@id": "http://snomed.info/id/228273003",
                "@type": "sdisco:LifestyleFactor",
                "snomed:code": "228273003",
                "rdfs:label": "Drinks alcohol",
                "skos:prefLabel": "Moderate alcohol consumption",
                "factor_type": "alcohol",
                "frequency": f"{random.randint(1, 14)} drinks/week",
                "note": "May affect CYP2E1 and liver function"
            },
            {
                "@id": "http://snomed.info/id/228276006",
                "@type": "sdisco:LifestyleFactor",
                "snomed:code": "228276006",
                "rdfs:label": "Does not drink alcohol",
                "skos:prefLabel": "Non-drinker",
                "factor_type": "alcohol",
                "note": "No alcohol-related drug interactions"
            }
        ])
        factors.append(alcohol_choice)
        
        # Exercise frequency
        exercise_choice = random.choice([
            {
                "@type": "sdisco:LifestyleFactor",
                "factor_type": "exercise",
                "rdfs:label": "Regular exercise",
                "frequency": f"{random.randint(2, 7)} times/week",
                "note": "May improve drug metabolism"
            },
            {
                "@type": "sdisco:LifestyleFactor",
                "factor_type": "exercise",
                "rdfs:label": "Sedentary lifestyle",
                "frequency": "Minimal physical activity",
                "note": "May affect drug distribution"
            }
        ])
        factors.append(exercise_choice)
        
        # Grapefruit consumption (important for CYP3A4)
        if random.random() < 0.3:  # 30% chance of grapefruit consumption
            factors.append({
                "@type": "sdisco:LifestyleFactor",
                "factor_type": "diet",
                "rdfs:label": "Regular grapefruit consumption",
                "frequency": "Daily",
                "note": "IMPORTANT: Inhibits CYP3A4 - affects many drugs"
            })
        
        return factors
    
    def _generate_organ_function(self):
        """Generate organ function test results with SNOMED CT codes (matching auto-generated structure)"""
        test_date = (datetime.now() - timedelta(days=random.randint(1, 90))).strftime("%Y-%m-%d")
        
        # Kidney function - normal range: 90-120 mL/min/1.73m²
        # Occasionally abnormal (15% chance of mild reduction)
        if random.random() < 0.15:
            creatinine_clearance = round(random.uniform(60, 89), 1)
            status_kidney = "mild_reduction"
        else:
            creatinine_clearance = round(random.uniform(90, 120), 1)
            status_kidney = "normal"
        
        serum_creatinine = round(random.uniform(0.6, 1.1), 2)
        
        # Liver function - normal ALT: 7-56 U/L, AST: 10-40 U/L
        # Occasionally elevated (10% chance)
        if random.random() < 0.10:
            alt_value = round(random.uniform(57, 100), 0)
            ast_value = round(random.uniform(41, 80), 0)
            status_liver = "elevated"
        else:
            alt_value = round(random.uniform(10, 50), 0)
            ast_value = round(random.uniform(15, 38), 0)
            status_liver = "normal"
        
        bilirubin_total = round(random.uniform(0.3, 1.0), 2)
        
        return {
            "kidney_function": {
                "creatinine_clearance": {
                    "@id": "http://snomed.info/id/102001005",
                    "snomed:code": "102001005",
                    "rdfs:label": "Creatinine clearance test",
                    "value": creatinine_clearance,
                    "unit": "mL/min/1.73m²",
                    "date": test_date,
                    "normal_range": "90-120 mL/min/1.73m²",
                    "status": status_kidney
                },
                "serum_creatinine": {
                    "value": serum_creatinine,
                    "unit": "mg/dL",
                    "date": test_date,
                    "normal_range": "0.6-1.1 mg/dL",
                    "status": "normal" if serum_creatinine <= 1.1 else "elevated"
                }
            },
            "liver_function": {
                "alt": {
                    "@id": "http://snomed.info/id/102711005",
                    "snomed:code": "102711005",
                    "rdfs:label": "Alanine aminotransferase measurement",
                    "value": alt_value,
                    "unit": "U/L",
                    "date": test_date,
                    "normal_range": "7-56 U/L",
                    "status": status_liver
                },
                "ast": {
                    "@id": "http://snomed.info/id/102712005",
                    "snomed:code": "102712005",
                    "rdfs:label": "Aspartate aminotransferase measurement",
                    "value": ast_value,
                    "unit": "U/L",
                    "date": test_date,
                    "normal_range": "10-40 U/L",
                    "status": status_liver
                },
                "bilirubin_total": {
                    "value": bilirubin_total,
                    "unit": "mg/dL",
                    "date": test_date,
                    "normal_range": "0.1-1.2 mg/dL",
                    "status": "normal" if bilirubin_total <= 1.2 else "elevated"
                }
            },
            "note": "Critical for drug dosing - particularly important for drugs cleared by kidney/liver"
        }
