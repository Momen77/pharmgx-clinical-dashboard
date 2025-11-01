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
        
        for variant in variants:
            try:
                gene_symbol = variant.get("gene")
                variant_id = variant.get("variant_id")
                rsid = variant.get("rsid")
                
                # Extract diplotype info
                diplotype_info = variant.get("diplotype", {})
                if isinstance(diplotype_info, str):
                    diplotype = diplotype_info
                else:
                    diplotype = diplotype_info.get("diplotype")
                
                # Phenotype
                phenotype = variant.get("phenotype") or variant.get("predicted_phenotype")
                
                # SCHEMA-ALIGNED: Extract ALL required columns
                protein_id = variant.get("protein_id")
                genotype = variant.get("genotype")
                zygosity = variant.get("zygosity")
                clinical_significance = variant.get("clinical_significance")
                
                # FIXED: Added missing columns
                consequence_type = variant.get("consequence_type") or variant.get("molecularConsequence")
                wild_type = variant.get("wild_type") or variant.get("wildType")
                alternative_sequence = variant.get("alternativeSequence")
                begin_position = variant.get("begin") or variant.get("beginPosition")
                end_position = variant.get("end") or variant.get("endPosition")
                codon = variant.get("codon")
                somatic_status = variant.get("somaticStatus")
                source_type = variant.get("sourceType")
                genomic_notation = variant.get("genomicNotation")
                hgvs_notation = variant.get("hgvs") or variant.get("hgvsNotation")
                
                # FIXED: Added raw data columns
                # Extract raw UniProt data (all UniProt-related fields)
                raw_uniprot_data = {
                    "alternativeSequence": variant.get("alternativeSequence"),
                    "begin": variant.get("begin"),
                    "end": variant.get("end"),
                    "codon": variant.get("codon"),
                    "molecularConsequence": variant.get("molecularConsequence"),
                    "wildType": variant.get("wildType"),
                    "somaticStatus": variant.get("somaticStatus"),
                    "sourceType": variant.get("sourceType"),
                    "xrefs": variant.get("xrefs", []),
                    "genomicLocation": variant.get("genomicLocation") or variant.get("genomicLocations", []),
                    "evidences": variant.get("evidences", [])
                }
                
                # Extract raw PharmGKB data
                raw_pharmgkb_data = variant.get("pharmgkb", {})
                
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
        
        self.logger.info(f"✓ SCHEMA-ALIGNED: Inserted {count} patient variants (with 22 columns)")
        return count

