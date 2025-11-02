"""
Linking Tables Loader - SCHEMA ALIGNED v2.1
Handles: medication_to_variant_links, pgx_conflicts, conflict_variants, 
         ethnicity_medication_adjustments, population_frequencies
FIXED: medication_to_variant_links - use medication_id (not drug_name), timestamp (not link_timestamp)
FIXED: ethnicity_medication_adjustments - remove "source" column (doesn't exist in schema)
"""

# VERSION: v2.1.20251102 - Force module reload
_MODULE_VERSION = "2.1.20251102"

import json
import logging
from datetime import datetime
from typing import Dict
import psycopg
from .utils import parse_date

# Log module version on import
_logger_init = logging.getLogger(__name__)
_logger_init.info(f"📦 Loading LinkingTablesLoader module v{_MODULE_VERSION}")


class LinkingTablesLoader:
    """Loads linking tables with schema-aligned structure"""
    
    def __init__(self, inserted_drugs: Dict, inserted_pharmgkb_annotations: Dict):
        self.logger = logging.getLogger(__name__)
        self.inserted_drugs = inserted_drugs
        self.inserted_pharmgkb_annotations = inserted_pharmgkb_annotations
    
    def load_all(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """Load all linking tables"""
        count = 0
        count += self.insert_medication_to_variant_links(cursor, profile)
        count += self.insert_pgx_conflicts(cursor, profile)
        count += self.insert_population_frequencies(cursor, profile)
        count += self.insert_ethnicity_medication_adjustments(cursor, profile)
        return count
    
    def insert_medication_to_variant_links(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """
        ✅ SCHEMA-ALIGNED v2.0: Insert medication_to_variant_links
        CRITICAL FIX: Schema uses medication_id (not drug_name), timestamp (not link_timestamp),
                      clinical_annotation_types JSONB (not clinical_annotation_type)
        """
        count = 0
        patient_id = profile.get("patient_id")
        variants = profile.get("variants", [])
        
        # Build medication name to ID mapping from patient's current medications
        # This allows us to link variants to medications the patient actually takes
        patient_medications = profile.get("clinical_information", {}).get("current_medications", [])
        med_name_to_id = {}
        for med in patient_medications:
            if "_medication_id" in med:
                med_name = med.get("schema:name") or med.get("rdfs:label") or med.get("drug_name")
                if med_name:
                    med_name_to_id[med_name.lower()] = med["_medication_id"]
        
        for variant in variants:
            gene_symbol = variant.get("gene")
            variant_id = variant.get("variant_id")
            rsid = variant.get("rsid")
            
            # Get drugs affected by this variant
            drugs = variant.get("drugs", [])
            
            for drug_entry in drugs:
                drug_name = drug_entry.get("name")
                if not drug_name:
                    continue
                
                # Look up medication_id if this drug is in patient's medications
                medication_id = med_name_to_id.get(drug_name.lower())
                
                # Get the corresponding PharmGKB annotation ID
                pharmgkb_annotation_id = None
                pharmgkb_data = variant.get("pharmgkb", {})
                annotations = pharmgkb_data.get("annotations", [])
                for annotation in annotations:
                    # Match annotation to this drug
                    related_chemicals = annotation.get("relatedChemicals", [])
                    if isinstance(related_chemicals, list):
                        for chem in related_chemicals:
                            if isinstance(chem, dict) and chem.get("name", "").lower() == drug_name.lower():
                                pharmgkb_annotation_id = annotation.get("id")
                                break
                    if pharmgkb_annotation_id:
                        break
                
                # Convert clinical_annotation_type to JSONB array format
                clinical_annotation_type = drug_entry.get("clinical_annotation_type")
                if clinical_annotation_type:
                    clinical_annotation_types = json.dumps([clinical_annotation_type]) if isinstance(clinical_annotation_type, str) else json.dumps(clinical_annotation_type) if isinstance(clinical_annotation_type, list) else None
                else:
                    clinical_annotation_types = None
                
                # Use savepoint to prevent transaction abort
                savepoint_name = f"med_variant_link_{count}"
                try:
                    cursor.execute(f"SAVEPOINT {savepoint_name}")
                    
                    # SCHEMA-FIXED: Use medication_id (not drug_name), timestamp (not link_timestamp),
                    #              clinical_annotation_types JSONB (not clinical_annotation_type)
                    insert_sql = """
                        INSERT INTO medication_to_variant_links (
                            patient_id, medication_id, gene_symbol, variant_id, rsid,
                            recommendation, evidence_level,
                            pharmgkb_annotation_id,
                            clinical_annotation_types, timestamp
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    
                    cursor.execute(insert_sql, (
                        patient_id,
                        medication_id,  # Can be NULL if drug not in patient's medications
                        gene_symbol,
                        variant_id,
                        rsid,
                        drug_entry.get("recommendation"),
                        drug_entry.get("evidence_level"),
                        pharmgkb_annotation_id,
                        clinical_annotation_types,  # JSONB array
                        datetime.now()  # timestamp column
                    ))
                    count += 1
                    cursor.execute(f"RELEASE SAVEPOINT {savepoint_name}")
                except Exception as e:
                    error_msg = str(e)
                    self.logger.warning(f"Could not insert medication-variant link for {drug_name}: {error_msg}")
                    try:
                        cursor.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
                    except Exception as rollback_error:
                        if "transaction is aborted" in str(rollback_error).lower():
                            self.logger.error(f"Transaction aborted - cannot use savepoint. Original error: {error_msg}")
                            # Re-raise to trigger transaction restart in main_loader
                            raise RuntimeError(f"Transaction aborted in medication_to_variant_links: {error_msg}") from e
        
        self.logger.info(f"✓ SCHEMA-ALIGNED: Inserted {count} medication-variant links")
        return count
    
    def insert_pgx_conflicts(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """
        ✅ SCHEMA-ALIGNED: Insert pgx_conflicts + conflict_variants
        MAJOR FIX: Complete restructure into 2 tables
        pgx_conflicts: conflict_id, patient_id, drug_name, medication_id, severity, 
                       affecting_variants_count, match_method, recommendation, timestamp
        conflict_variants: link_id, conflict_id, gene_symbol, variant_id, rsid,
                           recommendation, evidence_level, clinical_significance
        """
        count = 0
        patient_id = profile.get("patient_id")
        conflicts = profile.get("conflicts", [])
        
        # Get medication IDs from profile (stored during medication insert)
        medications = profile.get("clinical_information", {}).get("current_medications", [])
        med_name_to_id = {}
        for med in medications:
            if "_medication_id" in med:
                med_name = med.get("schema:name") or med.get("rdfs:label")
                med_name_to_id[med_name] = med["_medication_id"]
        
        for conflict in conflicts:
            try:
                drug_name = conflict.get("drug_name")
                medication_id = med_name_to_id.get(drug_name)
                
                affecting_variants = conflict.get("affecting_variants", [])
                affecting_variants_count = len(affecting_variants)
                
                # SCHEMA-ALIGNED: Insert to pgx_conflicts table
                cursor.execute("""
                    INSERT INTO pgx_conflicts (
                        patient_id, drug_name, medication_id, severity,
                        affecting_variants_count, match_method, recommendation, timestamp
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING conflict_id
                """, (
                    patient_id,
                    drug_name,
                    medication_id,
                    conflict.get("severity"),
                    affecting_variants_count,
                    conflict.get("match_method", "exact"),
                    conflict.get("recommendation"),
                    datetime.now()
                ))
                conflict_id = cursor.fetchone()[0]
                count += 1
                
                # FIXED: Insert affecting_variants into conflict_variants table
                for affecting_var in affecting_variants:
                    self._insert_conflict_variant(cursor, conflict_id, affecting_var)
                
            except Exception as e:
                self.logger.warning(f"Could not insert pgx conflict for {drug_name}: {e}")
        
        self.logger.info(f"✓ SCHEMA-ALIGNED: Inserted {count} pgx conflicts (with conflict_variants table)")
        return count
    
    def _insert_conflict_variant(self, cursor: psycopg.Cursor, conflict_id: int, affecting_var: Dict):
        """✅ Insert into conflict_variants table (NEW TABLE)"""
        try:
            cursor.execute("""
                INSERT INTO conflict_variants (
                    conflict_id, gene_symbol, variant_id, rsid,
                    recommendation, evidence_level, clinical_significance
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                conflict_id,
                affecting_var.get("gene_symbol"),
                affecting_var.get("variant_id"),
                affecting_var.get("rsid"),
                affecting_var.get("recommendation"),
                affecting_var.get("evidence_level"),
                affecting_var.get("clinical_significance")
            ))
        except Exception as e:
            self.logger.warning(f"Could not insert conflict variant: {e}")
    
    def insert_population_frequencies(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """✅ SCHEMA-ALIGNED: Insert population frequencies"""
        count = 0
        variants = profile.get("variants", [])
        
        for variant in variants:
            variant_id = variant.get("variant_id")
            gene_symbol = variant.get("gene")
            rsid = variant.get("rsid")
            
            population_frequencies = variant.get("population_frequencies", {})
            for pop_name, freq in population_frequencies.items():
                if freq is not None:
                    try:
                        cursor.execute("""
                            INSERT INTO population_frequencies (
                                variant_id, gene_symbol, rsid, population, frequency
                            )
                            VALUES (%s, %s, %s, %s, %s)
                        """, (variant_id, gene_symbol, rsid, pop_name, freq))
                        count += 1
                    except Exception as e:
                        self.logger.warning(f"Could not insert population frequency: {e}")
        
        self.logger.info(f"✓ SCHEMA-ALIGNED: Inserted {count} population frequencies")
        return count
    
    def insert_ethnicity_medication_adjustments(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """
        ✅ SCHEMA-ALIGNED v2.1: Insert ethnicity_medication_adjustments
        CRITICAL FIX: Schema has NO "source" column
        Schema columns: variant_id, gene_symbol, ethnicity, drug_name, adjustment_type, 
                       adjustment_factor, recommendation, evidence_level, frequency_in_population
        """
        count = 0
        patient_id = profile.get("patient_id")
        
        # Get patient ethnicity
        demographics = profile.get("clinical_information", {}).get("demographics", {})
        ethnicity = demographics.get("ethnicity", [])
        if not ethnicity:
            return 0
        
        # Extract primary ethnicity
        primary_ethnicity = ethnicity[0] if isinstance(ethnicity, list) else str(ethnicity)
        
        # Get adjustments from profile
        ethnicity_adjustments = profile.get("ethnicity_medication_adjustments", [])
        
        for adjustment in ethnicity_adjustments:
            savepoint_name = f"ethnicity_adj_{count}"
            try:
                cursor.execute(f"SAVEPOINT {savepoint_name}")
                
                # SCHEMA-FIXED: Remove "source" column (doesn't exist)
                # Schema: variant_id, gene_symbol, ethnicity, drug_name, adjustment_type, 
                #         adjustment_factor, recommendation, evidence_level, frequency_in_population
                cursor.execute("""
                    INSERT INTO ethnicity_medication_adjustments (
                        variant_id, gene_symbol, ethnicity, drug_name,
                        adjustment_type, adjustment_factor, 
                        recommendation, evidence_level, frequency_in_population
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    adjustment.get("variant_id"),
                    adjustment.get("gene_symbol"),
                    adjustment.get("ethnicity") or primary_ethnicity,
                    adjustment.get("drug_name"),
                    adjustment.get("adjustment_type"),  # adjustment_type column
                    adjustment.get("adjustment_factor"),
                    adjustment.get("recommendation"),
                    adjustment.get("evidence_level"),
                    adjustment.get("frequency_in_population")  # Optional frequency
                ))
                count += 1
                cursor.execute(f"RELEASE SAVEPOINT {savepoint_name}")
            except Exception as e:
                error_msg = str(e)
                self.logger.warning(f"Could not insert ethnicity adjustment: {error_msg}")
                try:
                    cursor.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
                except Exception as rollback_error:
                    if "transaction is aborted" in str(rollback_error).lower():
                        self.logger.error(f"Transaction aborted - cannot use savepoint. Original error: {error_msg}")
                        raise RuntimeError(f"Transaction aborted in ethnicity_medication_adjustments: {error_msg}") from e
        
        self.logger.info(f"✓ SCHEMA-ALIGNED: Inserted {count} ethnicity medication adjustments")
        return count

