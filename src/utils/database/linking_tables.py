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
        count += self.insert_variant_to_phenotype_links(cursor, profile)
        count += self.insert_drug_to_variant_links(cursor, profile)
        count += self.insert_variant_drug_evidence(cursor, profile)
        count += self.insert_disease_drug_variant_associations(cursor, profile)
        count += self.insert_patient_variant_population_context(cursor, profile)
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
                    
                    # SCHEMA-COMPLETE v2.1: Insert ALL 20 schema columns
                    # Get variant details for genotype, diplotype, phenotype, allele, clinical_significance
                    genotype = variant.get("genotype")
                    diplotype_info = variant.get("diplotype", {})
                    if isinstance(diplotype_info, dict):
                        diplotype = diplotype_info.get("diplotype")
                    else:
                        diplotype = diplotype_info if isinstance(diplotype_info, str) else None
                    phenotype = variant.get("phenotype") or variant.get("predicted_phenotype")
                    allele = drug_entry.get("allele")  # May be in drug_entry
                    clinical_significance = variant.get("clinical_significance")
                    
                    # Determine severity from recommendation
                    severity = None
                    recommendation_text = drug_entry.get("recommendation", "") or ""
                    if any(word in recommendation_text.lower() for word in ["contraindicated", "avoid", "do not use", "not recommended"]):
                        severity = "CRITICAL"
                    elif any(word in recommendation_text.lower() for word in ["risk", "toxicity", "adverse", "reduced efficacy"]):
                        severity = "WARNING"
                    elif recommendation_text:
                        severity = "INFO"
                    
                    # Determine match method
                    match_method = "exact"  # Default, could be enhanced based on matching logic
                    
                    insert_sql = """
                        INSERT INTO medication_to_variant_links (
                            patient_id, medication_id, variant_id, gene_symbol, rsid,
                            genotype, diplotype, phenotype, allele,
                            recommendation, evidence_level, clinical_significance,
                            clinical_annotation_types, pediatric,
                            severity, match_method,
                            pharmgkb_annotation_id, timestamp
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    
                    cursor.execute(insert_sql, (
                        patient_id,
                        medication_id,  # Can be NULL if drug not in patient's medications
                        variant_id,
                        gene_symbol,
                        rsid,
                        genotype,  # genotype
                        diplotype,  # diplotype
                        phenotype,  # phenotype
                        allele,  # allele
                        drug_entry.get("recommendation"),
                        drug_entry.get("evidence_level"),
                        clinical_significance,  # clinical_significance
                        clinical_annotation_types,  # JSONB array
                        drug_entry.get("pediatric", False),  # pediatric
                        severity,  # severity
                        match_method,  # match_method
                        pharmgkb_annotation_id,
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
        """✅ SCHEMA-COMPLETE v2.0: Insert population frequencies with ALL schema columns"""
        count = 0
        variants = profile.get("variants", [])
        
        for variant in variants:
            variant_id = variant.get("variant_id")
            gene_symbol = variant.get("gene")
            rsid = variant.get("rsid")
            
            population_frequencies = variant.get("population_frequencies", {})
            
            # Handle different data structures
            # Option 1: Simple dict {population: frequency}
            # Option 2: Detailed dict {population: {allele: freq_data}}
            # Option 3: List of frequency objects
            
            for pop_name, freq_data in population_frequencies.items():
                if freq_data is None:
                    continue
                
                # Check if freq_data is a simple value or detailed dict
                if isinstance(freq_data, dict):
                    # Detailed frequency data
                    sub_population = freq_data.get("sub_population") or freq_data.get("subPopulation")
                    allele = freq_data.get("allele")
                    allele_count = freq_data.get("allele_count") or freq_data.get("alleleCount")
                    allele_number = freq_data.get("allele_number") or freq_data.get("alleleNumber")
                    allele_frequency = freq_data.get("allele_frequency") or freq_data.get("alleleFrequency") or freq_data.get("frequency")
                    homozygote_count = freq_data.get("homozygote_count") or freq_data.get("homozygoteCount")
                    source = freq_data.get("source", "gnomAD")
                    database_version = freq_data.get("database_version") or freq_data.get("databaseVersion")
                else:
                    # Simple frequency value
                    sub_population = None
                    allele = None
                    allele_count = None
                    allele_number = None
                    allele_frequency = freq_data if isinstance(freq_data, (int, float)) else None
                    homozygote_count = None
                    source = "gnomAD"  # Default source
                    database_version = None
                
                try:
                    cursor.execute("""
                        INSERT INTO population_frequencies (
                            variant_id, gene_symbol, rsid, population, sub_population,
                            allele, allele_count, allele_number, allele_frequency,
                            homozygote_count, source, database_version
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (
                        variant_id,
                        gene_symbol,
                        rsid,
                        pop_name,  # population
                        sub_population,  # sub_population
                        allele,  # allele
                        allele_count,  # allele_count
                        allele_number,  # allele_number
                        allele_frequency,  # allele_frequency (not just "frequency")
                        homozygote_count,  # homozygote_count
                        source,  # source
                        database_version  # database_version
                    ))
                    count += 1
                except Exception as e:
                    self.logger.warning(f"Could not insert population frequency: {e}")
        
        self.logger.info(f"✓ SCHEMA-COMPLETE: Inserted {count} population frequencies (with all columns)")
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
    
    def insert_variant_to_phenotype_links(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """✅ SCHEMA-ALIGNED: Insert variant_to_phenotype_links"""
        count = 0
        variant_linking = profile.get("variant_linking", {})
        links = variant_linking.get("links", {})
        variant_to_phenotype_links = links.get("variant_to_phenotype", [])
        
        for link in variant_to_phenotype_links:
            try:
                cursor.execute("""
                    INSERT INTO variant_to_phenotype_links (
                        variant_id, gene_symbol, phenotype_text, source, link_type
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (
                    link.get("variant_id"),
                    link.get("gene_symbol") or link.get("gene"),
                    link.get("phenotype_text") or link.get("phenotype"),
                    link.get("source", "PharmGKB"),
                    link.get("link_type", "variant_phenotype")
                ))
                count += 1
            except Exception as e:
                self.logger.warning(f"Could not insert variant-to-phenotype link: {e}")
        
        # Also extract from variants directly if not in variant_linking
        if count == 0:
            variants = profile.get("variants", [])
            for variant in variants:
                phenotype = variant.get("phenotype") or variant.get("predicted_phenotype")
                if phenotype:
                    try:
                        cursor.execute("""
                            INSERT INTO variant_to_phenotype_links (
                                variant_id, gene_symbol, phenotype_text, source, link_type
                            )
                            VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT DO NOTHING
                        """, (
                            variant.get("variant_id"),
                            variant.get("gene"),
                            str(phenotype),
                            "Variant Data",
                            "direct_phenotype"
                        ))
                        count += 1
                    except Exception as e:
                        self.logger.debug(f"Could not insert variant phenotype from variant data: {e}")
        
        self.logger.info(f"✓ SCHEMA-ALIGNED: Inserted {count} variant-to-phenotype links")
        return count
    
    def insert_drug_to_variant_links(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """✅ SCHEMA-ALIGNED: Insert drug_to_variant_links"""
        count = 0
        variant_linking = profile.get("variant_linking", {})
        links = variant_linking.get("links", {})
        drug_to_variant_links = links.get("drug_to_variant", [])
        
        for link in drug_to_variant_links:
            try:
                cursor.execute("""
                    INSERT INTO drug_to_variant_links (
                        drug_name, snomed_code, variant_id, gene_symbol, rsid,
                        genotype, diplotype, phenotype, allele,
                        interaction_type, recommendation, evidence_level,
                        clinical_annotation_types, pediatric, link_type
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (
                    link.get("drug_name"),
                    link.get("snomed_code"),
                    link.get("variant_id"),
                    link.get("gene_symbol") or link.get("gene"),
                    link.get("rsid"),
                    link.get("genotype"),
                    link.get("diplotype"),
                    link.get("phenotype"),
                    link.get("allele"),
                    link.get("interaction_type", "pharmacogenomic"),
                    link.get("recommendation"),
                    link.get("evidence_level"),
                    json.dumps(link.get("clinical_annotation_types", [])) if link.get("clinical_annotation_types") else None,
                    link.get("pediatric", False),
                    link.get("link_type", "drug_variant")
                ))
                count += 1
            except Exception as e:
                self.logger.warning(f"Could not insert drug-to-variant link: {e}")
        
        # Also extract from variant drugs if not in variant_linking
        if count == 0:
            variants = profile.get("variants", [])
            for variant in variants:
                drugs = variant.get("drugs", [])
                for drug in drugs:
                    try:
                        cursor.execute("""
                            INSERT INTO drug_to_variant_links (
                                drug_name, variant_id, gene_symbol, rsid,
                                recommendation, evidence_level,
                                clinical_annotation_types, link_type
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT DO NOTHING
                        """, (
                            drug.get("name"),
                            variant.get("variant_id"),
                            variant.get("gene"),
                            variant.get("rsid"),
                            drug.get("recommendation"),
                            drug.get("evidence_level"),
                            json.dumps([drug.get("clinical_annotation_type")]) if drug.get("clinical_annotation_type") else None,
                            "variant_drug"
                        ))
                        count += 1
                    except Exception as e:
                        self.logger.debug(f"Could not insert drug-to-variant from variant data: {e}")
        
        self.logger.info(f"✓ SCHEMA-ALIGNED: Inserted {count} drug-to-variant links")
        return count
    
    def insert_variant_drug_evidence(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """✅ SCHEMA-ALIGNED: Insert variant_drug_evidence (evidence chain)"""
        count = 0
        variants = profile.get("variants", [])
        
        for variant in variants:
            variant_id = variant.get("variant_id")
            gene_symbol = variant.get("gene")
            drugs = variant.get("drugs", [])
            
            for drug in drugs:
                drug_name = drug.get("name")
                if not drug_name:
                    continue
                
                # Get PharmGKB annotation ID for this variant-drug pair
                pharmgkb_annotation_id = None
                pharmgkb_data = variant.get("pharmgkb", {})
                annotations = pharmgkb_data.get("annotations", [])
                
                for annotation in annotations:
                    # Check if this annotation is related to this drug
                    related_chemicals = annotation.get("relatedChemicals", [])
                    if isinstance(related_chemicals, list):
                        for chem in related_chemicals:
                            if isinstance(chem, dict) and chem.get("name", "").lower() == drug_name.lower():
                                pharmgkb_annotation_id = annotation.get("id")
                                break
                    if pharmgkb_annotation_id:
                        break
                
                # Extract publication PMID if available
                publication_pmid = None
                publications = variant.get("publications", [])
                if publications:
                    # Get first publication PMID
                    first_pub = publications[0] if isinstance(publications, list) else publications
                    publication_pmid = first_pub.get("pmid") if isinstance(first_pub, dict) else None
                
                # Get guideline and label IDs from PharmGKB annotation
                guideline_id = None
                label_id = None
                if pharmgkb_annotation_id:
                    # Look up guideline and label from pharmgkb_annotation_guidelines and pharmgkb_annotation_labels
                    # These were inserted by reference_data.py
                    try:
                        cursor.execute("""
                            SELECT guideline_id FROM pharmgkb_annotation_guidelines
                            WHERE annotation_id = %s LIMIT 1
                        """, (pharmgkb_annotation_id,))
                        result = cursor.fetchone()
                        if result:
                            guideline_id = result[0]
                    except:
                        pass
                    
                    try:
                        cursor.execute("""
                            SELECT label_id FROM pharmgkb_annotation_labels
                            WHERE annotation_id = %s LIMIT 1
                        """, (pharmgkb_annotation_id,))
                        result = cursor.fetchone()
                        if result:
                            label_id = result[0]
                    except:
                        pass
                
                evidence_level = drug.get("evidence_level")
                evidence_type = "PharmGKB Clinical Annotation" if pharmgkb_annotation_id else "Variant Drug Association"
                
                try:
                    cursor.execute("""
                        INSERT INTO variant_drug_evidence (
                            variant_id, drug_name, pharmgkb_annotation_id,
                            publication_pmid, guideline_id, label_id,
                            evidence_type, evidence_level
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (
                        variant_id,
                        drug_name,
                        pharmgkb_annotation_id,
                        publication_pmid,
                        guideline_id,
                        label_id,
                        evidence_type,
                        evidence_level
                    ))
                    count += 1
                except Exception as e:
                    self.logger.warning(f"Could not insert variant-drug evidence: {e}")
        
        self.logger.info(f"✓ SCHEMA-ALIGNED: Inserted {count} variant-drug evidence records")
        return count
    
    def insert_disease_drug_variant_associations(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """✅ SCHEMA-ALIGNED: Insert disease_drug_variant_associations (triangle associations)"""
        count = 0
        patient_id = profile.get("patient_id")
        medications = profile.get("clinical_information", {}).get("current_medications", [])
        variants = profile.get("variants", [])
        
        # Build variant-drug map
        variant_drug_map = {}
        for variant in variants:
            variant_id = variant.get("variant_id")
            drugs = variant.get("drugs", [])
            for drug in drugs:
                drug_name = drug.get("name")
                if drug_name:
                    key = f"{variant_id}:{drug_name.lower()}"
                    variant_drug_map[key] = {
                        "variant": variant,
                        "drug": drug
                    }
        
        # For each medication with a treats_condition, create associations
        for med in medications:
            treats_condition = med.get("treats_condition", {})
            disease_snomed = treats_condition.get("snomed:code") or treats_condition.get("snomed_code")
            drug_name = med.get("schema:name") or med.get("rdfs:label")
            
            if not disease_snomed or not drug_name:
                continue
            
            # Find variants that affect this drug
            for variant in variants:
                variant_id = variant.get("variant_id")
                drugs = variant.get("drugs", [])
                
                for variant_drug in drugs:
                    if variant_drug.get("name", "").lower() == drug_name.lower():
                        # Found a variant-drug-disease association
                        try:
                            cursor.execute("""
                                INSERT INTO disease_drug_variant_associations (
                                    disease_snomed, drug_name, variant_id, gene_symbol,
                                    association_type, evidence_level, recommendation, source
                                )
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT DO NOTHING
                            """, (
                                disease_snomed,
                                drug_name,
                                variant_id,
                                variant.get("gene"),
                                "medication_indication",
                                variant_drug.get("evidence_level"),
                                variant_drug.get("recommendation"),
                                "Patient Medication + Variant Data"
                            ))
                            count += 1
                        except Exception as e:
                            self.logger.warning(f"Could not insert disease-drug-variant association: {e}")
        
        self.logger.info(f"✓ SCHEMA-ALIGNED: Inserted {count} disease-drug-variant associations")
        return count
    
    def insert_patient_variant_population_context(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """✅ SCHEMA-ALIGNED: Insert patient_variant_population_context (ethnicity-aware)"""
        count = 0
        patient_id = profile.get("patient_id")
        demographics = profile.get("clinical_information", {}).get("demographics", {})
        ethnicity = demographics.get("ethnicity", [])
        variants = profile.get("variants", [])
        
        if not ethnicity or not variants:
            return 0
        
        # Get primary ethnicity
        primary_ethnicity = ethnicity[0] if isinstance(ethnicity, list) else str(ethnicity)
        
        for variant in variants:
            variant_id = variant.get("variant_id")
            
            # Get population frequencies for this variant
            population_frequencies = variant.get("population_frequencies", {})
            
            # Find frequency for patient's ethnicity
            frequency_in_patient_population = None
            if isinstance(population_frequencies, dict):
                # Try to match ethnicity
                for pop_name, freq in population_frequencies.items():
                    if isinstance(pop_name, str) and primary_ethnicity.lower() in pop_name.lower():
                        frequency_in_patient_population = freq if isinstance(freq, (int, float)) else None
                        break
            
            # Get ethnicity-specific drugs from variant data
            ethnicity_specific_drugs = []
            ethnicity_specific_recommendations = []
            
            # Check ethnicity_medication_adjustments for this variant
            ethnicity_adjustments = profile.get("ethnicity_medication_adjustments", [])
            for adj in ethnicity_adjustments:
                if adj.get("variant_id") == variant_id:
                    drug_name = adj.get("drug_name")
                    if drug_name and drug_name not in ethnicity_specific_drugs:
                        ethnicity_specific_drugs.append(drug_name)
                    recommendation = adj.get("recommendation")
                    if recommendation and recommendation not in ethnicity_specific_recommendations:
                        ethnicity_specific_recommendations.append(recommendation)
            
            # Build population significance text
            population_significance = None
            if frequency_in_patient_population:
                if frequency_in_patient_population > 0.1:
                    population_significance = f"Common variant in {primary_ethnicity} population ({frequency_in_patient_population:.2%})"
                elif frequency_in_patient_population > 0.01:
                    population_significance = f"Moderate frequency in {primary_ethnicity} population ({frequency_in_patient_population:.2%})"
                else:
                    population_significance = f"Rare variant in {primary_ethnicity} population ({frequency_in_patient_population:.2%})"
            
            try:
                cursor.execute("""
                    INSERT INTO patient_variant_population_context (
                        patient_id, variant_id, patient_ethnicity,
                        frequency_in_patient_population, population_significance,
                        ethnicity_specific_drugs, ethnicity_specific_recommendations
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (
                    patient_id,
                    variant_id,
                    primary_ethnicity,
                    frequency_in_patient_population,
                    population_significance,
                    json.dumps(ethnicity_specific_drugs) if ethnicity_specific_drugs else None,
                    json.dumps(ethnicity_specific_recommendations) if ethnicity_specific_recommendations else None
                ))
                count += 1
            except Exception as e:
                self.logger.warning(f"Could not insert patient variant population context: {e}")
        
        self.logger.info(f"✓ SCHEMA-ALIGNED: Inserted {count} patient variant population contexts")
        return count

