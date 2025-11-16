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
                "African",
                "South Asian",
                "East Asian",
                "Southeast Asian",
                "Caucasian/European",
                "Hispanic/Latino",
                "Middle Eastern",
                "Native American",
                "Pacific Islander",
                "Mixed",
                "Other"
            ]
            ethnicity = st.multiselect(
                "Select Ethnicity/Race (important for PGx variant frequencies)",
                ethnicity_options,
                help="Examples: South Asian (Indian, Pakistani, Bangladeshi), East Asian (Chinese, Japanese, Korean), Southeast Asian (Thai, Vietnamese, Filipino). Indians typically fall under South Asian (within Asian)."
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
                language = st.selectbox(
                    "Primary Language",
                    [
                        "English",
                        "Arabic",
                        "Chinese",
                        "Dutch",
                        "French",
                        "Georgian",
                        "German",
                        "Hindi",
                        "Italian",
                        "Japanese",
                        "Korean",
                        "Portuguese",
                        "Russian",
                        "Spanish",
                        "Turkish",
                        "Urdu",
                        "Bengali",
                        "Persian (Farsi)",
                        "Other",
                    ],
                )
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
            submitted = st.form_submit_button("✅ Create Patient Profile", type="primary")
            
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
                        # Ensure we reload the latest AI photo generator code on reruns
                        import importlib
                        import utils.ai_photo_generator as _ai_pg
                        importlib.reload(_ai_pg)
                        AIPhotoGenerator = _ai_pg.AIPhotoGenerator

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
                                # Check required package
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

        # Diverse ethnicity options with realistic population-based weights
        # IMPORTANT: Matches manual form - Asian is split into South/East/Southeast for accurate representation
        # Weights balance global demographics with testing diversity (e.g., Pacific Islander ~0.1% globally, not 12.5%)
        ethnicity_options = [
            "South Asian",        # 15% - Indian, Pakistani, Bangladeshi, Sri Lankan (~24% global)
            "East Asian",         # 15% - Chinese, Japanese, Korean (~23% global)
            "Caucasian/European", # 20% - reflects ~16% global population (reduced from previous 45% bias)
            "African",            # 17% - reflects ~17% global population
            "Hispanic/Latino",    # 13% - reflects ~8% global population
            "Middle Eastern",     # 7%  - reflects ~5% global population
            "Southeast Asian",    # 5%  - Thai, Vietnamese, Filipino, Indonesian, Malaysian (~9% global)
            "Mixed",              # 5%  - ensures diverse mixed-ethnicity representation
            "Native American",    # 2%  - reflects <1% global population
            "Pacific Islander"    # 1%  - reflects <0.5% global population
        ]

        ethnicity_weights = [0.15, 0.15, 0.20, 0.17, 0.13, 0.07, 0.05, 0.05, 0.02, 0.01]

        # Select ethnicity based on weighted probabilities (not uniform!)
        ethnicity = [random.choices(ethnicity_options, weights=ethnicity_weights, k=1)[0]]
        ethnicity_key = ethnicity[0]

        # REGIONAL NAME STRUCTURE - Ensures cultural/geographic matching
        # First names from a region are ONLY paired with last names from that SAME region
        # This prevents unrealistic combinations (e.g., Nigerian first + Kenyan last)
        names_by_ethnicity_regional = {
            "African": {
                "regions": {
                    "Nigerian_Igbo": {
                        "countries": ["Nigeria"],
                        "Male": {
                            "first": ["Chike", "Chidi", "Chinonso", "Chibueze", "Emeka", "Ikenna", "Obinna", "Nnamdi", "Okechukwu", "Uchenna",
                                      "Chinedu", "Chijioke", "Obafemi", "Enyinnaya", "Ifeanyi", "Kelechi", "Nkem", "Obi", "Oge", "Ugo",
                                      "Chukwudi", "Chukwuemeka", "Ebuka", "Echezona", "Izuchukwu", "Kenechukwu", "Nnamani", "Obichukwu", "Okolie", "Onyeka"],
                            "last": ["Okafor", "Okeke", "Okonkwo", "Udoka", "Nwosu", "Eze", "Nnamdi", "Nwankwo", "Obinna", "Obi",
                                     "Onyekwere", "Ugochukwu", "Uzodinma", "Ezekiel", "Chukwu", "Onwuachu", "Nwachukwu", "Emezie"]
                        },
                        "Female": {
                            "first": ["Amara", "Chioma", "Ngozi", "Adaeze", "Ifeoma", "Chiamaka", "Nneka", "Obiageli", "Uchenna", "Nkechi",
                                      "Chidinma", "Chinwe", "Ebere", "Ego", "Ifunanya", "Njideka", "Nkiruka", "Nneoma", "Nwamaka", "Obioma",
                                      "Adanna", "Amarachi", "Chinenye", "Chinyere", "Echezona", "Ezinne", "Ijeoma", "Kamsiyochi", "Nkemdilim", "Onyinye"],
                            "last": ["Okafor", "Okeke", "Okonkwo", "Udoka", "Nwosu", "Eze", "Nnamdi", "Nwankwo", "Obinna", "Obi",
                                     "Onyekwere", "Ugochukwu", "Uzodinma", "Ezekiel", "Chukwu", "Onwuachu", "Nwachukwu", "Emezie"]
                        }
                    },
                    "Nigerian_Yoruba": {
                        "countries": ["Nigeria"],
                        "Male": {
                            "first": ["Ade", "Adebayo", "Adewale", "Ademola", "Oluwaseun", "Olumide", "Babatunde", "Ayodele", "Akinwale", "Olusegun",
                                      "Adeyemi", "Adekunle", "Adeniyi", "Akintunde", "Bolaji", "Damilola", "Kayode", "Olalekan", "Olaniyan", "Oluwatobi",
                                      "Adeyinka", "Akinola", "Ayotunde", "Babajide", "Femi", "Olamide", "Olaseni", "Oluseyi", "Omowale", "Taiwo"],
                            "last": ["Adeyemi", "Adeleke", "Akinyemi", "Oluwole", "Babatunde", "Ogundele", "Adekunle", "Adebayo", "Olawale", "Ogunleye",
                                     "Akinde", "Akinola", "Ayodele", "Famuyiwa", "Ogunbiyi", "Ogunsola", "Oladele", "Olatunji", "Oyewole"]
                        },
                        "Female": {
                            "first": ["Adunni", "Ayomide", "Bisola", "Folake", "Ife", "Jumoke", "Kehinde", "Modupe", "Omolara", "Titilayo",
                                      "Abosede", "Adetoun", "Aisha", "Boluwatife", "Damilola", "Folashade", "Funmilayo", "Iyabo", "Mojisola", "Olabisi",
                                      "Adebimpe", "Adedoyin", "Adeola", "Akinyi", "Bolanle", "Morayo", "Omowunmi", "Ronke", "Seun", "Yetunde"],
                            "last": ["Adeyemi", "Adeleke", "Akinyemi", "Oluwole", "Babatunde", "Ogundele", "Adekunle", "Adebayo", "Olawale", "Ogunleye",
                                     "Akinde", "Akinola", "Ayodele", "Famuyiwa", "Ogunbiyi", "Ogunsola", "Oladele", "Olatunji", "Oyewole"]
                        }
                    },
                    "Ghanaian_Akan": {
                        "countries": ["Ghana"],
                        "Male": {
                            "first": ["Kwame", "Kofi", "Kwesi", "Kwaku", "Yaw", "Kojo", "Kobina", "Kwadwo", "Kwabena", "Koffi",
                                      "Agyeman", "Akwasi", "Ato", "Kwamena", "Nana", "Opoku", "Yeboah", "Akosua", "Boateng", "Osei",
                                      "Adom", "Agyei", "Anane", "Atta", "Boadi", "Darkwa", "Frimpong", "Mensah", "Nyantakyi", "Owusu"],
                            "last": ["Mensah", "Asante", "Boateng", "Owusu", "Osei", "Nkrumah", "Agyeman", "Agyei", "Amoah", "Antwi",
                                     "Appiah", "Asare", "Attah", "Darkwa", "Frimpong", "Konadu", "Nyantakyi", "Opoku", "Yeboah"]
                        },
                        "Female": {
                            "first": ["Ama", "Afua", "Akua", "Abena", "Afia", "Akosua", "Adwoa", "Yaa", "Adjoa", "Esi",
                                      "Abena", "Efua", "Akosua", "Abenaa", "Ama", "Adwoa", "Afua", "Akua", "Yaa", "Esi",
                                      "Akosua", "Akosuah", "Amma", "Efua", "Ekua", "Enyonam", "Maame", "Nana", "Oboshie", "Yaayaa"],
                            "last": ["Mensah", "Asante", "Boateng", "Owusu", "Osei", "Nkrumah", "Agyeman", "Agyei", "Amoah", "Antwi",
                                     "Appiah", "Asare", "Attah", "Darkwa", "Frimpong", "Konadu", "Nyantakyi", "Opoku", "Yeboah"]
                        }
                    },
                    "Kenyan_Kikuyu": {
                        "countries": ["Kenya"],
                        "Male": {
                            "first": ["Kamau", "Mwangi", "Njoroge", "Kariuki", "Waweru", "Githinji", "Kimani", "Mugo", "Maina", "Ndungu",
                                      "Gachanja", "Gathii", "Karanja", "Kihara", "Macharia", "Mbugua", "Munyua", "Ng'ang'a", "Wachira", "Waititu",
                                      "Gacheru", "Gakuru", "Kamande", "Kariuki", "Kinyua", "Muhoro", "Mungai", "Muriithi", "Mutuku", "Njeru"],
                            "last": ["Mwangi", "Kamau", "Njoroge", "Kariuki", "Waweru", "Githinji", "Kimani", "Mugo", "Maina", "Ndungu",
                                     "Gachanja", "Githongo", "Karanja", "Macharia", "Mbugua", "Munyua", "Ng'ang'a", "Wachira", "Waithaka"]
                        },
                        "Female": {
                            "first": ["Wanjiru", "Njeri", "Nyambura", "Wangari", "Wanjiku", "Wairimu", "Gathoni", "Muthoni", "Nyokabi", "Wangui",
                                      "Kagure", "Mumbi", "Nduta", "Njoki", "Wambui", "Wangari", "Wanjiru", "Wawira", "Wacera", "Wamuyu",
                                      "Gitau", "Kanini", "Kariuki", "Mwihaki", "Njambi", "Nyaguthii", "Wahu", "Wainaina", "Wangu", "Warui"],
                            "last": ["Mwangi", "Kamau", "Njoroge", "Kariuki", "Waweru", "Githinji", "Kimani", "Mugo", "Maina", "Ndungu",
                                     "Gachanja", "Githongo", "Karanja", "Macharia", "Mbugua", "Munyua", "Ng'ang'a", "Wachira", "Waithaka"]
                        }
                    },
                    "Senegalese_Wolof": {
                        "countries": ["Senegal"],
                        "Male": {
                            "first": ["Amadou", "Ibrahima", "Mamadou", "Moussa", "Oumar", "Abdoulaye", "Aliou", "Babacar", "Cheikh", "Demba",
                                      "Fallou", "Lamine", "Mbacke", "Modou", "Omar", "Pape", "Samba", "Serigne", "Souleymane", "Youssou",
                                      "Ababacar", "Alioune", "Assane", "Baye", "Doudou", "El Hadji", "Gorgui", "Khadim", "Malick", "Ndiaga"],
                            "last": ["Diallo", "Sow", "Ba", "Sy", "Gueye", "Ndiaye", "Diop", "Fall", "Faye", "Sarr",
                                     "Cisse", "Diouf", "Kane", "Niang", "Sall", "Seck", "Thiam", "Toure", "Wade"]
                        },
                        "Female": {
                            "first": ["Aissatou", "Fatou", "Maimouna", "Mariame", "Ndeye", "Astou", "Coumba", "Diarra", "Khady", "Mame",
                                      "Nafi", "Ndella", "Oumou", "Rama", "Rokhaya", "Sokhna", "Yacine", "Aminata", "Bintou", "Dieynaba",
                                      "Adama", "Awa", "Daba", "Fama", "Hawa", "Kine", "Mbossé", "Seynabou", "Thierno", "Yaye"],
                            "last": ["Diallo", "Sow", "Ba", "Sy", "Gueye", "Ndiaye", "Diop", "Fall", "Faye", "Sarr",
                                     "Cisse", "Diouf", "Kane", "Niang", "Sall", "Seck", "Thiam", "Toure", "Wade"]
                        }
                    },
                    "South_African_Zulu": {
                        "countries": ["South Africa"],
                        "Male": {
                            "first": ["Themba", "Thabo", "Sipho", "Mandla", "Jabu", "Sizwe", "Bongani", "Mthunzi", "Sbu", "Vusi",
                                      "Bheki", "Dumisani", "Jabulani", "Khulekani", "Lungile", "Mlungisi", "Musa", "Nkosinathi", "Sandile", "Thulani",
                                      "Ayanda", "Bhekisisa", "Celimpilo", "Lwazi", "Mfundo", "Nhlanhla", "Nkululeko", "Sfiso", "Simphiwe", "Zweli"],
                            "last": ["Dube", "Khumalo", "Moyo", "Ncube", "Nkosi", "Ntuli", "Zulu", "Buthelezi", "Cele", "Gumede",
                                     "Hadebe", "Khanyile", "Mkhize", "Mlotshwa", "Ndlovu", "Ngcobo", "Nxumalo", "Shabalala", "Vilakazi"]
                        },
                        "Female": {
                            "first": ["Thandiwe", "Thando", "Nosipho", "Nomsa", "Precious", "Lindiwe", "Nandi", "Busisiwe", "Zandile", "Nonhle",
                                      "Ayanda", "Bongi", "Dudu", "Fikile", "Hlengiwe", "Khanyisile", "Londiwe", "Mandisa", "Mbali", "Nelisiwe",
                                      "Nompilo", "Nonhlanhla", "Ntombifuthi", "Phindile", "Sanelephi", "Sibongile", "Thembeka", "Zamani", "Zanele", "Zinhle"],
                            "last": ["Dube", "Khumalo", "Moyo", "Ncube", "Nkosi", "Ntuli", "Zulu", "Buthelezi", "Cele", "Gumede",
                                     "Hadebe", "Khanyile", "Mkhize", "Mlotshwa", "Ndlovu", "Ngcobo", "Nxumalo", "Shabalala", "Vilakazi"]
                        }
                    }
                }
            },
            "South Asian": {
                "regions": {
                    "North_Indian_Hindi": {
                        "countries": ["India"],
                        "Male": {
                            "first": ["Raj", "Rajesh", "Ravi", "Rohan", "Rahul", "Rohit", "Rakesh", "Amit", "Ankit", "Aman", "Abhishek",
                                      "Sanjay", "Suresh", "Sunil", "Sandeep", "Sachin", "Sameer", "Ajay", "Arun", "Ashok", "Atul",
                                      "Deepak", "Dev", "Dinesh", "Dhruv", "Gaurav", "Hemant", "Jatin", "Karan", "Kunal", "Lalit",
                                      "Manoj", "Mohit", "Naveen", "Nitin", "Pankaj", "Pramod", "Ramesh", "Saurabh", "Sumit", "Tarun"],
                            "last": ["Sharma", "Verma", "Gupta", "Agarwal", "Jain", "Bansal", "Kumar", "Singh", "Saxena", "Mathur",
                                     "Srivastava", "Tiwari", "Mishra", "Pandey", "Tripathi", "Chaturvedi", "Dixit", "Dwivedi", "Joshi", "Khanna"]
                        },
                        "Female": {
                            "first": ["Priya", "Preeti", "Pooja", "Pallavi", "Anjali", "Ananya", "Aditi", "Aarti", "Aparna", "Neha",
                                      "Nisha", "Nikita", "Namrata", "Nidhi", "Kavita", "Komal", "Meera", "Megha", "Manisha", "Maya",
                                      "Deepa", "Divya", "Ritu", "Radha", "Sonia", "Shreya", "Shweta", "Simran", "Sapna", "Swati",
                                      "Tanvi", "Vaishali", "Vidya", "Anita", "Asha", "Geeta", "Jaya", "Kiran", "Lata", "Mamta"],
                            "last": ["Sharma", "Verma", "Gupta", "Agarwal", "Jain", "Bansal", "Kumar", "Singh", "Saxena", "Mathur",
                                     "Srivastava", "Tiwari", "Mishra", "Pandey", "Tripathi", "Chaturvedi", "Dixit", "Dwivedi", "Joshi", "Khanna"]
                        }
                    },
                    "North_Indian_Punjabi": {
                        "countries": ["India"],
                        "Male": {
                            "first": ["Gurpreet", "Harpreet", "Jaspreet", "Kuldeep", "Mandeep", "Navdeep", "Parmeet", "Rajinder", "Sukhdev", "Tejinder",
                                      "Amarjit", "Balwinder", "Gurbir", "Harbir", "Inderjit", "Joginder", "Kulwant", "Manjit", "Navjot", "Paramjit",
                                      "Ranjit", "Satwinder", "Surinder", "Tarlok", "Varinder", "Bhagat", "Gurdev", "Hardev", "Jasbir", "Lakhwinder"],
                            "last": ["Singh", "Kaur", "Gill", "Sandhu", "Bhatia", "Dhillon", "Grewal", "Sidhu", "Saini", "Randhawa",
                                     "Bajwa", "Cheema", "Virk", "Brar", "Chahal", "Hundal", "Mann", "Sohi", "Bal", "Deol"]
                        },
                        "Female": {
                            "first": ["Simran", "Harleen", "Jasmeet", "Kulwant", "Manpreet", "Navneet", "Parminder", "Rajinder", "Sukhjit", "Tejinder",
                                      "Amarjit", "Balwinder", "Gurbir", "Harbir", "Inderjit", "Jagjit", "Kulvir", "Manjit", "Navjot", "Parveen",
                                      "Ramandeep", "Satwant", "Surinder", "Taranjit", "Varinder", "Bhagwant", "Gurdev", "Hardev", "Jasbir", "Lakhwinder"],
                            "last": ["Singh", "Kaur", "Gill", "Sandhu", "Bhatia", "Dhillon", "Grewal", "Sidhu", "Saini", "Randhawa",
                                     "Bajwa", "Cheema", "Virk", "Brar", "Chahal", "Hundal", "Mann", "Sohi", "Bal", "Deol"]
                        }
                    },
                    "South_Indian_Tamil": {
                        "countries": ["India", "Sri Lanka"],
                        "Male": {
                            "first": ["Arun", "Balaji", "Dinesh", "Ganesh", "Karthik", "Kumar", "Murali", "Prakash", "Rajesh", "Ramesh",
                                      "Suresh", "Venkat", "Vijay", "Aravind", "Bala", "Chandru", "Durai", "Ganesan", "Hari", "Ilango",
                                      "Jagan", "Kannan", "Kumaran", "Loganathan", "Murugan", "Naveen", "Pandiyan", "Raja", "Saravanan", "Tamil"],
                            "last": ["Kumar", "Raj", "Selvam", "Murugan", "Rajan", "Krishnan", "Narayanan", "Subramanian", "Ramachandran", "Venkatesh",
                                     "Sundaram", "Pillai", "Nair", "Menon", "Iyer", "Iyengar", "Chettiar", "Gounder", "Mudaliar", "Nadar"]
                        },
                        "Female": {
                            "first": ["Devi", "Lakshmi", "Meera", "Priya", "Radha", "Saranya", "Sita", "Uma", "Vani", "Vijaya",
                                      "Anitha", "Bhavani", "Deepa", "Geetha", "Hema", "Indira", "Janaki", "Kamala", "Latha", "Malini",
                                      "Nithya", "Padma", "Revathi", "Sangeetha", "Tamilselvi", "Usha", "Vasantha", "Yamuna", "Asha", "Kavitha"],
                            "last": ["Kumar", "Raj", "Selvam", "Murugan", "Rajan", "Krishnan", "Narayanan", "Subramanian", "Ramachandran", "Venkatesh",
                                     "Sundaram", "Pillai", "Nair", "Menon", "Iyer", "Iyengar", "Chettiar", "Gounder", "Mudaliar", "Nadar"]
                        }
                    },
                    "Pakistani": {
                        "countries": ["Pakistan"],
                        "Male": {
                            "first": ["Farhan", "Faisal", "Fahad", "Faraz", "Imran", "Irfan", "Ibrahim", "Ismail", "Hassan", "Hamza",
                                      "Ahmed", "Ali", "Arslan", "Asif", "Adnan", "Bilal", "Babar", "Rehan", "Rizwan", "Salman",
                                      "Shahid", "Tariq", "Usman", "Zain", "Aamir", "Aslam", "Azhar", "Danish", "Fawad", "Haider",
                                      "Junaid", "Kamran", "Majid", "Naveed", "Omar", "Qaiser", "Saad", "Sohail", "Waqar", "Yasir"],
                            "last": ["Khan", "Ahmed", "Ali", "Malik", "Sheikh", "Syed", "Hussain", "Hassan", "Abbas", "Raza",
                                     "Akhtar", "Aziz", "Butt", "Chaudhry", "Iqbal", "Javed", "Mirza", "Qureshi", "Riaz", "Shah"]
                        },
                        "Female": {
                            "first": ["Aisha", "Ayesha", "Amina", "Aliya", "Fatima", "Farah", "Farhana", "Zara", "Zainab", "Zahra",
                                      "Sana", "Sara", "Sadia", "Samina", "Nadia", "Noor", "Mariam", "Maria", "Hina", "Hira",
                                      "Bushra", "Dur-e-Shehwar", "Eman", "Fozia", "Kiran", "Laiba", "Mehwish", "Naila", "Rabiya", "Saima",
                                      "Shazia", "Sidra", "Tahira", "Uzma", "Wardah", "Zoya", "Anum", "Fiza", "Maheen", "Rabia"],
                            "last": ["Khan", "Ahmed", "Ali", "Malik", "Sheikh", "Syed", "Hussain", "Hassan", "Abbas", "Raza",
                                     "Akhtar", "Aziz", "Butt", "Chaudhry", "Iqbal", "Javed", "Mirza", "Qureshi", "Riaz", "Shah"]
                        }
                    },
                    "Bangladeshi": {
                        "countries": ["Bangladesh"],
                        "Male": {
                            "first": ["Abdul", "Akram", "Alam", "Aziz", "Faruk", "Habib", "Hasan", "Iqbal", "Jalal", "Kamal",
                                      "Latif", "Majid", "Moin", "Nasir", "Rafiq", "Rahim", "Rashid", "Salam", "Salim", "Shafiq",
                                      "Shahin", "Shakil", "Taher", "Tariq", "Wahid", "Yusuf", "Zahid", "Zia", "Asad", "Babar"],
                            "last": ["Chowdhury", "Rahman", "Hossain", "Islam", "Mahmud", "Ahmed", "Ali", "Haque", "Khan", "Miah",
                                     "Alam", "Aziz", "Bhuiyan", "Chowdhury", "Hasan", "Hussain", "Kabir", "Karim", "Molla", "Uddin"]
                        },
                        "Female": {
                            "first": ["Aklima", "Amina", "Ayesha", "Farida", "Fatema", "Hasina", "Jasmin", "Joya", "Khadija", "Kulsum",
                                      "Laila", "Morium", "Nasima", "Parveen", "Rahima", "Rehana", "Rokshana", "Sabina", "Salma", "Shamsun",
                                      "Shapla", "Sharmin", "Shireen", "Sufia", "Sultana", "Tahmina", "Taslima", "Yasmin", "Zakia", "Zebunnessa"],
                            "last": ["Chowdhury", "Rahman", "Hossain", "Islam", "Mahmud", "Ahmed", "Ali", "Haque", "Khan", "Miah",
                                     "Alam", "Aziz", "Bhuiyan", "Chowdhury", "Hasan", "Hussain", "Kabir", "Karim", "Molla", "Uddin"]
                        }
                    }
                }
            },
            "East Asian": {
                "regions": {
                    "Chinese": {
                        "countries": ["China", "Taiwan", "Hong Kong"],
                        "Male": {
                            "first": ["Wei", "Wang", "Chen", "Li", "Zhang", "Liu", "Yang", "Huang", "Zhao", "Wu",
                                      "Zhou", "Xu", "Sun", "Ma", "Zhu", "Hu", "Guo", "He", "Gao", "Lin",
                                      "Zheng", "Liang", "Song", "Tang", "Han", "Feng", "Yu", "Dong", "Xiao", "Cheng",
                                      "Cao", "Peng", "Luo", "Yuan", "Jiang", "Gu", "Cui", "Lu", "Shi", "Tian"],
                            "last": ["Wang", "Li", "Zhang", "Liu", "Chen", "Yang", "Huang", "Zhao", "Wu", "Zhou",
                                     "Xu", "Sun", "Ma", "Zhu", "Hu", "Guo", "He", "Gao", "Lin", "Zheng",
                                     "Liang", "Song", "Tang", "Han", "Feng", "Yu", "Dong", "Cao", "Peng", "Yuan"]
                        },
                        "Female": {
                            "first": ["Mei", "Lin", "Ying", "Xiu", "Jing", "Hui", "Fang", "Min", "Yan", "Qing",
                                      "Xia", "Juan", "Ling", "Li", "Yue", "Rui", "Shu", "Xin", "Yu", "Na",
                                      "Hua", "Ping", "Lan", "Hong", "Jie", "Wen", "Xue", "Rou", "Shan", "Zhen",
                                      "Qian", "Fen", "Cui", "Dan", "Fei", "Gui", "He", "Ju", "Kun", "Man"],
                            "last": ["Wang", "Li", "Zhang", "Liu", "Chen", "Yang", "Huang", "Zhao", "Wu", "Zhou",
                                     "Xu", "Sun", "Ma", "Zhu", "Hu", "Guo", "He", "Gao", "Lin", "Zheng",
                                     "Liang", "Song", "Tang", "Han", "Feng", "Yu", "Dong", "Cao", "Peng", "Yuan"]
                        }
                    },
                    "Japanese": {
                        "countries": ["Japan"],
                        "Male": {
                            "first": ["Hiroshi", "Takeshi", "Kenji", "Takashi", "Yuki", "Kazuo", "Akira", "Haruki", "Ryo", "Satoshi",
                                      "Masaki", "Yuto", "Daiki", "Koji", "Makoto", "Naoki", "Shota", "Takumi", "Yuuki", "Kaito",
                                      "Sho", "Ren", "Hayato", "Kenta", "Taro", "Ichiro", "Jiro", "Kenji", "Minoru", "Osamu",
                                      "Shigeru", "Tatsuya", "Tomoya", "Yasuo", "Yoshio", "Katsuo", "Masao", "Noboru", "Shiro", "Toshio"],
                            "last": ["Tanaka", "Suzuki", "Takahashi", "Watanabe", "Ito", "Yamamoto", "Nakamura", "Kobayashi", "Kato", "Yoshida",
                                     "Yamada", "Sasaki", "Yamaguchi", "Matsumoto", "Inoue", "Kimura", "Hayashi", "Shimizu", "Saito", "Endo",
                                     "Fujita", "Okada", "Goto", "Hasegawa", "Murakami", "Kondo", "Ishikawa", "Maeda", "Fujii", "Ogawa"]
                        },
                        "Female": {
                            "first": ["Yuki", "Sakura", "Hana", "Aiko", "Yui", "Haruka", "Kana", "Aya", "Mio", "Rina",
                                      "Saki", "Nana", "Miyu", "Ayaka", "Yuka", "Miyuki", "Akiko", "Keiko", "Emi", "Kaori",
                                      "Rei", "Chika", "Fumiko", "Hanako", "Junko", "Kumiko", "Mariko", "Noriko", "Reiko", "Sachiko",
                                      "Tomoko", "Yoko", "Ayumi", "Chihiro", "Eriko", "Hitomi", "Kiyomi", "Mayumi", "Natsuko", "Satomi"],
                            "last": ["Tanaka", "Suzuki", "Takahashi", "Watanabe", "Ito", "Yamamoto", "Nakamura", "Kobayashi", "Kato", "Yoshida",
                                     "Yamada", "Sasaki", "Yamaguchi", "Matsumoto", "Inoue", "Kimura", "Hayashi", "Shimizu", "Saito", "Endo",
                                     "Fujita", "Okada", "Goto", "Hasegawa", "Murakami", "Kondo", "Ishikawa", "Maeda", "Fujii", "Ogawa"]
                        }
                    },
                    "Korean": {
                        "countries": ["South Korea"],
                        "Male": {
                            "first": ["Min-jun", "Min-ho", "Seung", "Jin", "Joon", "Hwan", "Hyun", "Tae", "Sang", "Jun",
                                      "Woo", "Soo", "Dong", "Young", "Sung", "Ji-ho", "Seo-jun", "Ha-jun", "Do-yoon", "Si-woo",
                                      "Ye-jun", "Jae", "Kyung", "Ho", "Chul", "Hyung", "Myung", "Byung", "Chang", "Dae",
                                      "Gyu", "Ik", "Jong", "Ki", "Nam", "Pil", "Sang", "Tae", "Won", "Yong"],
                            "last": ["Kim", "Lee", "Park", "Choi", "Jung", "Kang", "Cho", "Yoon", "Jang", "Lim",
                                     "Han", "Oh", "Seo", "Shin", "Kwon", "Hwang", "Ahn", "Song", "Hong", "Baek",
                                     "Nam", "Moon", "Yang", "Ko", "Kwak", "Jeon", "Son", "Yoo", "Ryu", "Noh"]
                        },
                        "Female": {
                            "first": ["Ji-woo", "Min-ji", "Seo-yeon", "Hye", "Yuna", "Su", "Eun", "Soo-jin", "Ji-hye", "Mi",
                                      "Young", "Sun", "Hee", "Jin", "Ha-eun", "Seo-hyun", "Ye-ji", "Chae-won", "Ji-yoo", "Soo-ah",
                                      "Kyung", "Bo", "Ae", "Ok", "Soon", "Ja", "Sook", "Jung", "Hwa", "Myung",
                                      "Yeon", "Hyun", "Seon", "Hyo", "Na", "Da", "Ra", "Sa", "A", "Bi"],
                            "last": ["Kim", "Lee", "Park", "Choi", "Jung", "Kang", "Cho", "Yoon", "Jang", "Lim",
                                     "Han", "Oh", "Seo", "Shin", "Kwon", "Hwang", "Ahn", "Song", "Hong", "Baek",
                                     "Nam", "Moon", "Yang", "Ko", "Kwak", "Jeon", "Son", "Yoo", "Ryu", "Noh"]
                        }
                    }
                }
            },
            "Southeast Asian": {
                "regions": {
                    "Vietnamese": {
                        "countries": ["Vietnam"],
                        "Male": {
                            "first": ["Nguyen", "Thanh", "Minh", "Tuan", "Hai", "Hung", "Duc", "Huy", "Khoa", "Phong",
                                      "Tung", "Dung", "Quan", "Kien", "Long", "Nam", "An", "Binh", "Cuong", "Dat",
                                      "Hieu", "Hoang", "Khanh", "Linh", "Manh", "Quang", "Son", "Tam", "Thang", "Trung",
                                      "Tien", "Vinh", "Vu", "Thien", "Phat", "Thinh", "Toan", "Tri", "Truong", "Viet"],
                            "last": ["Nguyen", "Tran", "Le", "Pham", "Hoang", "Huynh", "Phan", "Vu", "Vo", "Dang",
                                     "Bui", "Do", "Ngo", "Duong", "Ly", "Dinh", "Ha", "Cao", "Trinh", "Lam"]
                        },
                        "Female": {
                            "first": ["Linh", "Thu", "Mai", "Lan", "Hoa", "Huong", "Nga", "Thuy", "Hanh", "Phuong",
                                      "Van", "Thi", "Hong", "My", "Anh", "Vy", "Chi", "Dung", "Giang", "Ha",
                                      "Hang", "Hien", "Kim", "Loan", "Nhu", "Quynh", "Tam", "Thao", "Trang", "Tuyet",
                                      "Uyen", "Xuan", "Yen", "Bich", "Cam", "Dao", "Dieu", "Le", "Ngoc", "Phuong"],
                            "last": ["Nguyen", "Tran", "Le", "Pham", "Hoang", "Huynh", "Phan", "Vu", "Vo", "Dang",
                                     "Bui", "Do", "Ngo", "Duong", "Ly", "Dinh", "Ha", "Cao", "Trinh", "Lam"]
                        }
                    },
                    "Thai": {
                        "countries": ["Thailand"],
                        "Male": {
                            "first": ["Somchai", "Prakit", "Surin", "Kittisak", "Anon", "Boon", "Chai", "Niran", "Thaksin", "Manop",
                                      "Prawit", "Somsak", "Wichai", "Apichat", "Chaiya", "Danai", "Ekachai", "Kriangsak", "Narong", "Prayut",
                                      "Sarawut", "Somkid", "Supachai", "Thanakorn", "Weerasak", "Arthit", "Chatchai", "Itthipol", "Krit", "Nirut",
                                      "Phakorn", "Rachan", "Sawat", "Thanat", "Wasan", "Yutthana", "Anucha", "Boonyong", "Chusak", "Damrong"],
                            "last": ["Pong", "Srisai", "Boon", "Chai", "Somchai", "Thaksin", "Wongsakorn", "Rattana", "Sukhothai", "Pattana",
                                     "Chaiyaporn", "Kittipong", "Narongrit", "Phongchai", "Suraphon", "Thawatchai", "Weerachai", "Yongyut", "Anusorn", "Chatchawan"]
                        },
                        "Female": {
                            "first": ["Siriporn", "Kanya", "Ratana", "Suda", "Malee", "Pranee", "Nittaya", "Arunee", "Busara", "Chanya",
                                      "Pimchanok", "Warunee", "Anchali", "Chanida", "Jintana", "Nongnat", "Parichat", "Saengdao", "Somjai", "Thitima",
                                      "Wilaiwan", "Apinya", "Bussaba", "Chalinee", "Kannika", "Lakana", "Monthira", "Nisa", "Orawan", "Patcharee",
                                      "Rachanee", "Saowapa", "Supaporn", "Tarika", "Wanpen", "Yaowares", "Apsara", "Boonyisa", "Chompoo", "Duangjai"],
                            "last": ["Pong", "Srisai", "Boon", "Chai", "Somchai", "Thaksin", "Wongsakorn", "Rattana", "Sukhothai", "Pattana",
                                     "Chaiyaporn", "Kittipong", "Narongrit", "Phongchai", "Suraphon", "Thawatchai", "Weerachai", "Yongyut", "Anusorn", "Chatchawan"]
                        }
                    },
                    "Filipino": {
                        "countries": ["Philippines"],
                        "Male": {
                            "first": ["Jose", "Ramon", "Carlos", "Miguel", "Juan", "Antonio", "Francisco", "Manuel", "Luis", "Pedro",
                                      "Fernando", "Rafael", "Mario", "Ernesto", "Roberto", "Enrique", "Ricardo", "Alfredo", "Eduardo", "Rodrigo",
                                      "Raul", "Sergio", "Arturo", "Jorge", "Alberto", "Felipe", "Julio", "Marcos", "Pablo", "Salvador",
                                      "Vicente", "Dante", "Emilio", "Gregorio", "Jaime", "Leonardo", "Martin", "Oscar", "Pascual", "Rey"],
                            "last": ["Santos", "Reyes", "Cruz", "Bautista", "Ocampo", "Garcia", "Mendoza", "Dela Cruz", "Ramos", "Flores",
                                     "Gonzales", "Torres", "Aquino", "Villanueva", "Lopez", "Rivera", "Fernandez", "Martinez", "Domingo", "Castillo"]
                        },
                        "Female": {
                            "first": ["Maria", "Rosa", "Carmen", "Ana", "Isabel", "Teresa", "Elena", "Sofia", "Luisa", "Angelica",
                                      "Cristina", "Patricia", "Gloria", "Lourdes", "Mercedes", "Remedios", "Beatriz", "Concepcion", "Dolores", "Esperanza",
                                      "Fe", "Guadalupe", "Imelda", "Josefina", "Luz", "Milagros", "Natividad", "Paz", "Rosario", "Soledad",
                                      "Victoria", "Asuncion", "Caridad", "Divina", "Erlinda", "Felicidad", "Gracia", "Josefa", "Leonor", "Purificacion"],
                            "last": ["Santos", "Reyes", "Cruz", "Bautista", "Ocampo", "Garcia", "Mendoza", "Dela Cruz", "Ramos", "Flores",
                                     "Gonzales", "Torres", "Aquino", "Villanueva", "Lopez", "Rivera", "Fernandez", "Martinez", "Domingo", "Castillo"]
                        }
                    },
                    "Indonesian": {
                        "countries": ["Indonesia", "Malaysia", "Singapore"],
                        "Male": {
                            "first": ["Budi", "Ahmad", "Farid", "Amir", "Rizal", "Yusuf", "Hassan", "Ibrahim", "Ismail", "Abdullah",
                                      "Rahman", "Aziz", "Fikri", "Hadi", "Ilham", "Joko", "Kurnia", "Lukman", "Muchtar", "Nur",
                                      "Prayitno", "Raden", "Santoso", "Taufik", "Usman", "Wahyu", "Yanto", "Zainal", "Adi", "Bagus",
                                      "Cahya", "Darmawan", "Eko", "Febrian", "Guntur", "Hendro", "Irfan", "Jaya", "Kusuma", "Luhur"],
                            "last": ["Santoso", "Wijaya", "Rahman", "Abdullah", "Tan", "Lim", "Ng", "Wong", "Chan", "Putri",
                                     "Sari", "Kusuma", "Pratama", "Utama", "Kurniawan", "Susanto", "Wibowo", "Setiawan", "Pranoto", "Hakim"]
                        },
                        "Female": {
                            "first": ["Siti", "Nurul", "Aisyah", "Dewi", "Sri", "Fatimah", "Aminah", "Khadijah", "Maryam", "Zainab",
                                      "Nur", "Laila", "Salma", "Ayu", "Citra", "Dian", "Eka", "Fitri", "Indah", "Kartika",
                                      "Lestari", "Maya", "Nisa", "Putri", "Rina", "Sari", "Tuti", "Uswah", "Wulan", "Yuni",
                                      "Anggun", "Bunga", "Cahaya", "Diah", "Endah", "Galuh", "Hasna", "Intan", "Jelita", "Kasih"],
                            "last": ["Santoso", "Wijaya", "Rahman", "Abdullah", "Tan", "Lim", "Ng", "Wong", "Chan", "Putri",
                                     "Sari", "Kusuma", "Pratama", "Utama", "Kurniawan", "Susanto", "Wibowo", "Setiawan", "Pranoto", "Hakim"]
                        }
                    }
                }
            },
            "Caucasian/European": {
                "regions": {
                    "British": {
                        "countries": ["United Kingdom", "England", "Scotland", "Wales", "Ireland"],
                        "Male": {
                            "first": ["James", "William", "Thomas", "Oliver", "Alexander", "Henry", "Charles", "Daniel", "Lucas", "Michael",
                                      "John", "Robert", "David", "Richard", "Joseph", "Christopher", "Matthew", "Andrew", "George", "Edward",
                                      "Benjamin", "Samuel", "Jack", "Harry", "Liam", "Noah", "Jacob", "Ethan", "Logan", "Oscar",
                                      "Arthur", "Archie", "Freddie", "Leo", "Theodore", "Alfie", "Finley", "Isaac", "Joshua", "Muhammad"],
                            "last": ["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Wilson", "Anderson", "Taylor",
                                     "Thomas", "Moore", "Jackson", "Martin", "Lee", "Thompson", "White", "Harris", "Clark", "Lewis",
                                     "Walker", "Hall", "Allen", "Young", "King", "Wright", "Scott", "Green", "Baker", "Adams"]
                        },
                        "Female": {
                            "first": ["Emma", "Olivia", "Sophia", "Charlotte", "Amelia", "Isabella", "Mia", "Evelyn", "Harper", "Emily",
                                      "Elizabeth", "Sarah", "Grace", "Victoria", "Hannah", "Jessica", "Sophie", "Lucy", "Alice", "Rose",
                                      "Lily", "Ella", "Chloe", "Abigail", "Ava", "Isla", "Poppy", "Freya", "Ivy", "Willow",
                                      "Florence", "Daisy", "Phoebe", "Elsie", "Rosie", "Maisie", "Aria", "Matilda", "Sienna", "Eleanor"],
                            "last": ["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Wilson", "Anderson", "Taylor",
                                     "Thomas", "Moore", "Jackson", "Martin", "Lee", "Thompson", "White", "Harris", "Clark", "Lewis",
                                     "Walker", "Hall", "Allen", "Young", "King", "Wright", "Scott", "Green", "Baker", "Adams"]
                        }
                    },
                    "French": {
                        "countries": ["France"],
                        "Male": {
                            "first": ["Pierre", "Jean", "Louis", "François", "Antoine", "Nicolas", "Luc", "Marc", "Jacques", "Michel",
                                      "Philippe", "Alain", "Patrick", "Christophe", "Laurent", "Olivier", "Julien", "Sébastien", "Stéphane", "David",
                                      "Thomas", "Alexandre", "Maxime", "Hugo", "Lucas", "Nathan", "Mathis", "Léo", "Gabriel", "Arthur",
                                      "Jules", "Raphaël", "Théo", "Nolan", "Adam", "Ethan", "Paul", "Victor", "Sacha", "Romain"],
                            "last": ["Dubois", "Martin", "Bernard", "Petit", "Robert", "Richard", "Durand", "Leroy", "Moreau", "Simon",
                                     "Laurent", "Lefebvre", "Michel", "Garcia", "Roux", "Fontaine", "Chevalier", "Lambert", "Bonnet", "Blanc",
                                     "Garnier", "Morel", "Fournier", "Rousseau", "Vincent", "Muller", "Leclerc", "Mercier", "Girard", "Dupont"]
                        },
                        "Female": {
                            "first": ["Marie", "Sophie", "Camille", "Julie", "Chloé", "Emma", "Léa", "Manon", "Charlotte", "Sarah",
                                      "Pauline", "Laura", "Lucie", "Anaïs", "Claire", "Marion", "Amélie", "Céline", "Nathalie", "Isabelle",
                                      "Louise", "Alice", "Jade", "Léna", "Zoé", "Inès", "Lola", "Rose", "Anna", "Lily",
                                      "Mila", "Nina", "Juliette", "Chloé", "Eva", "Romane", "Clara", "Elise", "Margot", "Ambre"],
                            "last": ["Dubois", "Martin", "Bernard", "Petit", "Robert", "Richard", "Durand", "Leroy", "Moreau", "Simon",
                                     "Laurent", "Lefebvre", "Michel", "Garcia", "Roux", "Fontaine", "Chevalier", "Lambert", "Bonnet", "Blanc",
                                     "Garnier", "Morel", "Fournier", "Rousseau", "Vincent", "Muller", "Leclerc", "Mercier", "Girard", "Dupont"]
                        }
                    },
                    "German": {
                        "countries": ["Germany", "Austria", "Switzerland"],
                        "Male": {
                            "first": ["Hans", "Klaus", "Wolfgang", "Dieter", "Jürgen", "Helmut", "Stefan", "Matthias", "Andreas", "Michael",
                                      "Thomas", "Christian", "Martin", "Daniel", "Sebastian", "Markus", "Alexander", "Tobias", "Florian", "Lukas",
                                      "Felix", "Maximilian", "Leon", "Paul", "Jonas", "Noah", "Elias", "Finn", "Oskar", "Anton",
                                      "Karl", "Friedrich", "Wilhelm", "Heinrich", "Otto", "Ludwig", "Franz", "Ernst", "Walter", "Hermann"],
                            "last": ["Müller", "Schmidt", "Schneider", "Fischer", "Weber", "Meyer", "Wagner", "Becker", "Schulz", "Hoffmann",
                                     "Schäfer", "Koch", "Bauer", "Richter", "Klein", "Wolf", "Schröder", "Neumann", "Schwarz", "Zimmermann",
                                     "Braun", "Krüger", "Hofmann", "Hartmann", "Lange", "Schmitt", "Werner", "Schmitz", "Krause", "Meier"]
                        },
                        "Female": {
                            "first": ["Anna", "Emma", "Maria", "Sophie", "Laura", "Lena", "Julia", "Katharina", "Sarah", "Lisa",
                                      "Hannah", "Lea", "Mia", "Emilia", "Clara", "Charlotte", "Maja", "Luisa", "Amelie", "Johanna",
                                      "Marie", "Paula", "Frieda", "Greta", "Ida", "Mila", "Ella", "Nele", "Pia", "Helene",
                                      "Gertrud", "Hildegard", "Ursula", "Ingrid", "Brunhilde", "Heidi", "Anneliese", "Brigitte", "Christa", "Monika"],
                            "last": ["Müller", "Schmidt", "Schneider", "Fischer", "Weber", "Meyer", "Wagner", "Becker", "Schulz", "Hoffmann",
                                     "Schäfer", "Koch", "Bauer", "Richter", "Klein", "Wolf", "Schröder", "Neumann", "Schwarz", "Zimmermann",
                                     "Braun", "Krüger", "Hofmann", "Hartmann", "Lange", "Schmitt", "Werner", "Schmitz", "Krause", "Meier"]
                        }
                    },
                    "Italian": {
                        "countries": ["Italy"],
                        "Male": {
                            "first": ["Marco", "Luca", "Matteo", "Alessandro", "Giovanni", "Andrea", "Francesco", "Giuseppe", "Antonio", "Luigi",
                                      "Paolo", "Carlo", "Stefano", "Davide", "Federico", "Lorenzo", "Riccardo", "Simone", "Nicola", "Gabriele",
                                      "Leonardo", "Tommaso", "Edoardo", "Pietro", "Filippo", "Vincenzo", "Salvatore", "Emanuele", "Alberto", "Roberto",
                                      "Domenico", "Franco", "Bruno", "Sergio", "Mario", "Angelo", "Massimo", "Claudio", "Giorgio", "Daniele"],
                            "last": ["Rossi", "Russo", "Ferrari", "Esposito", "Bianchi", "Romano", "Colombo", "Ricci", "Marino", "Greco",
                                     "Bruno", "Gallo", "Conti", "De Luca", "Costa", "Giordano", "Mancini", "Rizzo", "Lombardi", "Moretti",
                                     "Barbieri", "Fontana", "Santoro", "Mariani", "Rinaldi", "Caruso", "Ferrara", "Galli", "Martini", "Leone"]
                        },
                        "Female": {
                            "first": ["Giulia", "Sofia", "Francesca", "Chiara", "Martina", "Valentina", "Alessia", "Sara", "Elisa", "Anna",
                                      "Laura", "Silvia", "Claudia", "Elena", "Paola", "Maria", "Federica", "Ilaria", "Roberta", "Michela",
                                      "Giorgia", "Aurora", "Alice", "Greta", "Beatrice", "Emma", "Matilde", "Vittoria", "Camilla", "Viola",
                                      "Rosa", "Teresa", "Lucia", "Carmela", "Angela", "Giovanna", "Isabella", "Caterina", "Margherita", "Serena"],
                            "last": ["Rossi", "Russo", "Ferrari", "Esposito", "Bianchi", "Romano", "Colombo", "Ricci", "Marino", "Greco",
                                     "Bruno", "Gallo", "Conti", "De Luca", "Costa", "Giordano", "Mancini", "Rizzo", "Lombardi", "Moretti",
                                     "Barbieri", "Fontana", "Santoro", "Mariani", "Rinaldi", "Caruso", "Ferrara", "Galli", "Martini", "Leone"]
                        }
                    },
                    "Spanish_Portuguese": {
                        "countries": ["Spain", "Portugal"],
                        "Male": {
                            "first": ["Pablo", "Javier", "Alberto", "Fernando", "Rafael", "Jorge", "Antonio", "Manuel", "José", "Carlos",
                                      "Miguel", "Alejandro", "David", "Daniel", "Francisco", "Sergio", "Andrés", "Luis", "Pedro", "Óscar",
                                      "Raúl", "Rubén", "Iván", "Adrián", "Víctor", "Álvaro", "Hugo", "Mario", "Diego", "Gonzalo",
                                      "João", "Miguel", "Pedro", "Tiago", "Gonçalo", "Francisco", "Diogo", "André", "Rafael", "Martim"],
                            "last": ["González", "Rodríguez", "García", "Fernández", "López", "Martínez", "Sánchez", "Pérez", "Gómez", "Martín",
                                     "Jiménez", "Ruiz", "Hernández", "Díaz", "Moreno", "Álvarez", "Muñoz", "Romero", "Alonso", "Gutiérrez",
                                     "Silva", "Santos", "Ferreira", "Pereira", "Oliveira", "Costa", "Rodrigues", "Martins", "Sousa", "Carvalho"]
                        },
                        "Female": {
                            "first": ["María", "Carmen", "Dolores", "Pilar", "Isabel", "Teresa", "Ana", "Lucía", "Paula", "Laura",
                                      "Marta", "Sara", "Cristina", "Elena", "Beatriz", "Raquel", "Silvia", "Natalia", "Patricia", "Andrea",
                                      "Sofía", "Claudia", "Julia", "Alba", "Irene", "Marina", "Carla", "Nerea", "Daniela", "Victoria",
                                      "Maria", "Ana", "Beatriz", "Inês", "Mariana", "Sofia", "Carolina", "Joana", "Leonor", "Matilde"],
                            "last": ["González", "Rodríguez", "García", "Fernández", "López", "Martínez", "Sánchez", "Pérez", "Gómez", "Martín",
                                     "Jiménez", "Ruiz", "Hernández", "Díaz", "Moreno", "Álvarez", "Muñoz", "Romero", "Alonso", "Gutiérrez",
                                     "Silva", "Santos", "Ferreira", "Pereira", "Oliveira", "Costa", "Rodrigues", "Martins", "Sousa", "Carvalho"]
                        }
                    },
                    "Slavic": {
                        "countries": ["Russia", "Poland", "Ukraine", "Czech Republic", "Slovakia"],
                        "Male": {
                            "first": ["Ivan", "Dmitri", "Vladimir", "Sergei", "Alexei", "Nikolai", "Andrei", "Mikhail", "Aleksandr", "Pavel",
                                      "Boris", "Yuri", "Igor", "Oleg", "Viktor", "Konstantin", "Roman", "Anton", "Maxim", "Artem",
                                      "Piotr", "Wojciech", "Krzysztof", "Tomasz", "Marek", "Jan", "Jakub", "Kamil", "Adam", "Paweł",
                                      "Oleksandr", "Andriy", "Yuriy", "Bohdan", "Mykola", "Vasyl", "Taras", "Dmytro", "Petro", "Stepan"],
                            "last": ["Ivanov", "Petrov", "Sidorov", "Volkov", "Sokolov", "Lebedev", "Kozlov", "Novak", "Popov", "Smirnov",
                                     "Kowalski", "Nowak", "Wojcik", "Kowalczyk", "Lewandowski", "Zielinski", "Szymanski", "Wozniak", "Dąbrowski", "Krawczyk",
                                     "Shevchenko", "Kovalenko", "Bondarenko", "Tkachenko", "Melnyk", "Kravchenko", "Polishchuk", "Boyko", "Lysenko", "Marchenko"]
                        },
                        "Female": {
                            "first": ["Anna", "Maria", "Elena", "Natalia", "Olga", "Tatiana", "Irina", "Svetlana", "Ekaterina", "Anastasia",
                                      "Yulia", "Daria", "Victoria", "Alina", "Ksenia", "Polina", "Elizaveta", "Sofia", "Varvara", "Margarita",
                                      "Agnieszka", "Katarzyna", "Małgorzata", "Anna", "Magdalena", "Ewa", "Barbara", "Joanna", "Natalia", "Maria",
                                      "Oksana", "Olena", "Kateryna", "Iryna", "Natalia", "Tetyana", "Halyna", "Svitlana", "Lyudmyla", "Nina"],
                            "last": ["Ivanova", "Petrova", "Sidorova", "Volkova", "Sokolova", "Lebedeva", "Kozlova", "Novak", "Popova", "Smirnova",
                                     "Kowalska", "Nowak", "Wojcik", "Kowalczyk", "Lewandowska", "Zielinska", "Szymanska", "Wozniak", "Dąbrowska", "Krawczyk",
                                     "Shevchenko", "Kovalenko", "Bondarenko", "Tkachenko", "Melnyk", "Kravchenko", "Polishchuk", "Boyko", "Lysenko", "Marchenko"]
                        }
                    }
                }
            },
            "Hispanic/Latino": {
                "Male": {
                    "first": [
                        "Carlos", "Miguel", "Diego", "Luis", "Jose", "Juan", "Antonio", "Fernando", "Ricardo", "Alejandro",
                        "Javier", "Manuel", "Francisco", "Rafael", "Pedro", "Sergio", "Andres", "Jorge", "Eduardo", "Roberto",
                        "Pablo", "Raul", "Enrique", "Mauricio", "Oscar", "Cesar", "Ramon", "Alberto", "Hector", "Gustavo",
                        "Arturo", "Felipe", "Ernesto", "Rodrigo", "Gerardo", "Leonardo", "Ruben", "Adrian", "Marcos", "Daniel"
                    ],
                    "last": [
                        "Garcia", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Perez", "Sanchez", "Ramirez", "Torres",
                        "Rivera", "Gomez", "Diaz", "Cruz", "Morales", "Reyes", "Flores", "Jimenez", "Alvarez", "Romero",
                        "Castillo", "Gutierrez", "Mendoza", "Ruiz", "Vargas", "Castro", "Ortiz", "Ramos", "Vazquez", "Moreno",
                        "Herrera", "Silva", "Medina", "Aguilar", "Guerrero", "Rojas", "Pena", "Soto", "Delgado", "Campos"
                    ]
                },
                "Female": {
                    "first": [
                        "Maria", "Sofia", "Isabella", "Camila", "Valentina", "Lucia", "Elena", "Ana", "Carmen", "Rosa",
                        "Gabriela", "Daniela", "Andrea", "Fernanda", "Laura", "Paula", "Carolina", "Adriana", "Natalia", "Monica",
                        "Diana", "Patricia", "Veronica", "Alejandra", "Mariana", "Claudia", "Beatriz", "Teresa", "Silvia", "Alicia",
                        "Isabel", "Catalina", "Lorena", "Cecilia", "Marcela", "Paola", "Sandra", "Juliana", "Rocio", "Victoria"
                    ],
                    "last": [
                        "Garcia", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Perez", "Sanchez", "Ramirez", "Torres",
                        "Rivera", "Gomez", "Diaz", "Cruz", "Morales", "Reyes", "Flores", "Jimenez", "Alvarez", "Romero",
                        "Castillo", "Gutierrez", "Mendoza", "Ruiz", "Vargas", "Castro", "Ortiz", "Ramos", "Vazquez", "Moreno",
                        "Herrera", "Silva", "Medina", "Aguilar", "Guerrero", "Rojas", "Pena", "Soto", "Delgado", "Campos"
                    ]
                }
            },
            "Middle Eastern": {
                "regions": {
                    "Gulf_Arab": {
                        "countries": ["Saudi Arabia", "UAE", "Kuwait", "Qatar", "Bahrain", "Oman"],
                        "Male": {
                            "first": ["Mohammed", "Ahmed", "Abdullah", "Khalid", "Fahad", "Sultan", "Faisal", "Mansour", "Turki", "Rashid",
                                      "Abdulaziz", "Salman", "Nawaf", "Saud", "Majid", "Nasser", "Hamad", "Saeed", "Yousef", "Bandar",
                                      "Talal", "Waleed", "Mishal", "Mutlaq", "Nayef", "Omar", "Rakan", "Saqr", "Thamer", "Zayed",
                                      "Hamdan", "Rasheed", "Badr", "Fahd", "Jassim", "Khaled", "Mansoor", "Mubarak", "Saif", "Tariq"],
                            "last": ["Al-Saud", "Al-Otaibi", "Al-Dosari", "Al-Ghamdi", "Al-Zahrani", "Al-Qahtani", "Al-Mutairi", "Al-Harbi",
                                     "Al-Shammari", "Al-Rashid", "Al-Mansouri", "Al-Maktoum", "Al-Nahyan", "Al-Qasimi", "Al-Sabah", "Al-Thani",
                                     "Al-Marri", "Al-Kuwari", "Al-Khalifa", "Al-Said", "Bin Laden", "Bin Talal", "Bin Zayed", "Al-Faisal"]
                        },
                        "Female": {
                            "first": ["Noor", "Noura", "Fatima", "Aisha", "Maryam", "Sarah", "Hessa", "Amira", "Lulwa", "Shaikha",
                                      "Mahra", "Sheikha", "Latifa", "Maysa", "Reem", "Salma", "Haya", "Mozah", "Shamsa", "Moza",
                                      "Hind", "Jawahir", "Manal", "Nada", "Rania", "Wafa", "Abeer", "Buthaina", "Dalal", "Ghada",
                                      "Hanan", "Jamilah", "Karima", "Laila", "Maha", "Nadia", "Raghad", "Sama", "Wedad", "Yasmin"],
                            "last": ["Al-Saud", "Al-Otaibi", "Al-Dosari", "Al-Ghamdi", "Al-Zahrani", "Al-Qahtani", "Al-Mutairi", "Al-Harbi",
                                     "Al-Shammari", "Al-Rashid", "Al-Mansouri", "Al-Maktoum", "Al-Nahyan", "Al-Qasimi", "Al-Sabah", "Al-Thani",
                                     "Al-Marri", "Al-Kuwari", "Al-Khalifa", "Al-Said", "Bin Laden", "Bin Talal", "Bin Zayed", "Al-Faisal"]
                        }
                    },
                    "Levantine": {
                        "countries": ["Lebanon", "Syria", "Jordan", "Palestine"],
                        "Male": {
                            "first": ["Basel", "Fadi", "Rami", "Nabil", "Walid", "Tariq", "Jamil", "Sami", "Adel", "Imad",
                                      "Tarek", "Hatem", "Karim", "Marwan", "Wael", "Ziad", "Amjad", "Hani", "Maher", "Raed",
                                      "Samir", "Yasser", "Bilal", "Ghassan", "Hazem", "Ihab", "Jamal", "Kamal", "Mahmoud", "Nader",
                                      "Omar", "Qusay", "Rayan", "Salim", "Tamer", "Usama", "Wassim", "Yazid", "Zaki", "Adnan"],
                            "last": ["Haddad", "Khoury", "Bitar", "Harb", "Saleh", "Khalil", "Mansour", "Nasr", "Farah", "Abbas",
                                     "Said", "Aoun", "Gemayel", "Frangieh", "Jumblatt", "Salam", "Karami", "Mikati", "Safadi", "Assaf",
                                     "Hourani", "Masri", "Shaheen", "Atallah", "Karam", "Nasser", "Al-Assad", "Shami", "Halabi", "Hakim"]
                        },
                        "Female": {
                            "first": ["Lina", "Maya", "Reem", "Rana", "Dalia", "Sana", "Hiba", "Samar", "Duha", "Iman",
                                      "Nadine", "Jana", "Rawan", "Lama", "Suha", "Dina", "Mona", "Rim", "Hala", "Rasha",
                                      "Layla", "Yasmin", "Hana", "Sara", "Malak", "Nada", "Ghada", "Maha", "Sawsan", "Bushra",
                                      "Amal", "Farah", "Haneen", "Layan", "Nour", "Razan", "Sereen", "Tala", "Yara", "Zeina"],
                            "last": ["Haddad", "Khoury", "Bitar", "Harb", "Saleh", "Khalil", "Mansour", "Nasr", "Farah", "Abbas",
                                     "Said", "Aoun", "Gemayel", "Frangieh", "Jumblatt", "Salam", "Karami", "Mikati", "Safadi", "Assaf",
                                     "Hourani", "Masri", "Shaheen", "Atallah", "Karam", "Nasser", "Al-Assad", "Shami", "Halabi", "Hakim"]
                        }
                    },
                    "Egyptian_North_African": {
                        "countries": ["Egypt", "Libya", "Tunisia", "Algeria", "Morocco"],
                        "Male": {
                            "first": ["Mohamed", "Ahmed", "Mahmoud", "Ali", "Hassan", "Omar", "Youssef", "Ibrahim", "Mustafa", "Khaled",
                                      "Karim", "Amr", "Tamer", "Hossam", "Sherif", "Ashraf", "Wael", "Tarek", "Hany", "Ehab",
                                      "Magdy", "Samir", "Adel", "Hatem", "Gamal", "Reda", "Essam", "Ayman", "Basel", "Fady",
                                      "Yasser", "Walid", "Ramy", "Nader", "Hesham", "Salah", "Maged", "Hamza", "Medhat", "Sayed"],
                            "last": ["Abdel-Nasser", "El-Sayed", "Mohamed", "Ahmed", "Hassan", "Hussein", "Mahmoud", "Ali", "Ibrahim", "Abdallah",
                                     "Farouk", "Sadat", "Mubarak", "Morsi", "El-Masry", "El-Shazly", "El-Kady", "El-Sisi", "Fahmy", "Khalil",
                                     "Ben Ali", "Bouazizi", "Ghannouchi", "Bourguiba", "Bouteflika", "Zeroual", "Belkhadem", "Tebboune", "Hassan II", "Mohammed VI"]
                        },
                        "Female": {
                            "first": ["Fatima", "Mariam", "Zainab", "Aisha", "Nour", "Salma", "Heba", "Aya", "Yasmin", "Nada",
                                      "Rania", "Dina", "Mona", "Noha", "Rana", "Hala", "Samar", "Laila", "Amira", "Nesrine",
                                      "Eman", "Inas", "Nagwa", "Niveen", "Soha", "Yara", "Basma", "Dalia", "Ghada", "Hanan",
                                      "Maha", "Manal", "Nawal", "Rasha", "Samira", "Wafaa", "Amina", "Farida", "Khadija", "Malika"],
                            "last": ["Abdel-Nasser", "El-Sayed", "Mohamed", "Ahmed", "Hassan", "Hussein", "Mahmoud", "Ali", "Ibrahim", "Abdallah",
                                     "Farouk", "Sadat", "Mubarak", "Morsi", "El-Masry", "El-Shazly", "El-Kady", "El-Sisi", "Fahmy", "Khalil",
                                     "Ben Ali", "Bouazizi", "Ghannouchi", "Bourguiba", "Bouteflika", "Zeroual", "Belkhadem", "Tebboune", "Hassan II", "Mohammed VI"]
                        }
                    }
                }
            },
            "Native American": {
                "Male": {
                    "first": [
                        "Takoda", "Chayton", "Elan", "Ahanu", "Koda", "Tahoma", "Mato", "Nashoba", "Mikasi", "Waya",
                        "Ohiyesa", "Hanska", "Chaska", "Etu", "Honovi", "Kele", "Kohana", "Langundo", "Isi", "Nayati",
                        "Nodin", "Otaktay", "Paco", "Sakima", "Sani", "Tadi", "Takoda", "Totsi", "Tupi", "Yancy"
                    ],
                    "last": [
                        "Running Bear", "Black Elk", "Red Cloud", "Swift Eagle", "Little Wolf", "Sitting Bull", "Lone Wolf",
                        "White Horse", "Gray Eagle", "Thunder Hawk", "Brave Heart", "Red Hawk", "Standing Bear", "Walking Bear",
                        "Morning Star", "White Cloud", "Black Crow", "Big Bear", "Crazy Horse", "Strong Bow"
                    ]
                },
                "Female": {
                    "first": [
                        "Aiyana", "Kiona", "Tallulah", "Winona", "Cocheta", "Sahkyo", "Kaya", "Nita", "Taini", "Ayasha",
                        "Chenoa", "Donoma", "Halona", "Istas", "Keezheekoni", "Kimama", "Lomasi", "Mika", "Niabi", "Odina",
                        "Orenda", "Pocahontas", "Shada", "Tala", "Tayen", "Tuwa", "Weeko", "Yanaba", "Yoki", "Zonta"
                    ],
                    "last": [
                        "Running Bear", "Black Elk", "Red Cloud", "Swift Eagle", "Little Wolf", "Sitting Bull", "Lone Wolf",
                        "White Horse", "Gray Eagle", "Thunder Hawk", "Brave Heart", "Red Hawk", "Standing Bear", "Walking Bear",
                        "Morning Star", "White Cloud", "Black Crow", "Big Bear", "Crazy Horse", "Strong Bow"
                    ]
                }
            },
            "Pacific Islander": {
                "Male": {
                    "first": [
                        # Hawaiian names
                        "Keanu", "Koa", "Makoa", "Kai", "Kale", "Ikaika", "Kaleo", "Keoni", "Mana", "Noa",
                        "Kalani", "Kapono", "Kawika", "Manu", "Nalu", "Pono", "Teva",
                        # Samoan/Tongan names
                        "Tane", "Rangi", "Hoku", "Aolani", "Tavita", "Sione", "Pita", "Ioane", "Semisi", "Manaia",
                        # Maori names
                        "Tama", "Aroha", "Wiremu", "Hemi", "Matiu", "Hohepa"
                    ],
                    "last": [
                        # Hawaiian surnames
                        "Kealoha", "Kalani", "Kahale", "Mahoe", "Kamaka", "Lum", "Wong", "Nakamura",
                        # Samoan/Tongan surnames
                        "Tavita", "Tuiasosopo", "Fetu", "Moana", "Tui", "Palelei", "Sione", "Tonga", "Samoa",
                        # Maori surnames
                        "Pene", "Tamati", "Tipene", "Wiremu", "Ngata", "Henare"
                    ]
                },
                "Female": {
                    "first": [
                        # Hawaiian names
                        "Leilani", "Moana", "Nani", "Kailani", "Hina", "Alana", "Mahina", "Iolana", "Keahi", "Nalani",
                        "Kalena", "Luana", "Malia", "Noelani", "Olina", "Pua", "Ulani",
                        # Samoan/Tongan names
                        "Sina", "Mele", "Lupe", "Vaiola", "Teuila", "Lani", "Seini", "Ana", "Malia", "Fetu",
                        # Maori names
                        "Aroha", "Hine", "Kiri", "Mere", "Ani", "Wikitoria"
                    ],
                    "last": [
                        # Hawaiian surnames
                        "Kealoha", "Kalani", "Kahale", "Mahoe", "Kamaka", "Lum", "Wong", "Nakamura",
                        # Samoan/Tongan surnames
                        "Tavita", "Tuiasosopo", "Fetu", "Moana", "Tui", "Palelei", "Sione", "Tonga", "Samoa",
                        # Maori surnames
                        "Pene", "Tamati", "Tipene", "Wiremu", "Ngata", "Henare"
                    ]
                }
            },
            "Mixed": {
                "Male": {
                    "first": [
                        # Common mixed-ethnicity names
                        "Jordan", "Jayden", "Marcus", "Andre", "Malik", "Isaiah", "Xavier", "Elijah", "Cameron", "Derek",
                        "Darius", "Jamal", "Khalil", "Rashad", "Terrence", "Troy", "Wesley", "Desmond", "Malcolm", "Quincy",
                        "Jaden", "Kai", "Noah", "Elijah", "Liam", "Ethan", "Lucas", "Mason", "Logan", "Aiden",
                        "Ryan", "Kevin", "Brandon", "Justin", "Eric", "Daniel", "Adam", "Sean", "Brian", "Nathan"
                    ],
                    "last": [
                        "Washington", "Jackson", "Thompson", "Rivera", "Santos", "Mitchell", "Brooks", "Powell", "Foster", "Coleman",
                        "Bennett", "Hayes", "Bryant", "Alexander", "Russell", "Griffin", "Diaz", "Hayes", "Myers", "Ford",
                        "Hamilton", "Graham", "Sullivan", "Wallace", "Woods", "Cole", "West", "Jordan", "Owens", "Reynolds",
                        "Fisher", "Ellis", "Harrison", "Gibson", "McDonald", "Cruz", "Marshall", "Ortiz", "Gomez", "Murray"
                    ]
                },
                "Female": {
                    "first": [
                        # Common mixed-ethnicity names
                        "Maya", "Aaliyah", "Jasmine", "Kiara", "Bianca", "Sierra", "Gabriela", "Naomi", "Zara", "Anaya",
                        "Destiny", "Diamond", "Heaven", "India", "Jade", "Jada", "Kayla", "Keisha", "Latoya", "Shaniqua",
                        "Isabella", "Mia", "Ava", "Sophia", "Emma", "Olivia", "Emily", "Madison", "Chloe", "Abigail",
                        "Samantha", "Ashley", "Brianna", "Alyssa", "Hannah", "Sarah", "Jessica", "Taylor", "Rachel", "Lauren"
                    ],
                    "last": [
                        "Washington", "Jackson", "Thompson", "Rivera", "Santos", "Mitchell", "Brooks", "Powell", "Foster", "Coleman",
                        "Bennett", "Hayes", "Bryant", "Alexander", "Russell", "Griffin", "Diaz", "Hayes", "Myers", "Ford",
                        "Hamilton", "Graham", "Sullivan", "Wallace", "Woods", "Cole", "West", "Jordan", "Owens", "Reynolds",
                        "Fisher", "Ellis", "Harrison", "Gibson", "McDonald", "Cruz", "Marshall", "Ortiz", "Gomez", "Murray"
                    ]
                }
            }
        }

        # Randomly select biological sex and gender (can be different for some profiles)
        biological_sex = random.choice(["Male", "Female"])

        # 95% of the time gender matches biological sex
        if random.random() < 0.95:
            gender = biological_sex
        else:
            gender = random.choice(["Male", "Female", "Other", "Prefer not to say"])

        # Get names based on biological sex (for photo generation) and ethnicity
        # Use biological_sex for name selection to match photo appearance
        name_gender = biological_sex if biological_sex in ["Male", "Female"] else "Male"

        # Get appropriate names for ethnicity and gender WITH REGIONAL MATCHING
        # This ensures first names from a region are ONLY paired with last names from the SAME region
        # (e.g., Nigerian Igbo first name will only get Nigerian Igbo surname, never Kenyan or Ghanaian)

        if ethnicity_key in names_by_ethnicity_regional:
            ethnicity_data = names_by_ethnicity_regional[ethnicity_key]

            # Check if this ethnicity has regional structure
            if "regions" in ethnicity_data:
                # Pick a random region within this ethnicity
                regions = ethnicity_data["regions"]
                region_key = random.choice(list(regions.keys()))
                region_data = regions[region_key]

                # Get MATCHED first and last name from the SAME region
                first_name = random.choice(region_data[name_gender]["first"])
                last_name = random.choice(region_data[name_gender]["last"])

                # Middle name also from same region
                middle_name_pool = region_data[name_gender]["first"]
            else:
                # Old flat structure (for ethnicities not yet regionalized)
                first_name = random.choice(ethnicity_data[name_gender]["first"])
                last_name = random.choice(ethnicity_data[name_gender]["last"])
                middle_name_pool = ethnicity_data[name_gender]["first"]
        else:
            # Fallback to Mixed names if ethnicity not in dictionary
            if "Mixed" in names_by_ethnicity_regional and "regions" not in names_by_ethnicity_regional["Mixed"]:
                first_name = random.choice(names_by_ethnicity_regional["Mixed"][name_gender]["first"])
                last_name = random.choice(names_by_ethnicity_regional["Mixed"][name_gender]["last"])
                middle_name_pool = names_by_ethnicity_regional["Mixed"][name_gender]["first"]
            else:
                # Ultimate fallback
                first_name = "John" if name_gender == "Male" else "Jane"
                last_name = "Doe"
                middle_name_pool = [first_name]

        # Generate middle name (optional, 70% chance) from SAME region
        middle_name = ""
        if random.random() < 0.7:
            middle_name = random.choice(middle_name_pool)

        # Random demographics
        age = random.randint(25, 75)
        date_of_birth = datetime.now() - timedelta(days=365*age)

        # Random MRN
        mrn = f"MRN-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Random measurements based on biological sex (for realistic proportions)
        if biological_sex == "Male":
            height_cm = random.uniform(165, 190)
            weight_kg = random.uniform(65, 95)
        else:
            height_cm = random.uniform(155, 175)
            weight_kg = random.uniform(50, 80)

        bmi = weight_kg / ((height_cm / 100) ** 2)
        gender_uri = f"http://schema.org/{gender}"

        # Use MRN directly as ID
        patient_id = mrn

        # Generate diverse birth countries based on ethnicity
        birth_countries_by_ethnicity = {
            "African": ["Nigeria", "Kenya", "Ghana", "Ethiopia", "South Africa", "Egypt", "Morocco", "Tanzania", "Uganda", "Senegal"],
            "South Asian": ["India", "Pakistan", "Bangladesh", "Sri Lanka", "Nepal", "Bhutan", "Maldives"],
            "East Asian": ["China", "Japan", "South Korea", "Taiwan", "Hong Kong", "Mongolia"],
            "Southeast Asian": ["Vietnam", "Thailand", "Philippines", "Indonesia", "Malaysia", "Singapore", "Myanmar", "Cambodia", "Laos"],
            "Caucasian/European": ["USA", "UK", "Germany", "France", "Italy", "Spain", "Poland", "Netherlands", "Belgium", "Sweden"],
            "Hispanic/Latino": ["Mexico", "Colombia", "Argentina", "Peru", "Venezuela", "Chile", "Ecuador", "Guatemala", "Cuba", "Dominican Republic"],
            "Middle Eastern": ["Saudi Arabia", "UAE", "Egypt", "Turkey", "Iran", "Iraq", "Jordan", "Lebanon", "Syria", "Morocco"],
            "Native American": ["USA", "Canada", "Mexico", "Guatemala", "Peru"],
            "Pacific Islander": ["Hawaii", "Samoa", "Tonga", "Fiji", "New Zealand", "Tahiti", "Guam"],
            "Mixed": ["USA", "Canada", "UK", "Brazil", "South Africa", "Australia"]
        }

        birth_country = random.choice(birth_countries_by_ethnicity.get(ethnicity_key, ["USA"]))

        # Generate diverse birth and current cities
        # COMPREHENSIVE city coverage for unique profile generation
        cities_by_country = {
            # North America
            "USA": ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose",
                    "Austin", "Jacksonville", "San Francisco", "Indianapolis", "Columbus", "Fort Worth", "Charlotte", "Seattle", "Denver", "Boston",
                    "Detroit", "Nashville", "Portland", "Las Vegas", "Memphis", "Louisville", "Baltimore", "Milwaukee", "Albuquerque", "Tucson"],
            "Canada": ["Toronto", "Vancouver", "Montreal", "Calgary", "Edmonton", "Ottawa", "Winnipeg", "Quebec City", "Hamilton", "Kitchener"],
            "Mexico": ["Mexico City", "Guadalajara", "Monterrey", "Puebla", "Tijuana", "Cancun", "Mérida", "León", "Querétaro", "San Luis Potosí"],

            # Europe
            "Belgium": ["Brussels", "Antwerp", "Ghent", "Bruges", "Liège", "Namur", "Leuven", "Charleroi", "Mons", "Hasselt"],
            "UK": ["London", "Manchester", "Birmingham", "Leeds", "Glasgow", "Liverpool", "Newcastle", "Sheffield", "Bristol", "Edinburgh"],
            "Germany": ["Berlin", "Munich", "Hamburg", "Frankfurt", "Cologne", "Stuttgart", "Düsseldorf", "Dortmund", "Essen", "Leipzig"],
            "France": ["Paris", "Marseille", "Lyon", "Toulouse", "Nice", "Nantes", "Strasbourg", "Montpellier", "Bordeaux", "Lille"],
            "Italy": ["Rome", "Milan", "Naples", "Turin", "Palermo", "Genoa", "Bologna", "Florence", "Bari", "Venice"],
            "Spain": ["Madrid", "Barcelona", "Valencia", "Seville", "Zaragoza", "Málaga", "Murcia", "Palma", "Bilbao", "Alicante"],
            "Netherlands": ["Amsterdam", "Rotterdam", "The Hague", "Utrecht", "Eindhoven", "Tilburg", "Groningen", "Almere", "Breda", "Nijmegen"],
            "Poland": ["Warsaw", "Kraków", "Łódź", "Wrocław", "Poznań", "Gdańsk", "Szczecin", "Bydgoszcz", "Lublin", "Katowice"],
            "Russia": ["Moscow", "St. Petersburg", "Novosibirsk", "Yekaterinburg", "Kazan", "Nizhny Novgorod", "Chelyabinsk", "Samara", "Omsk", "Rostov-on-Don"],
            "Sweden": ["Stockholm", "Gothenburg", "Malmö", "Uppsala", "Västerås", "Örebro", "Linköping", "Helsingborg"],

            # Africa
            "Nigeria": ["Lagos", "Abuja", "Kano", "Ibadan", "Port Harcourt", "Benin City", "Kaduna", "Enugu", "Onitsha", "Jos"],
            "Kenya": ["Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret", "Thika", "Malindi", "Kakamega", "Meru", "Nyeri"],
            "Ghana": ["Accra", "Kumasi", "Tamale", "Sekondi-Takoradi", "Ashaman", "Sunyani", "Cape Coast", "Obuasi"],
            "Ethiopia": ["Addis Ababa", "Dire Dawa", "Mekelle", "Gondar", "Hawassa", "Bahir Dar", "Adama", "Jimma"],
            "South Africa": ["Johannesburg", "Cape Town", "Durban", "Pretoria", "Port Elizabeth", "Bloemfontein", "Soweto", "Pietermaritzburg"],
            "Egypt": ["Cairo", "Alexandria", "Giza", "Shubra El Kheima", "Port Said", "Suez", "Luxor", "Aswan", "Mansoura", "Tanta"],
            "Morocco": ["Casablanca", "Rabat", "Fes", "Marrakech", "Agadir", "Tangier", "Meknes", "Oujda", "Kenitra"],

            # South Asia
            "India": ["Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai", "Kolkata", "Pune", "Ahmedabad", "Jaipur", "Surat",
                      "Lucknow", "Kanpur", "Nagpur", "Indore", "Bhopal", "Visakhapatnam", "Patna", "Vadodara", "Ludhiana", "Agra"],
            "Pakistan": ["Karachi", "Lahore", "Islamabad", "Rawalpindi", "Faisalabad", "Multan", "Peshawar", "Quetta", "Sialkot", "Gujranwala"],
            "Bangladesh": ["Dhaka", "Chittagong", "Khulna", "Rajshahi", "Sylhet", "Barisal", "Rangpur", "Comilla", "Mymensingh", "Narayanganj"],
            "Sri Lanka": ["Colombo", "Kandy", "Galle", "Jaffna", "Negombo", "Trincomalee", "Batticaloa", "Kurunegala", "Matara"],

            # East Asia
            "China": ["Beijing", "Shanghai", "Guangzhou", "Shenzhen", "Chengdu", "Hangzhou", "Wuhan", "Xi'an", "Tianjin", "Nanjing",
                      "Chongqing", "Suzhou", "Dongguan", "Shenyang", "Dalian", "Qingdao", "Harbin", "Zhengzhou", "Changsha", "Kunming"],
            "Japan": ["Tokyo", "Osaka", "Kyoto", "Yokohama", "Nagoya", "Sapporo", "Fukuoka", "Kobe", "Kawasaki", "Saitama",
                      "Hiroshima", "Sendai", "Kitakyushu", "Chiba", "Niigata", "Hamamatsu", "Kumamoto", "Okayama", "Kagoshima"],
            "South Korea": ["Seoul", "Busan", "Incheon", "Daegu", "Daejeon", "Gwangju", "Suwon", "Ulsan", "Changwon", "Goyang"],
            "Taiwan": ["Taipei", "Kaohsiung", "Taichung", "Tainan", "Hsinchu", "Keelung", "Chiayi", "Changhua"],
            "Hong Kong": ["Hong Kong", "Kowloon", "Tsuen Wan", "Sha Tin", "Tuen Mun", "Yuen Long"],
            "Mongolia": ["Ulaanbaatar", "Erdenet", "Darkhan", "Choibalsan"],

            # Southeast Asia
            "Vietnam": ["Ho Chi Minh City", "Hanoi", "Da Nang", "Hue", "Can Tho", "Bien Hoa", "Nha Trang", "Hải Phòng", "Buôn Ma Thuột", "Vung Tau"],
            "Thailand": ["Bangkok", "Chiang Mai", "Phuket", "Pattaya", "Krabi", "Hat Yai", "Nakhon Ratchasima", "Khon Kaen", "Udon Thani", "Chiang Rai"],
            "Philippines": ["Manila", "Quezon City", "Davao", "Cebu", "Makati", "Zamboanga", "Pasig", "Cagayan de Oro", "Bacolod", "Iloilo"],
            "Indonesia": ["Jakarta", "Surabaya", "Bandung", "Medan", "Bali", "Semarang", "Palembang", "Makassar", "Yogyakarta", "Malang"],
            "Malaysia": ["Kuala Lumpur", "Penang", "Johor Bahru", "Ipoh", "Malacca", "Kuching", "Kota Kinabalu", "Petaling Jaya", "Shah Alam", "Klang"],
            "Singapore": ["Singapore"],
            "Myanmar": ["Yangon", "Mandalay", "Naypyidaw", "Bago", "Mawlamyine", "Pathein"],
            "Cambodia": ["Phnom Penh", "Siem Reap", "Battambang", "Sihanoukville", "Kampong Cham"],
            "Laos": ["Vientiane", "Pakse", "Savannakhet", "Luang Prabang"],

            # Middle East
            "Saudi Arabia": ["Riyadh", "Jeddah", "Mecca", "Medina", "Dammam", "Khobar", "Tabuk", "Buraidah", "Khamis Mushait", "Hofuf"],
            "UAE": ["Dubai", "Abu Dhabi", "Sharjah", "Al Ain", "Ajman", "Ras Al Khaimah", "Fujairah"],
            "Turkey": ["Istanbul", "Ankara", "Izmir", "Bursa", "Adana", "Gaziantep", "Konya", "Antalya", "Kayseri", "Mersin"],
            "Iran": ["Tehran", "Mashhad", "Isfahan", "Karaj", "Tabriz", "Shiraz", "Qom", "Ahvaz", "Kermanshah", "Urmia"],
            "Iraq": ["Baghdad", "Basra", "Mosul", "Erbil", "Sulaymaniyah", "Najaf", "Karbala", "Kirkuk"],
            "Jordan": ["Amman", "Zarqa", "Irbid", "Aqaba", "Madaba", "Jerash", "Petra"],
            "Lebanon": ["Beirut", "Tripoli", "Sidon", "Tyre", "Jounieh", "Zahle", "Baalbek"],
            "Syria": ["Damascus", "Aleppo", "Homs", "Latakia", "Hama", "Deir ez-Zor"],
            "Yemen": ["Sana'a", "Aden", "Taiz", "Hodeidah", "Ibb", "Mukalla"],

            # Latin America
            "Colombia": ["Bogotá", "Medellín", "Cali", "Barranquilla", "Cartagena", "Cúcuta", "Bucaramanga", "Pereira", "Manizales"],
            "Argentina": ["Buenos Aires", "Córdoba", "Rosario", "Mendoza", "La Plata", "Tucumán", "Mar del Plata", "Salta", "Santa Fe"],
            "Peru": ["Lima", "Arequipa", "Trujillo", "Chiclayo", "Piura", "Iquitos", "Cusco", "Huancayo"],
            "Venezuela": ["Caracas", "Maracaibo", "Valencia", "Barquisimeto", "Maracay", "Ciudad Guayana", "Maturín"],
            "Chile": ["Santiago", "Valparaíso", "Concepción", "La Serena", "Antofagasta", "Temuco", "Rancagua", "Viña del Mar"],
            "Ecuador": ["Quito", "Guayaquil", "Cuenca", "Santo Domingo", "Machala", "Manta", "Portoviejo"],
            "Guatemala": ["Guatemala City", "Mixco", "Villa Nueva", "Quetzaltenango", "Escuintla"],
            "Cuba": ["Havana", "Santiago de Cuba", "Camagüey", "Holguín", "Santa Clara", "Guantánamo"],
            "Dominican Republic": ["Santo Domingo", "Santiago", "La Romana", "San Pedro de Macorís", "Puerto Plata"],
            "Brazil": ["São Paulo", "Rio de Janeiro", "Brasília", "Salvador", "Fortaleza", "Belo Horizonte", "Manaus", "Curitiba", "Recife", "Porto Alegre"],

            # Oceania
            "Australia": ["Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide", "Gold Coast", "Newcastle", "Canberra", "Wollongong", "Hobart"],
            "New Zealand": ["Auckland", "Wellington", "Christchurch", "Hamilton", "Tauranga", "Dunedin", "Palmerston North", "Napier"],

            # Pacific Islands
            "Hawaii": ["Honolulu", "Hilo", "Kailua", "Kaneohe", "Waipahu", "Pearl City", "Waimalu", "Kahului"],
            "Samoa": ["Apia", "Vaitele", "Faleula", "Siusega"],
            "Tonga": ["Nuku'alofa", "Neiafu", "Haveluloto", "Vaini"],
            "Fiji": ["Suva", "Nadi", "Lautoka", "Labasa", "Ba"],
            "Tahiti": ["Papeete", "Faaa", "Punaauia", "Pirae"],
            "Guam": ["Hagåtña", "Dededo", "Tamuning", "Mangilao", "Yigo"],
        }

        # Birth city based on birth country
        birth_city = random.choice(cities_by_country.get(birth_country, [birth_country]))

        # Current location (60% chance same as birth, 40% migrated)
        if random.random() < 0.6:
            current_country = birth_country
            current_city = birth_city
        else:
            # Migrated - common destinations
            current_country = random.choice(["Belgium", "USA", "UK", "Germany", "Canada", "Australia"])
            current_city = random.choice(cities_by_country.get(current_country, [current_country]))

        # Generate contact information
        phone = f"+{random.randint(1, 99)}-{random.randint(100, 999)}-{random.randint(1000000, 9999999)}"
        email = f"{first_name.lower()}.{last_name.lower().replace(' ', '')}@example.com"

        # Emergency contact
        emergency_contact_names = {
            "Male": ["spouse", "partner", "brother", "father", "son"],
            "Female": ["spouse", "partner", "sister", "mother", "daughter"]
        }
        emergency_relation = random.choice(emergency_contact_names.get(biological_sex, ["spouse"]))
        emergency_contact = f"{first_name}'s {emergency_relation}"
        emergency_phone = f"+{random.randint(1, 99)}-{random.randint(100, 999)}-{random.randint(1000000, 9999999)}"

        # Address and postal code
        address = f"{random.randint(1, 9999)} {random.choice(['Main', 'Oak', 'Maple', 'Cedar', 'Elm', 'Pine', 'Washington', 'Park', 'Lake'])} {random.choice(['Street', 'Avenue', 'Road', 'Boulevard', 'Lane', 'Drive'])}"
        postal_code = f"{random.randint(1000, 9999)}"

        # Language based on birth country
        languages_by_country = {
            "Belgium": "Dutch",
            "France": "French",
            "Germany": "German",
            "Spain": "Spanish",
            # South Asian languages
            "India": "Hindi",
            "Pakistan": "Urdu",
            "Bangladesh": "Bengali",
            "Sri Lanka": "English",  # Official languages: Sinhala/Tamil, but English widely used
            # East Asian languages
            "China": "Chinese",
            "Japan": "Japanese",
            "South Korea": "Korean",
            "Taiwan": "Chinese",
            "Hong Kong": "Chinese",
            # Southeast Asian languages
            "Vietnam": "Vietnamese",
            "Thailand": "Thai",
            "Philippines": "English",  # Filipino/Tagalog and English are official
            "Indonesia": "Bahasa Indonesia",
            "Malaysia": "Bahasa Melayu",
            "Singapore": "English",
            "Myanmar": "Burmese",
            # Other
            "Mexico": "Spanish",
            "Brazil": "Portuguese",
            "Saudi Arabia": "Arabic",
            "Egypt": "Arabic",
            "Nigeria": "English",
            "Kenya": "English"
        }
        language = languages_by_country.get(birth_country, "English")
        interpreter_needed = language not in ["English", "Dutch", "French", "German"] and random.random() < 0.3

        # Insurance information (70% have insurance)
        if random.random() < 0.7:
            insurance_providers = ["Blue Cross", "Aetna", "United Healthcare", "Cigna", "Humana", "Kaiser Permanente", "Medicare", "Medicaid"]
            insurance_provider = random.choice(insurance_providers)
            insurance_policy = f"{random.choice(['BC', 'AE', 'UH', 'CI', 'HM', 'KP'])}-{random.randint(100000, 999999)}"
        else:
            insurance_provider = ""
            insurance_policy = ""

        # Primary care physician
        pcp_names = ["Dr. Smith", "Dr. Johnson", "Dr. Williams", "Dr. Brown", "Dr. Jones", "Dr. Garcia", "Dr. Martinez", "Dr. Lee", "Dr. Patel", "Dr. Kim"]
        pcp_name = random.choice(pcp_names)
        pcp_contact = f"+{random.randint(1, 99)}-{random.randint(100, 999)}-{random.randint(1000000, 9999999)}"

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
                    "schema:additionalName": middle_name,
                    "preferredName": first_name,
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

        # Add top-level demographics shortcut (for compatibility with other components)
        patient_profile['demographics'] = {
            'first_name': first_name,
            'last_name': last_name,
            'middle_name': middle_name,
            'preferred_name': first_name,
            'mrn': mrn,
            'age': age,
            'gender': gender,
            'biological_sex': biological_sex,
            'date_of_birth': date_of_birth.isoformat(),
            'ethnicity': ethnicity,
            'birth_city': birth_city,
            'birth_country': birth_country,
            'current_city': current_city,
            'current_country': current_country,
            'address': address,
            'postal_code': postal_code,
            'phone': phone,
            'email': email,
            'emergency_contact': emergency_contact,
            'emergency_phone': emergency_phone,
            'language': language,
            'interpreter_needed': interpreter_needed,
            'insurance_provider': insurance_provider,
            'insurance_policy': insurance_policy,
            'pcp_name': pcp_name,
            'pcp_contact': pcp_contact,
            'height': height_cm,
            'weight': weight_kg,
            'bmi': round(bmi, 1)
        }

        # Generate AI photo if requested
        if generate_ai_photo:
            try:
                import sys
                from pathlib import Path
                sys.path.append(str(Path(__file__).parent.parent))
                # Ensure we reload the latest AI photo generator code on reruns
                import importlib
                import utils.ai_photo_generator as _ai_pg
                importlib.reload(_ai_pg)
                AIPhotoGenerator = _ai_pg.AIPhotoGenerator

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
        
        # Exercise frequency - dynamically look up SNOMED codes
        exercise_options = [
            {
                "@type": "sdisco:LifestyleFactor",
                "factor_type": "exercise",
                "rdfs:label": "Regular exercise",
                "skos:prefLabel": "Regular exercise",
                "frequency": f"{random.randint(2, 7)} times/week",
                "note": "May improve drug metabolism",
                "search_term": "regular exercise"
            },
            {
                "@type": "sdisco:LifestyleFactor",
                "factor_type": "exercise",
                "rdfs:label": "Sedentary lifestyle",
                "skos:prefLabel": "Sedentary lifestyle",
                "frequency": "Minimal physical activity",
                "note": "May affect drug distribution",
                "search_term": "sedentary lifestyle"
            }
        ]
        exercise_choice = random.choice(exercise_options)
        
        # Dynamically look up SNOMED code for the selected exercise factor
        search_term = exercise_choice.pop("search_term", exercise_choice.get("rdfs:label", ""))
        snomed_result = self.clinical_generator.search_snomed_term(search_term) if hasattr(self, 'clinical_generator') else None
        
        if snomed_result and snomed_result.get("snomed:code"):
            exercise_choice["snomed:code"] = snomed_result["snomed:code"]
            exercise_choice["@id"] = snomed_result.get("@id", f"http://snomed.info/id/{snomed_result['snomed:code']}")
            # Update label if SNOMED has a better one
            if snomed_result.get("rdfs:label"):
                exercise_choice["rdfs:label"] = snomed_result["rdfs:label"]
                exercise_choice["skos:prefLabel"] = snomed_result["rdfs:label"]
        
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
                    "@id": "http://snomed.info/id/365757006",
                    "snomed:code": "365757006",
                    "rdfs:label": "Serum creatinine measurement",
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
                    "@id": "http://snomed.info/id/365787000",
                    "snomed:code": "365787000",
                    "rdfs:label": "Serum bilirubin level",
                    "value": bilirubin_total,
                    "unit": "mg/dL",
                    "date": test_date,
                    "normal_range": "0.1-1.2 mg/dL",
                    "status": "normal" if bilirubin_total <= 1.2 else "elevated"
                }
            },
            "note": "Critical for drug dosing - particularly important for drugs cleared by kidney/liver"
        }
