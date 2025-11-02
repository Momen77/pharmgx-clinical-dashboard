"""
Summaries Loader - SCHEMA ALIGNED v2.0
Handles: clinical_summaries, literature_summaries, processing_summary
FIXED: processing_summary - use correct column names from schema
"""

# VERSION: v2.0.20251102 - Force module reload
_MODULE_VERSION = "2.0.20251102"

import json
import logging
from datetime import datetime
from typing import Dict
import psycopg

# Log module version on import
_logger_init = logging.getLogger(__name__)
_logger_init.info(f"📦 Loading SummariesLoader module v{_MODULE_VERSION}")


class SummariesLoader:
    """Loads summary tables with schema-aligned structure"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def load_all(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """Load all summary data"""
        count = 0
        count += self.insert_clinical_summary(cursor, profile)
        count += self.insert_literature_summary(cursor, profile)
        count += self.insert_processing_summary(cursor, profile)
        return count
    
    def insert_clinical_summary(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """
        ✅ SCHEMA-ALIGNED: Insert clinical_summaries
        Fixed: drug_response_count (not drug_response_variants)
        Added: pathogenic_count, likely_pathogenic_count, uncertain_significance_count, benign_count
        """
        try:
            patient_id = profile.get("patient_id")
            
            # Count variants by clinical significance
            variants = profile.get("variants", [])
            pathogenic_count = 0
            likely_pathogenic_count = 0
            uncertain_significance_count = 0
            benign_count = 0
            drug_response_count = 0
            
            high_impact_genes = []
            
            for variant in variants:
                clinical_sig = (variant.get("clinical_significance") or "").lower()
                
                if "pathogenic" in clinical_sig and "likely" not in clinical_sig:
                    pathogenic_count += 1
                elif "likely pathogenic" in clinical_sig:
                    likely_pathogenic_count += 1
                elif "uncertain" in clinical_sig or "vus" in clinical_sig:
                    uncertain_significance_count += 1
                elif "benign" in clinical_sig and "likely" not in clinical_sig:
                    benign_count += 1
                
                # Count drug response variants
                if variant.get("drugs") or variant.get("pharmgkb"):
                    drug_response_count += 1
                    gene = variant.get("gene")
                    if gene and gene not in high_impact_genes:
                        high_impact_genes.append(gene)
            
            # SCHEMA-ALIGNED INSERT
            cursor.execute("""
                INSERT INTO clinical_summaries (
                    patient_id, total_variants,
                    pathogenic_count, likely_pathogenic_count,
                    uncertain_significance_count, benign_count,
                    drug_response_count,
                    high_impact_genes, analysis_timestamp
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (patient_id) DO UPDATE SET
                    total_variants = EXCLUDED.total_variants,
                    pathogenic_count = EXCLUDED.pathogenic_count,
                    likely_pathogenic_count = EXCLUDED.likely_pathogenic_count,
                    uncertain_significance_count = EXCLUDED.uncertain_significance_count,
                    benign_count = EXCLUDED.benign_count,
                    drug_response_count = EXCLUDED.drug_response_count,
                    high_impact_genes = EXCLUDED.high_impact_genes,
                    analysis_timestamp = EXCLUDED.analysis_timestamp
            """, (
                patient_id,
                len(variants),
                pathogenic_count,  # FIXED: Added
                likely_pathogenic_count,  # FIXED: Added
                uncertain_significance_count,  # FIXED: Added
                benign_count,  # FIXED: Added
                drug_response_count,  # FIXED: Changed from drug_response_variants
                json.dumps(high_impact_genes),
                datetime.now()
            ))
            self.logger.info(f"✓ SCHEMA-ALIGNED: Inserted clinical summary for patient {patient_id}")
            return 1
        except Exception as e:
            self.logger.error(f"Could not insert clinical summary: {e}")
            return 0
    
    def insert_literature_summary(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """✅ SCHEMA-ALIGNED: Insert literature_summaries"""
        try:
            patient_id = profile.get("patient_id")
            literature_summary = profile.get("literature_summary", {})
            
            if not literature_summary:
                return 0
            
            # Count publications
            total_publications = 0
            gene_lit = literature_summary.get("gene_literature", {})
            for gene_pubs in gene_lit.values():
                total_publications += len(gene_pubs) if gene_pubs else 0
            
            variant_lit = literature_summary.get("variant_literature", {})
            for var_pubs in variant_lit.values():
                total_publications += len(var_pubs) if var_pubs else 0
            
            drug_lit = literature_summary.get("drug_literature", {})
            for drug_pubs in drug_lit.values():
                total_publications += len(drug_pubs) if drug_pubs else 0
            
            cursor.execute("""
                INSERT INTO literature_summaries (
                    patient_id, total_publications, gene_literature_count,
                    variant_literature_count, drug_literature_count,
                    search_timestamp
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (patient_id) DO UPDATE SET
                    total_publications = EXCLUDED.total_publications,
                    search_timestamp = EXCLUDED.search_timestamp
            """, (
                patient_id,
                total_publications,
                len(gene_lit),
                len(variant_lit),
                len(drug_lit),
                datetime.now()
            ))
            self.logger.info(f"✓ SCHEMA-ALIGNED: Inserted literature summary for patient {patient_id}")
            return 1
        except Exception as e:
            self.logger.error(f"Could not insert literature summary: {e}")
            return 0
    
    def insert_processing_summary(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """
        ✅ SCHEMA-ALIGNED v2.0: Insert processing_summary
        CRITICAL FIX: Schema uses different column names
        Schema: patient_id, total_medication_variant_links, total_condition_disease_links,
                total_variant_phenotype_links, total_drug_variant_links,
                conflicts_total, conflicts_critical, conflicts_warnings, conflicts_info,
                patient_conditions_count, patient_medications_count,
                total_variants, variants_with_drug_data,
                analysis_timestamp, provenance_source, provenance_date, rdf_context
        """
        try:
            patient_id = profile.get("patient_id")
            
            # Count variants
            variants = profile.get("variants", [])
            total_variants = len(variants)
            variants_with_drug_data = sum(1 for v in variants if v.get("pharmgkb") or v.get("drugs"))
            
            # Count conflicts by severity - map to schema column names
            conflicts = profile.get("conflicts", [])
            conflicts_total = len(conflicts)
            conflicts_critical = sum(1 for c in conflicts if c.get("severity", "").upper() == "CRITICAL")
            conflicts_warnings = sum(1 for c in conflicts if c.get("severity", "").upper() in ("WARNING", "MODERATE"))
            conflicts_info = sum(1 for c in conflicts if c.get("severity", "").upper() in ("INFO", "MINOR"))
            
            # Count patient conditions and medications
            clinical_info = profile.get("clinical_information", {})
            patient_conditions_count = len(clinical_info.get("current_conditions", []))
            patient_medications_count = len(clinical_info.get("current_medications", []))
            
            # Count links (from variant_linking data if available)
            variant_linking = profile.get("variant_linking", {})
            links = variant_linking.get("links", {}) if variant_linking else {}
            total_medication_variant_links = len(links.get("medication_to_variant", []))
            total_condition_disease_links = len(links.get("condition_to_disease", []))
            total_variant_phenotype_links = len(links.get("variant_to_phenotype", []))
            total_drug_variant_links = len(links.get("drug_to_variant", []))
            
            # RDF context (if available)
            rdf_context = variant_linking.get("rdf_context") if variant_linking else None
            
            # SCHEMA-FIXED INSERT - match exact column names from schema
            cursor.execute("""
                INSERT INTO processing_summary (
                    patient_id, 
                    total_medication_variant_links, total_condition_disease_links,
                    total_variant_phenotype_links, total_drug_variant_links,
                    conflicts_total, conflicts_critical, conflicts_warnings, conflicts_info,
                    patient_conditions_count, patient_medications_count,
                    total_variants, variants_with_drug_data,
                    analysis_timestamp, provenance_source, provenance_date, rdf_context
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (patient_id) DO UPDATE SET
                    total_medication_variant_links = EXCLUDED.total_medication_variant_links,
                    total_condition_disease_links = EXCLUDED.total_condition_disease_links,
                    total_variant_phenotype_links = EXCLUDED.total_variant_phenotype_links,
                    total_drug_variant_links = EXCLUDED.total_drug_variant_links,
                    conflicts_total = EXCLUDED.conflicts_total,
                    conflicts_critical = EXCLUDED.conflicts_critical,
                    conflicts_warnings = EXCLUDED.conflicts_warnings,
                    conflicts_info = EXCLUDED.conflicts_info,
                    total_variants = EXCLUDED.total_variants,
                    variants_with_drug_data = EXCLUDED.variants_with_drug_data,
                    analysis_timestamp = EXCLUDED.analysis_timestamp,
                    provenance_date = EXCLUDED.provenance_date
            """, (
                patient_id,
                total_medication_variant_links,
                total_condition_disease_links,
                total_variant_phenotype_links,
                total_drug_variant_links,
                conflicts_total,
                conflicts_critical,
                conflicts_warnings,
                conflicts_info,
                patient_conditions_count,
                patient_medications_count,
                total_variants,
                variants_with_drug_data,
                datetime.now(),  # analysis_timestamp
                "PGx Dashboard",  # provenance_source
                datetime.now(),  # provenance_date
                json.dumps(rdf_context) if rdf_context else None  # rdf_context JSONB
            ))
            self.logger.info(f"✓ SCHEMA-ALIGNED: Inserted processing summary for patient {patient_id}")
            return 1
        except Exception as e:
            self.logger.error(f"Could not insert processing summary: {e}")
            return 0

