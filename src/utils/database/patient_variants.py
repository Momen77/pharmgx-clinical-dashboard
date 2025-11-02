"""
Patient Variants Loader - SCHEMA ALIGNED
Handles: pharmacogenomics_profiles, patient_variants
"""

import json
import logging
from datetime import datetime
from typing import Dict
import psycopg
from .utils import parse_date, generate_variant_key
from .data_extraction_utils import (
    extract_variant_gene,
    extract_variant_field,
    extract_from_jsonb,
    log_extraction_stats
)


class PatientVariantsLoader:
    """Loads patient variants and pharmacogenomics profiles"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def load_all(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """Load all patient variant data"""
        count = 0
        count += self.insert_pharmacogenomics_profile(cursor, profile)
        count += self.insert_patient_variants(cursor, profile)
        return count
    
    def insert_pharmacogenomics_profile(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """
        ✅ SCHEMA-ALIGNED: Insert pharmacogenomics profile
        Fixed: Removed variants_by_gene, affected_drugs (don't exist in schema)
               Added: provenance_source, provenance_date, rdf_context
        """
        try:
            patient_id = profile.get("patient_id")
            pgx_profile = profile.get("pharmacogenomics_profile", {})
            
            # SCHEMA-ALIGNED columns
            cursor.execute("""
                INSERT INTO pharmacogenomics_profiles (
                    patient_id, genes_analyzed, total_variants, analysis_date,
                    provenance_source, provenance_date, rdf_context
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (patient_id) DO UPDATE SET
                    genes_analyzed = EXCLUDED.genes_analyzed,
                    total_variants = EXCLUDED.total_variants,
                    analysis_date = EXCLUDED.analysis_date,
                    provenance_date = EXCLUDED.provenance_date
            """, (
                patient_id,
                json.dumps(pgx_profile.get("genes_analyzed", [])),
                pgx_profile.get("total_variants", 0),
                datetime.now(),  # analysis_date
                # FIXED: Added provenance fields
                "PGx Dashboard",  # provenance_source
                datetime.now(),  # provenance_date
                json.dumps(profile.get("@context"))  # rdf_context
            ))
            self.logger.info(f"✓ SCHEMA-ALIGNED: Inserted pharmacogenomics profile for patient {patient_id}")
            return 1
        except Exception as e:
            self.logger.error(f"Could not insert pharmacogenomics profile: {e}")
            return 0
    
    def insert_patient_variants(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """
        ✅ SCHEMA-ALIGNED: Insert patient_variants
        MAJOR FIX: Added 14+ missing columns including:
        - protein_id, consequence_type, wild_type, alternative_sequence
        - begin_position, end_position, codon, somatic_status, source_type
        - genomic_notation, hgvs_notation, raw_uniprot_data, raw_pharmgkb_data
        Removed: allele1, allele2, phase (don't exist in schema)
        """
        count = 0
        patient_id = profile.get("patient_id")
        variants = profile.get("variants", [])
        
        expected_count = len(variants)
        for variant in variants:
            try:
                # ✅ ROBUST EXTRACTION: Use comprehensive extraction with fallbacks
                gene_symbol = extract_variant_gene(variant)
                variant_id = extract_variant_field(
                    variant, "variant_id",
                    fallback_keys=["id", "@id", "variantId"],
                    default=""
                )
                rsid = extract_variant_field(
                    variant, "rsid",
                    fallback_keys=["rs_id", "rsId", "dbSNP"],
                    default=None
                )
                if rsid and isinstance(rsid, str):
                    rsid = rsid.replace("rs", "").strip()
                
                # Extract diplotype info
                diplotype_info = variant.get("diplotype", {})
                if isinstance(diplotype_info, str):
                    diplotype = diplotype_info
                else:
                    diplotype = diplotype_info.get("diplotype") if isinstance(diplotype_info, dict) else None
                
                # Phenotype
                phenotype = extract_variant_field(
                    variant, "phenotype",
                    fallback_keys=["predicted_phenotype", "predictedPhenotype", "hasPhenotype"],
                    default=None
                )
                
                # ✅ ROBUST EXTRACTION: Extract ALL required columns with fallbacks
                protein_id = extract_variant_field(
                    variant, "protein_id",
                    fallback_keys=["proteinId", "protein"],
                    jsonb_fields=["raw_uniprot_data"],
                    default=None
                )
                genotype = extract_variant_field(
                    variant, "genotype",
                    fallback_keys=["hasGenotype"],
                    default=None
                )
                zygosity = extract_variant_field(
                    variant, "zygosity",
                    fallback_keys=["zygosity_status"],
                    default=None
                )
                clinical_significance = extract_variant_field(
                    variant, "clinical_significance",
                    camel_case="clinicalSignificance",
                    nested_paths=[["clinicalSignificances", 0, "type"]],
                    default=None
                )
                
                # ✅ EXTRACT WITH FALLBACKS: Try direct, then nested, then JSONB
                consequence_type = extract_variant_field(
                    variant, "consequence_type",
                    camel_case="molecularConsequence",
                    nested_paths=[["molecularConsequence"]],
                    jsonb_fields=["raw_uniprot_data"],
                    default=None
                )
                wild_type = extract_variant_field(
                    variant, "wild_type",
                    camel_case="wildType",
                    jsonb_fields=["raw_uniprot_data"],
                    default=None
                )
                alternative_sequence = extract_variant_field(
                    variant, "alternativeSequence",
                    fallback_keys=["alternative_sequence", "mutated_sequence"],
                    jsonb_fields=["raw_uniprot_data"],
                    default=None
                )
                begin_position = extract_variant_field(
                    variant, "begin",
                    fallback_keys=["beginPosition", "start", "start_position"],
                    jsonb_fields=["raw_uniprot_data"],
                    default=None
                )
                end_position = extract_variant_field(
                    variant, "end",
                    fallback_keys=["endPosition", "stop"],
                    jsonb_fields=["raw_uniprot_data"],
                    default=None
                )
                codon = extract_variant_field(
                    variant, "codon",
                    jsonb_fields=["raw_uniprot_data"],
                    default=None
                )
                somatic_status = extract_variant_field(
                    variant, "somaticStatus",
                    fallback_keys=["somatic_status", "is_somatic"],
                    jsonb_fields=["raw_uniprot_data"],
                    default=None
                )
                source_type = extract_variant_field(
                    variant, "sourceType",
                    fallback_keys=["source_type", "data_source"],
                    jsonb_fields=["raw_uniprot_data"],
                    default=None
                )
                genomic_notation = extract_variant_field(
                    variant, "genomicNotation",
                    fallback_keys=["genomic_notation", "genomic_notation_hgvs"],
                    default=None
                )
                hgvs_notation = extract_variant_field(
                    variant, "hgvs",
                    fallback_keys=["hgvsNotation", "hgvs_notation", "hgvs_notation_cdna"],
                    default=None
                )
                
                # ✅ EXTRACT RAW DATA: Get existing raw data or build from available fields
                raw_uniprot_data = variant.get("raw_uniprot_data")
                if isinstance(raw_uniprot_data, str):
                    try:
                        raw_uniprot_data = json.loads(raw_uniprot_data)
                    except:
                        raw_uniprot_data = {}
                
                # If no raw_uniprot_data exists, build from available fields
                if not raw_uniprot_data or not isinstance(raw_uniprot_data, dict):
                    raw_uniprot_data = {
                        "alternativeSequence": alternative_sequence,
                        "begin": begin_position,
                        "end": end_position,
                        "codon": codon,
                        "molecularConsequence": consequence_type,
                        "wildType": wild_type,
                        "somaticStatus": somatic_status,
                        "sourceType": source_type,
                        "xrefs": variant.get("xrefs", []),
                        "genomicLocation": variant.get("genomicLocation") or variant.get("genomicLocations", []),
                        "evidences": variant.get("evidences", [])
                    }
                    # Remove None values
                    raw_uniprot_data = {k: v for k, v in raw_uniprot_data.items() if v is not None}
                
                # ✅ EXTRACT RAW PHARMGKB DATA
                raw_pharmgkb_data = variant.get("pharmgkb", {})
                if isinstance(raw_pharmgkb_data, str):
                    try:
                        raw_pharmgkb_data = json.loads(raw_pharmgkb_data)
                    except:
                        raw_pharmgkb_data = {}
                if not raw_pharmgkb_data or not isinstance(raw_pharmgkb_data, dict):
                    raw_pharmgkb_data = variant.get("raw_pharmgkb_data", {})
                    if isinstance(raw_pharmgkb_data, str):
                        try:
                            raw_pharmgkb_data = json.loads(raw_pharmgkb_data)
                        except:
                            raw_pharmgkb_data = {}
                
                # SCHEMA-ALIGNED INSERT with ALL columns
                cursor.execute("""
                    INSERT INTO patient_variants (
                        patient_id, gene_symbol, protein_id,
                        variant_id, rsid, genotype, diplotype, phenotype, zygosity,
                        clinical_significance, consequence_type,
                        wild_type, alternative_sequence, begin_position, end_position,
                        codon, somatic_status, source_type,
                        genomic_notation, hgvs_notation,
                        raw_uniprot_data, raw_pharmgkb_data
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (patient_id, variant_id) DO UPDATE SET
                        diplotype = EXCLUDED.diplotype,
                        phenotype = EXCLUDED.phenotype,
                        clinical_significance = EXCLUDED.clinical_significance,
                        raw_pharmgkb_data = EXCLUDED.raw_pharmgkb_data
                """, (
                    patient_id,
                    gene_symbol,
                    protein_id,  # FIXED: Added
                    variant_id,
                    rsid,
                    genotype,
                    diplotype,
                    phenotype,
                    zygosity,
                    clinical_significance,
                    consequence_type,  # FIXED: Added
                    wild_type,  # FIXED: Added
                    alternative_sequence,  # FIXED: Added
                    begin_position,  # FIXED: Added
                    end_position,  # FIXED: Added
                    codon,  # FIXED: Added
                    somatic_status,  # FIXED: Added
                    source_type,  # FIXED: Added
                    genomic_notation,  # FIXED: Added
                    hgvs_notation,  # FIXED: Added
                    json.dumps(raw_uniprot_data) if raw_uniprot_data else None,  # FIXED: Added
                    json.dumps(raw_pharmgkb_data) if raw_pharmgkb_data else None  # FIXED: Added
                ))
                count += 1
            except Exception as e:
                self.logger.warning(f"Could not insert patient variant {variant_id}: {e}")
        
        log_extraction_stats(count, expected_count, "patient_variants")
        self.logger.info(f"✓ SCHEMA-ALIGNED: Inserted {count} patient variants (with 22 columns)")
        return count

