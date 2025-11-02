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
        # Weights balance global demographics with testing diversity (e.g., Pacific Islander ~0.1% globally, not 12.5%)
        ethnicity_options = [
            "Asian",              # 35% - reflects ~59% global population (reduced for more diversity)
            "Caucasian/European", # 20% - reflects ~16% global population (reduced from previous 45% bias)
            "African",            # 17% - reflects ~17% global population
            "Hispanic/Latino",    # 13% - reflects ~8% global population
            "Middle Eastern",     # 7%  - reflects ~5% global population
            "Mixed",              # 5%  - ensures diverse mixed-ethnicity representation
            "Native American",    # 2%  - reflects <1% global population
            "Pacific Islander"    # 1%  - reflects <0.5% global population
        ]

        ethnicity_weights = [0.35, 0.20, 0.17, 0.13, 0.07, 0.05, 0.02, 0.01]

        # Select ethnicity based on weighted probabilities (not uniform!)
        ethnicity = [random.choices(ethnicity_options, weights=ethnicity_weights, k=1)[0]]
        ethnicity_key = ethnicity[0]

        # Diverse names by ethnicity and gender
        names_by_ethnicity = {
            "African": {
                "Male": {
                    "first": ["Kwame", "Jabari", "Kofi", "Ade", "Chike", "Tunde", "Sekou", "Amadi", "Themba", "Zuri"],
                    "last": ["Okafor", "Mensah", "Adeyemi", "Kamara", "Nkrumah", "Diallo", "Banda", "Mwangi", "Ngozi", "Okeke"]
                },
                "Female": {
                    "first": ["Amara", "Zola", "Nia", "Ayana", "Safiya", "Kaya", "Thandiwe", "Imani", "Asha", "Nala"],
                    "last": ["Okafor", "Mensah", "Adeyemi", "Kamara", "Nkrumah", "Diallo", "Banda", "Mwangi", "Ngozi", "Okeke"]
                }
            },
            "Asian": {
                "Male": {
                    "first": ["Wei", "Hiroshi", "Min-jun", "Raj", "Arjun", "Chen", "Kenji", "Ravi", "Jin", "Ankit"],
                    "last": ["Wang", "Tanaka", "Kim", "Patel", "Singh", "Li", "Yamamoto", "Chen", "Park", "Kumar"]
                },
                "Female": {
                    "first": ["Mei", "Yuki", "Ji-woo", "Priya", "Aisha", "Lin", "Sakura", "Suki", "Devi", "Hana"],
                    "last": ["Wang", "Tanaka", "Kim", "Patel", "Singh", "Li", "Yamamoto", "Chen", "Park", "Kumar"]
                }
            },
            "Caucasian/European": {
                "Male": {
                    "first": ["James", "William", "Thomas", "Oliver", "Alexander", "Henry", "Charles", "Daniel", "Lucas", "Michael"],
                    "last": ["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Wilson", "Anderson", "Taylor"]
                },
                "Female": {
                    "first": ["Emma", "Olivia", "Sophia", "Charlotte", "Amelia", "Isabella", "Mia", "Evelyn", "Harper", "Emily"],
                    "last": ["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Wilson", "Anderson", "Taylor"]
                }
            },
            "Hispanic/Latino": {
                "Male": {
                    "first": ["Carlos", "Miguel", "Diego", "Luis", "Jose", "Juan", "Antonio", "Fernando", "Ricardo", "Alejandro"],
                    "last": ["Garcia", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Perez", "Sanchez", "Ramirez", "Torres"]
                },
                "Female": {
                    "first": ["Maria", "Sofia", "Isabella", "Camila", "Valentina", "Lucia", "Elena", "Ana", "Carmen", "Rosa"],
                    "last": ["Garcia", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Perez", "Sanchez", "Ramirez", "Torres"]
                }
            },
            "Middle Eastern": {
                "Male": {
                    "first": ["Omar", "Ali", "Hassan", "Ahmed", "Yusuf", "Khalil", "Rashid", "Tariq", "Karim", "Samir"],
                    "last": ["Al-Masri", "Al-Rashid", "Al-Farsi", "Al-Mansour", "Al-Hassan", "Al-Jabbar", "Al-Sayed", "Al-Najjar", "Al-Amin", "Al-Hakim"]
                },
                "Female": {
                    "first": ["Layla", "Fatima", "Zainab", "Aisha", "Noor", "Yasmin", "Mariam", "Amina", "Hana", "Salma"],
                    "last": ["Al-Masri", "Al-Rashid", "Al-Farsi", "Al-Mansour", "Al-Hassan", "Al-Jabbar", "Al-Sayed", "Al-Najjar", "Al-Amin", "Al-Hakim"]
                }
            },
            "Native American": {
                "Male": {
                    "first": ["Takoda", "Chayton", "Elan", "Ahanu", "Koda", "Tahoma", "Mato", "Nashoba", "Mikasi", "Waya"],
                    "last": ["Running Bear", "Black Elk", "Red Cloud", "Swift Eagle", "Little Wolf", "Sitting Bull", "Lone Wolf", "White Horse", "Gray Eagle", "Thunder Hawk"]
                },
                "Female": {
                    "first": ["Aiyana", "Kiona", "Tallulah", "Winona", "Cocheta", "Sahkyo", "Kaya", "Nita", "Taini", "Ayasha"],
                    "last": ["Running Bear", "Black Elk", "Red Cloud", "Swift Eagle", "Little Wolf", "Sitting Bull", "Lone Wolf", "White Horse", "Gray Eagle", "Thunder Hawk"]
                }
            },
            "Pacific Islander": {
                "Male": {
                    "first": ["Keanu", "Koa", "Makoa", "Tane", "Rangi", "Mana", "Kai", "Aolani", "Hoku", "Ikaika"],
                    "last": ["Kealoha", "Kalani", "Kahale", "Mahoe", "Nakamura", "Tavita", "Tuiasosopo", "Fetu", "Moana", "Tui"]
                },
                "Female": {
                    "first": ["Leilani", "Moana", "Nani", "Kailani", "Hina", "Alana", "Mahina", "Iolana", "Keahi", "Nalani"],
                    "last": ["Kealoha", "Kalani", "Kahale", "Mahoe", "Nakamura", "Tavita", "Tuiasosopo", "Fetu", "Moana", "Tui"]
                }
            },
            "Mixed": {
                "Male": {
                    "first": ["Jordan", "Jayden", "Marcus", "Andre", "Malik", "Isaiah", "Xavier", "Elijah", "Cameron", "Derek"],
                    "last": ["Washington", "Jackson", "Thompson", "Rivera", "Santos", "Mitchell", "Brooks", "Powell", "Foster", "Coleman"]
                },
                "Female": {
                    "first": ["Maya", "Aaliyah", "Jasmine", "Kiara", "Bianca", "Sierra", "Gabriela", "Naomi", "Zara", "Anaya"],
                    "last": ["Washington", "Jackson", "Thompson", "Rivera", "Santos", "Mitchell", "Brooks", "Powell", "Foster", "Coleman"]
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

        # Get appropriate names for ethnicity and gender
        if ethnicity_key in names_by_ethnicity:
            first_name = random.choice(names_by_ethnicity[ethnicity_key][name_gender]["first"])
            last_name = random.choice(names_by_ethnicity[ethnicity_key][name_gender]["last"])
        else:
            # Fallback to Mixed names if ethnicity not in dictionary
            first_name = random.choice(names_by_ethnicity["Mixed"][name_gender]["first"])
            last_name = random.choice(names_by_ethnicity["Mixed"][name_gender]["last"])

        # Generate middle name (optional, 70% chance)
        middle_name = ""
        if random.random() < 0.7:
            if ethnicity_key in names_by_ethnicity:
                middle_name = random.choice(names_by_ethnicity[ethnicity_key][name_gender]["first"])
            else:
                middle_name = random.choice(names_by_ethnicity["Mixed"][name_gender]["first"])

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
            "Asian": ["China", "India", "Japan", "South Korea", "Pakistan", "Bangladesh", "Vietnam", "Thailand", "Philippines", "Indonesia"],
            "Caucasian/European": ["USA", "UK", "Germany", "France", "Italy", "Spain", "Poland", "Netherlands", "Belgium", "Sweden"],
            "Hispanic/Latino": ["Mexico", "Colombia", "Argentina", "Peru", "Venezuela", "Chile", "Ecuador", "Guatemala", "Cuba", "Dominican Republic"],
            "Middle Eastern": ["Saudi Arabia", "UAE", "Egypt", "Turkey", "Iran", "Iraq", "Jordan", "Lebanon", "Syria", "Morocco"],
            "Native American": ["USA", "Canada", "Mexico", "Guatemala", "Peru"],
            "Pacific Islander": ["Hawaii", "Samoa", "Tonga", "Fiji", "New Zealand", "Tahiti", "Guam"],
            "Mixed": ["USA", "Canada", "UK", "Brazil", "South Africa", "Australia"]
        }

        birth_country = random.choice(birth_countries_by_ethnicity.get(ethnicity_key, ["USA"]))

        # Generate diverse birth and current cities
        cities_by_country = {
            "USA": ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose"],
            "Belgium": ["Brussels", "Antwerp", "Ghent", "Bruges", "Liège", "Namur", "Leuven"],
            "Nigeria": ["Lagos", "Abuja", "Kano", "Ibadan", "Port Harcourt"],
            "Kenya": ["Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret"],
            "India": ["Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai", "Kolkata", "Pune"],
            "China": ["Beijing", "Shanghai", "Guangzhou", "Shenzhen", "Chengdu", "Hangzhou"],
            "Mexico": ["Mexico City", "Guadalajara", "Monterrey", "Puebla", "Tijuana"],
            # Add more as needed...
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
            "China": "Chinese",
            "Japan": "Japanese",
            "India": "Hindi",
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
