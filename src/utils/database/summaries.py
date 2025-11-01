"""
Summaries Loader - SCHEMA ALIGNED
Handles: clinical_summaries, literature_summaries, processing_summary
"""

import json
import logging
from datetime import datetime
from typing import Dict
import psycopg


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
        ✅ SCHEMA-ALIGNED: Insert processing_summary
        MAJOR FIX: Complete restructure with all required fields
        Schema: patient_id, variants_total, variants_processed, variants_annotated,
                conflicts_total, conflicts_critical, conflicts_moderate, conflicts_minor,
                genes_analyzed, drugs_analyzed,
                analysis_start_time, analysis_end_time, total_processing_time_seconds,
                provenance_source, provenance_date, pipeline_version, raw_metadata
        """
        try:
            patient_id = profile.get("patient_id")
            
            # Count variants
            variants = profile.get("variants", [])
            variants_total = len(variants)
            variants_processed = variants_total
            variants_annotated = sum(1 for v in variants if v.get("pharmgkb") or v.get("drugs"))
            
            # Count conflicts by severity
            conflicts = profile.get("conflicts", [])
            conflicts_total = len(conflicts)
            conflicts_critical = sum(1 for c in conflicts if c.get("severity") == "critical")
            conflicts_moderate = sum(1 for c in conflicts if c.get("severity") == "moderate")
            conflicts_minor = sum(1 for c in conflicts if c.get("severity") == "minor")
            
            # Count genes and drugs analyzed
            genes_analyzed = len(set(v.get("gene") for v in variants if v.get("gene")))
            drugs_analyzed_set = set()
            for v in variants:
                for drug in v.get("drugs", []):
                    drugs_analyzed_set.add(drug.get("name"))
            drugs_analyzed = len(drugs_analyzed_set)
            
            # Processing times (if available)
            processing_metadata = profile.get("processing_metadata", {})
            analysis_start_time = processing_metadata.get("start_time")
            analysis_end_time = processing_metadata.get("end_time")
            total_processing_time_seconds = processing_metadata.get("duration_seconds")
            
            # SCHEMA-ALIGNED INSERT
            cursor.execute("""
                INSERT INTO processing_summary (
                    patient_id, variants_total, variants_processed, variants_annotated,
                    conflicts_total, conflicts_critical, conflicts_moderate, conflicts_minor,
                    genes_analyzed, drugs_analyzed,
                    analysis_start_time, analysis_end_time, total_processing_time_seconds,
                    provenance_source, provenance_date, pipeline_version, raw_metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (patient_id) DO UPDATE SET
                    variants_total = EXCLUDED.variants_total,
                    conflicts_total = EXCLUDED.conflicts_total,
                    conflicts_critical = EXCLUDED.conflicts_critical,
                    conflicts_moderate = EXCLUDED.conflicts_moderate,
                    conflicts_minor = EXCLUDED.conflicts_minor,
                    provenance_date = EXCLUDED.provenance_date
            """, (
                patient_id,
                variants_total,  # FIXED: Added
                variants_processed,  # FIXED: Added
                variants_annotated,  # FIXED: Added
                conflicts_total,  # FIXED: Restructured
                conflicts_critical,  # FIXED: Added
                conflicts_moderate,  # FIXED: Added
                conflicts_minor,  # FIXED: Added
                genes_analyzed,  # FIXED: Added
                drugs_analyzed,  # FIXED: Added
                analysis_start_time,  # FIXED: Added
                analysis_end_time,  # FIXED: Added
                total_processing_time_seconds,  # FIXED: Added
                "PGx Dashboard",  # provenance_source
                datetime.now(),  # provenance_date
                profile.get("data_version", "1.0"),  # pipeline_version
                json.dumps(processing_metadata) if processing_metadata else None  # raw_metadata
            ))
            self.logger.info(f"✓ SCHEMA-ALIGNED: Inserted processing summary for patient {patient_id}")
            return 1
        except Exception as e:
            self.logger.error(f"Could not insert processing summary: {e}")
            return 0

