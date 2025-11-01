"""
Patient Core Data Loader - SCHEMA ALIGNED
Handles: patients, demographics
"""

import json
import logging
from datetime import datetime
from typing import Dict
import psycopg
from .utils import parse_date


class PatientCoreLoader:
    """Loads patient core data (patients and demographics)"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def load_all(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """Load all patient core data"""
        count = 0
        count += self.insert_patient(cursor, profile)
        count += self.insert_demographics(cursor, profile)
        return count
    
    def insert_patient(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """Insert patient record"""
        try:
            patient_id = profile.get("patient_id")
            if not patient_id:
                self.logger.error("No patient_id found in profile")
                return 0
            
            cursor.execute("""
                INSERT INTO patients (
                    patient_id, name, description, dashboard_source, date_created,
                    data_version, total_critical_conflicts, provenance_source,
                    provenance_date, rdf_context
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (patient_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    total_critical_conflicts = EXCLUDED.total_critical_conflicts,
                    provenance_date = EXCLUDED.provenance_date
            """, (
                patient_id,
                profile.get("name"),
                profile.get("description"),
                profile.get("dashboard_source", True),
                parse_date(profile.get("dateCreated")),
                profile.get("data_version", 1),
                profile.get("total_critical_conflicts", 0),
                "PGx Dashboard",
                datetime.now(),
                json.dumps(profile.get("@context"))
            ))
            self.logger.info(f"✓ Inserted patient {patient_id}")
            return 1
        except Exception as e:
            self.logger.error(f"Could not insert patient: {e}")
            return 0
    
    def insert_demographics(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """
        ✅ SCHEMA-ALIGNED: Insert patient demographics
        Fixed column names: emergency_contact, birth_place_city, birth_place_country, policy_number, race, current_address
        """
        try:
            patient_id = profile.get("patient_id")
            demographics = profile.get("clinical_information", {}).get("demographics", {})
            
            if not demographics:
                return 0
            
            # Extract ethnicity data
            ethnicity = demographics.get("ethnicity", [])
            ethnicity_snomed_labels = []
            ethnicity_snomed = profile.get("clinical_information", {}).get("ethnicity_snomed", [])
            for e in ethnicity_snomed:
                ethnicity_snomed_labels.append(e.get("label", ""))
            
            # Extract location and contact
            current_location = demographics.get("current_location", {})
            contact = demographics.get("contact", {})
            insurance = demographics.get("insurance", {})
            pcp = demographics.get("pcp", {})
            birth_place = demographics.get("schema:birthPlace", {})
            weight = demographics.get("schema:weight", {})
            height = demographics.get("schema:height", {})
            
            # SCHEMA-ALIGNED column names
            cursor.execute("""
                INSERT INTO demographics (
                    patient_id, first_name, last_name, additional_name, preferred_name,
                    birth_date, age, biological_sex, gender, ethnicity, ethnicity_snomed_labels,
                    race, birth_place_city, birth_place_country,
                    weight_kg, height_cm, bmi,
                    current_address, current_city, current_country, postal_code,
                    phone, email,
                    emergency_contact, emergency_phone,
                    language, interpreter_needed,
                    insurance_provider, policy_number,
                    pcp_name, pcp_contact, note
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (patient_id) DO UPDATE SET
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    age = EXCLUDED.age,
                    weight_kg = EXCLUDED.weight_kg,
                    height_cm = EXCLUDED.height_cm,
                    bmi = EXCLUDED.bmi
            """, (
                patient_id,
                demographics.get("foaf:firstName") or demographics.get("schema:givenName"),
                demographics.get("foaf:familyName") or demographics.get("schema:familyName"),
                demographics.get("schema:additionalName"),
                demographics.get("preferredName"),
                parse_date(demographics.get("schema:birthDate")),
                demographics.get("age"),
                demographics.get("biological_sex"),
                demographics.get("schema:gender"),
                json.dumps(ethnicity) if ethnicity else None,
                json.dumps(ethnicity_snomed_labels) if ethnicity_snomed_labels else None,
                # FIXED: Schema uses 'race'
                None,  # race - not in current profile
                # FIXED: Schema has birth_place_city and birth_place_country
                birth_place.get("city"),  # birth_place_city
                birth_place.get("country"),  # birth_place_country
                weight.get("schema:value"),
                height.get("schema:value"),
                demographics.get("bmi"),
                # FIXED: Schema has current_address as separate field
                current_location.get("address"),  # current_address
                current_location.get("city"),
                current_location.get("country"),
                current_location.get("postal_code"),
                contact.get("phone"),
                contact.get("email"),
                # FIXED: Schema uses emergency_contact and emergency_phone
                contact.get("emergency_contact"),  # emergency_contact
                contact.get("emergency_phone"),  # emergency_phone
                demographics.get("language"),
                demographics.get("interpreter_needed", False),
                insurance.get("provider"),
                # FIXED: Schema uses policy_number
                insurance.get("policy_number"),  # policy_number
                pcp.get("name"),
                pcp.get("contact"),
                demographics.get("note")
            ))
            self.logger.info(f"✓ SCHEMA-ALIGNED: Inserted demographics for patient {patient_id}")
            return 1
        except Exception as e:
            self.logger.error(f"Could not insert demographics: {e}")
            return 0

