"""
Linking Tables Loader - SCHEMA ALIGNED
Handles: medication_to_variant_links, pgx_conflicts, conflict_variants, 
         ethnicity_medication_adjustments, population_frequencies
"""

import json
import logging
from datetime import datetime
from typing import Dict
import psycopg
from .utils import parse_date


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
        ✅ SCHEMA-ALIGNED: Insert medication_to_variant_links
        CRITICAL FIX: Added pharmgkb_annotation_id (was missing!)
        """
        count = 0
        patient_id = profile.get("patient_id")
        variants = profile.get("variants", [])
        
        for variant in variants:
            gene_symbol = variant.get("gene")
            variant_id = variant.get("variant_id")
            rsid = variant.get("rsid")
            
            # Get drugs affected by this variant
            drugs = variant.get("drugs", [])
            
            for drug_entry in drugs:
                drug_name = drug_entry.get("name")
                
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
                
                try:
                    # SCHEMA-ALIGNED INSERT with pharmgkb_annotation_id
                    cursor.execute("""
                        INSERT INTO medication_to_variant_links (
                            patient_id, gene_symbol, variant_id, rsid, drug_name,
                            recommendation, evidence_level,
                            pharmgkb_annotation_id,
                            clinical_annotation_type, link_timestamp
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        patient_id,
                        gene_symbol,
                        variant_id,
                        rsid,
                        drug_name,
                        drug_entry.get("recommendation"),
                        drug_entry.get("evidence_level"),
                        # FIXED: Critical foreign key added!
                        pharmgkb_annotation_id,  # pharmgkb_annotation_id
                        drug_entry.get("clinical_annotation_type"),
                        datetime.now()
                    ))
                    count += 1
                except Exception as e:
                    self.logger.warning(f"Could not insert medication-variant link for {drug_name}: {e}")
        
        self.logger.info(f"✓ SCHEMA-ALIGNED: Inserted {count} medication-variant links (with pharmgkb_annotation_id)")
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
        ✅ SCHEMA-ALIGNED: Insert ethnicity_medication_adjustments
        MAJOR FIX: Changed from patient-based to variant-based
        Schema: ethnicity, variant_id, gene_symbol, drug_name, adjustment_factor, 
                recommendation, evidence_level, source
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
            try:
                # SCHEMA-ALIGNED: variant-based, not patient-based
                cursor.execute("""
                    INSERT INTO ethnicity_medication_adjustments (
                        ethnicity, variant_id, gene_symbol, drug_name,
                        adjustment_factor, recommendation, evidence_level, source
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    adjustment.get("ethnicity") or primary_ethnicity,
                    adjustment.get("variant_id"),  # FIXED: variant_id instead of patient_id
                    adjustment.get("gene_symbol"),  # FIXED: Added gene_symbol
                    adjustment.get("drug_name"),
                    adjustment.get("adjustment_factor"),  # FIXED: adjustment_factor instead of adjustment_type
                    adjustment.get("recommendation"),
                    adjustment.get("evidence_level"),
                    adjustment.get("source", "PharmGKB")
                ))
                count += 1
            except Exception as e:
                self.logger.warning(f"Could not insert ethnicity adjustment: {e}")
        
        self.logger.info(f"✓ SCHEMA-ALIGNED: Inserted {count} ethnicity medication adjustments")
        return count

