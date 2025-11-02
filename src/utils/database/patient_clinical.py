"""
Patient Clinical Data Loader - SCHEMA ALIGNED v2.1
Handles: current_conditions, current_medications, organ_function_labs, lifestyle_factors
FIXED: Removed snomed_url from lifestyle_factors INSERT (does not exist in schema)
"""

import json
import logging
from typing import Dict
import psycopg
from .utils import parse_date


class PatientClinicalLoader:
    """Loads patient clinical data with schema-aligned column names"""
    
    def __init__(self, inserted_drugs: Dict):
        self.logger = logging.getLogger(__name__)
        self.inserted_drugs = inserted_drugs  # Reference to drugs cache
    
    def load_all(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """Load all patient clinical data"""
        count = 0
        count += self.insert_conditions(cursor, profile)
        count += self.insert_medications(cursor, profile)
        count += self.insert_organ_function_labs(cursor, profile)
        count += self.insert_lifestyle_factors(cursor, profile)
        return count
    
    def insert_conditions(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """
        ✅ SCHEMA-ALIGNED: Insert current_conditions
        Fixed: snomed_url (not snomed_uri), rdfs_label (not condition_name), 
               skos_pref_label (not preferred_label), added condition_type
        """
        count = 0
        patient_id = profile.get("patient_id")
        conditions = profile.get("clinical_information", {}).get("current_conditions", [])
        
        for cond in conditions:
            try:
                # SCHEMA-ALIGNED column names
                cursor.execute("""
                    INSERT INTO current_conditions (
                        patient_id, snomed_code, 
                        snomed_url, rdfs_label, skos_pref_label, 
                        search_term, condition_type
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    patient_id,
                    cond.get("snomed:code") or cond.get("snomed_code"),
                    # FIXED: Schema uses snomed_url (not snomed_uri)
                    cond.get("@id"),  # snomed_url
                    # FIXED: Schema uses rdfs_label (not condition_name)
                    cond.get("rdfs:label"),  # rdfs_label
                    # FIXED: Schema uses skos_pref_label (not preferred_label)
                    cond.get("skos:prefLabel"),  # skos_pref_label
                    cond.get("search_term"),
                    # FIXED: Schema requires condition_type
                    cond.get("@type", "").replace("sdisco:", "")  # condition_type
                ))
                count += 1
            except Exception as e:
                self.logger.warning(f"Could not insert condition: {e}")
        
        self.logger.info(f"✓ SCHEMA-ALIGNED: Inserted {count} conditions")
        return count
    
    def insert_medications(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """
        ✅ SCHEMA-ALIGNED: Insert current_medications
        Fixed: medication_url, medication_type, drug_name (not medication_name), 
               schema_name, rxnorm_uri, treats_condition_snomed, treats_condition_label
        """
        count = 0
        patient_id = profile.get("patient_id")
        medications = profile.get("clinical_information", {}).get("current_medications", [])
        
        for med in medications:
            try:
                drug_name = med.get("schema:name") or med.get("rdfs:label")
                treats_condition = med.get("treats_condition", {})
                rxnorm = med.get("rxnorm", {})
                
                # SCHEMA-ALIGNED column names
                cursor.execute("""
                    INSERT INTO current_medications (
                        patient_id, 
                        medication_url, medication_type,
                        drugbank_id, chembl_id, rxnorm_cui, rxnorm_uri,
                        drug_name, schema_name,
                        dosage_form, dose_value, dose_unit, frequency, start_date,
                        purpose, source,
                        treats_condition_snomed, treats_condition_label,
                        indication_name, indication_mesh_id, indication_mesh_heading,
                        efo_id, max_phase_for_ind, max_phase_overall, first_approval,
                        relevance_score, treatment_line, clinical_phase, guideline,
                        combination_therapy, chembl_molecule_type
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING medication_id
                """, (
                    patient_id,
                    # FIXED: Schema has medication_url
                    med.get("@id"),  # medication_url
                    # FIXED: Schema has medication_type
                    med.get("@type", "").replace("sdisco:", ""),  # medication_type
                    med.get("drugbank:id"),
                    med.get("chembl_id"),
                    rxnorm.get("rxnorm_cui"),
                    # FIXED: Schema has rxnorm_uri
                    rxnorm.get("uri"),  # rxnorm_uri
                    # FIXED: Schema uses drug_name (not medication_name)
                    drug_name,  # drug_name
                    # FIXED: Schema has schema_name
                    med.get("schema:name"),  # schema_name
                    med.get("schema:dosageForm"),
                    med.get("schema:doseValue"),
                    med.get("schema:doseUnit"),
                    med.get("schema:frequency"),
                    parse_date(med.get("start_date")),
                    med.get("purpose"),
                    med.get("source"),
                    # FIXED: Schema uses treats_condition_snomed (not treats_snomed_code)
                    treats_condition.get("snomed:code") or treats_condition.get("snomed_code"),  # treats_condition_snomed
                    # FIXED: Schema uses treats_condition_label (not treats_condition_name)
                    treats_condition.get("rdfs:label"),  # treats_condition_label
                    med.get("indication_name"),
                    med.get("indication_mesh_id"),
                    med.get("indication_mesh_heading"),
                    med.get("efo_id"),
                    med.get("max_phase_for_ind"),
                    med.get("max_phase_overall"),
                    med.get("first_approval"),
                    med.get("relevance_score"),
                    med.get("treatment_line"),
                    med.get("clinical_phase"),
                    med.get("guideline"),
                    med.get("combination_therapy"),
                    med.get("chembl_molecule_type")
                ))
                med_id = cursor.fetchone()[0]
                # Store for later use in linking tables
                med["_medication_id"] = med_id
                count += 1
            except Exception as e:
                self.logger.warning(f"Could not insert medication {drug_name}: {e}")
        
        self.logger.info(f"✓ SCHEMA-ALIGNED: Inserted {count} medications")
        return count
    
    def insert_organ_function_labs(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """
        ✅ SCHEMA-ALIGNED: Insert organ_function_labs
        MAJOR FIX: organ_system (not test_type), test_type (not test_name), 
                   snomed_url (not snomed_uri), rdfs_label (not snomed_label),
                   Added: egfr_value, serum_creatinine, alt_value, ast_value, bilirubin_total
        """
        count = 0
        patient_id = profile.get("patient_id")
        organ_function = profile.get("clinical_information", {}).get("organ_function", {})
        
        # Process kidney function
        kidney = organ_function.get("kidney_function", {})
        if kidney:
            for test_name, test_data in kidney.items():
                if isinstance(test_data, dict):
                    try:
                        # Extract specific values for schema columns
                        value = test_data.get("value")
                        egfr_value = value if test_name == "creatinine_clearance" else None
                        serum_creatinine = value if test_name == "serum_creatinine" else None
                        
                        # SCHEMA-ALIGNED column names
                        cursor.execute("""
                            INSERT INTO organ_function_labs (
                                patient_id, 
                                organ_system, test_type,
                                snomed_code, snomed_url, rdfs_label,
                                value, unit, test_date, normal_range, status,
                                egfr_value, serum_creatinine,
                                alt_value, ast_value, bilirubin_total
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            patient_id,
                            # FIXED: Schema uses organ_system (was test_type="kidney")
                            "kidney",  # organ_system
                            # FIXED: Schema uses test_type (was test_name like "creatinine_clearance")
                            test_data.get("rdfs:label") or test_name.replace("_", " ").title(),  # test_type
                            test_data.get("snomed:code") or test_data.get("snomed_code"),
                            # FIXED: Schema uses snomed_url (not snomed_uri)
                            test_data.get("@id"),  # snomed_url
                            # FIXED: Schema uses rdfs_label (not snomed_label)
                            test_data.get("rdfs:label"),  # rdfs_label
                            value,
                            test_data.get("unit"),
                            parse_date(test_data.get("date")),
                            test_data.get("normal_range"),
                            test_data.get("status"),
                            # FIXED: Schema has specific value columns
                            egfr_value,  # egfr_value
                            serum_creatinine,  # serum_creatinine
                            None,  # alt_value (liver)
                            None,  # ast_value (liver)
                            None   # bilirubin_total (liver)
                        ))
                        count += 1
                    except Exception as e:
                        self.logger.warning(f"Could not insert kidney test {test_name}: {e}")
        
        # Process liver function
        liver = organ_function.get("liver_function", {})
        if liver:
            for test_name, test_data in liver.items():
                if isinstance(test_data, dict):
                    try:
                        # Extract specific values for schema columns
                        value = test_data.get("value")
                        alt_value = value if test_name == "alt" else None
                        ast_value = value if test_name == "ast" else None
                        bilirubin_total = value if test_name == "bilirubin_total" else None
                        
                        # SCHEMA-ALIGNED column names
                        cursor.execute("""
                            INSERT INTO organ_function_labs (
                                patient_id,
                                organ_system, test_type,
                                snomed_code, snomed_url, rdfs_label,
                                value, unit, test_date, normal_range, status,
                                egfr_value, serum_creatinine,
                                alt_value, ast_value, bilirubin_total
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            patient_id,
                            # FIXED: Schema uses organ_system
                            "liver",  # organ_system
                            # FIXED: Schema uses test_type
                            test_data.get("rdfs:label") or test_name.replace("_", " ").upper(),  # test_type
                            test_data.get("snomed:code") or test_data.get("snomed_code"),
                            test_data.get("@id"),  # snomed_url
                            test_data.get("rdfs:label"),  # rdfs_label
                            value,
                            test_data.get("unit"),
                            parse_date(test_data.get("date")),
                            test_data.get("normal_range"),
                            test_data.get("status"),
                            None,  # egfr_value (kidney)
                            None,  # serum_creatinine (kidney)
                            # FIXED: Schema has specific liver value columns
                            alt_value,  # alt_value
                            ast_value,  # ast_value
                            bilirubin_total   # bilirubin_total
                        ))
                        count += 1
                    except Exception as e:
                        self.logger.warning(f"Could not insert liver test {test_name}: {e}")
        
        self.logger.info(f"✓ SCHEMA-ALIGNED: Inserted {count} organ function tests")
        return count
    
    def insert_lifestyle_factors(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """
        ✅ SCHEMA-ALIGNED v2.1: Insert lifestyle factors
        CRITICAL FIX: lifestyle_factors table does NOT have snomed_url column
        Only inserts: patient_id, factor_type, snomed_code, rdfs_label, status, frequency, note
        """
        count = 0
        patient_id = profile.get("patient_id")
        lifestyle_factors = profile.get("clinical_information", {}).get("lifestyle_factors", [])
        
        # Check transaction state before starting
        try:
            test_cursor = cursor.connection.cursor()
            test_cursor.execute("SELECT 1")
            test_cursor.close()
        except Exception as tx_check:
            if "transaction is aborted" in str(tx_check).lower():
                self.logger.error("❌ Transaction already aborted before lifestyle_factors insert")
                raise  # Re-raise to let main_loader handle transaction restart
        
        for idx, factor in enumerate(lifestyle_factors):
            savepoint_name = f"lifestyle_sp_{idx}"
            try:
                # CRITICAL: Create savepoint BEFORE any operation to protect transaction
                cursor.execute(f"SAVEPOINT {savepoint_name}")
                
                # CRITICAL FIX v2.1: lifestyle_factors table does NOT have snomed_url column
                # Schema columns are: patient_id, factor_type, snomed_code, rdfs_label, status, frequency, note
                # DO NOT INCLUDE snomed_url - it does not exist in the database schema
                cursor.execute("""
                    INSERT INTO lifestyle_factors (
                        patient_id, factor_type, snomed_code, rdfs_label,
                        status, frequency, note
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    patient_id,
                    factor.get("factor_type"),
                    factor.get("snomed:code") or factor.get("snomed_code"),
                    factor.get("rdfs:label") or factor.get("skos:prefLabel"),  # rdfs_label
                    factor.get("status"),
                    factor.get("frequency"),
                    factor.get("note")
                ))
                count += 1
                # Release savepoint only on success
                cursor.execute(f"RELEASE SAVEPOINT {savepoint_name}")
            except Exception as e:
                error_msg = str(e)
                self.logger.warning(f"⚠️ Could not insert lifestyle factor {idx}: {error_msg}")
                
                # CRITICAL: Immediately rollback to savepoint to prevent transaction abort
                try:
                    # Always try to rollback to savepoint first (works if transaction not aborted)
                    cursor.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
                    self.logger.debug(f"✓ Rolled back to savepoint {savepoint_name}")
                except Exception as rollback_error:
                    rollback_msg = str(rollback_error)
                    # If rollback fails, transaction is aborted
                    if "transaction is aborted" in rollback_msg.lower() or "current transaction is aborted" in rollback_msg.lower():
                        self.logger.error(f"❌ Transaction aborted - cannot use savepoint. Error: {error_msg}")
                        # Re-raise to let main_loader.py handle full transaction restart
                        raise RuntimeError(f"Transaction aborted in lifestyle_factors insert: {error_msg}") from e
                    else:
                        self.logger.error(f"❌ Savepoint rollback failed: {rollback_error}")
                        # Re-raise original error
                        raise
        
        self.logger.info(f"✓ SCHEMA-ALIGNED: Inserted {count} lifestyle factors")
        return count

