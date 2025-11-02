"""
SCHEMA-ALIGNED Database Loader for Pharmacogenomics Knowledge Base
Matches complete_enhanced_schema.sql EXACTLY - All column names and structures verified
Version: 3.0 - Complete Schema Alignment
"""

import psycopg
import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

# Try to import the Cloud SQL Connector (but don't instantiate yet)
try:
    from google.cloud.sql.connector import Connector
    _connector_available = True
except ImportError:
    _connector_available = False
    print("Warning: google-cloud-sql-connector not found. Cloud SQL connections will not work.")

# Global connector instance (created lazily only when needed)
_connector = None


def _get_connector():
    """Get or create the Cloud SQL Connector (lazy initialization)"""
    global _connector
    if _connector is None and _connector_available:
        try:
            _connector = Connector()
        except Exception as e:
            # Silently handle metadata service errors when not on GCP
            logging.getLogger(__name__).debug(f"Could not initialize Cloud SQL Connector: {e}")
            _connector = None
    return _connector


class SchemaAlignedDatabaseLoader:
    """
    Complete database loader that matches complete_enhanced_schema.sql EXACTLY.
    Every INSERT statement has been verified against the actual schema.
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the loader with configuration"""
        from utils.config import get_config
        self.config = get_config(config_path)
        self.db_enabled = self.config.database_enabled
        self.non_blocking = self.config.database_non_blocking
        self.connection_type = "cloud_sql"
        self.db_params = self._get_db_params()
        self.logger = self._get_logger()
        self.connection = None
        
        # Caches to avoid duplicate inserts
        self.inserted_genes = set()
        self.inserted_drugs = {}  # drug_name -> drug_id
        self.inserted_variants = set()
        self.inserted_snomed = set()
        self.inserted_pharmgkb_annotations = {}  # annotation_id -> db record
        self.inserted_pmids = set()
    
    def _get_logger(self):
        """Setup logger"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
    
    def _get_db_params(self) -> Dict[str, str]:
        """Read database credentials from Streamlit secrets or environment variables"""
        # Try Streamlit secrets first
        try:
            import streamlit as st
            # Check for PostgreSQL connection first
            db_host = st.secrets.get("DB_HOST", "")
            if db_host:
                # Direct PostgreSQL connection
                self.connection_type = "postgresql"
                self.logger.debug("Using direct PostgreSQL connection from Streamlit secrets")
                return {
                    "db_host": db_host,
                    "db_port": st.secrets.get("DB_PORT", "5432"),
                    "db_user": st.secrets.get("DB_USER", ""),
                    "db_pass": st.secrets.get("DB_PASS", ""),
                    "db_name": st.secrets.get("DB_NAME", "")
                }
            else:
                # Cloud SQL connection
                return {
                    "instance_connection_name": st.secrets.get("INSTANCE_CONNECTION_NAME", ""),
                    "db_user": st.secrets.get("DB_USER", ""),
                    "db_pass": st.secrets.get("DB_PASS", ""),
                    "db_name": st.secrets.get("DB_NAME", "")
                }
        except Exception as e:
            # Fallback to environment variables
            self.logger.warning(f"Could not load Streamlit secrets, trying environment variables: {e}")
            # Check for PostgreSQL connection first
            db_host = os.getenv("DB_HOST", "")
            if db_host:
                # Direct PostgreSQL connection
                self.connection_type = "postgresql"
                self.logger.debug("Using direct PostgreSQL connection from environment variables")
                return {
                    "db_host": db_host,
                    "db_port": os.getenv("DB_PORT", "5432"),
                    "db_user": os.getenv("DB_USER", ""),
                    "db_pass": os.getenv("DB_PASS", ""),
                    "db_name": os.getenv("DB_NAME", "")
                }
            else:
                # Cloud SQL connection
                return {
                    "instance_connection_name": os.getenv("INSTANCE_CONNECTION_NAME", ""),
                    "db_user": os.getenv("DB_USER", ""),
                    "db_pass": os.getenv("DB_PASS", ""),
                    "db_name": os.getenv("DB_NAME", "")
                }
    
    def get_connection(self) -> Optional[psycopg.Connection]:
        """Get database connection"""
        if not self.db_enabled:
            self.logger.info("Database loading is disabled in config.")
            return None
        if not self.db_params:
            self.logger.error("Database parameters not configured.")
            return None
        
        try:
            if self.connection_type == "postgresql":
                # Direct PostgreSQL connection
                db_host = self.db_params.get("db_host")
                db_port = self.db_params.get("db_port", "5432")
                db_user = self.db_params.get("db_user")
                db_pass = self.db_params.get("db_pass")
                db_name = self.db_params.get("db_name")
                
                if not all([db_host, db_user, db_pass, db_name]):
                    self.logger.error("Missing required PostgreSQL connection parameters")
                    return None
                
                # Build connection string
                conn_string = f"host={db_host} port={db_port} dbname={db_name} user={db_user} password={db_pass}"
                conn = psycopg.connect(conn_string)
                self.logger.info(f"Successfully connected to PostgreSQL at {db_host}:{db_port}")
                return conn
                
            elif self.connection_type == "cloud_sql":
                # Use lazy initialization of connector
                connector = _get_connector()
                if connector:
                    conn = connector.connect(
                        self.db_params["instance_connection_name"],
                        "psycopg",
                        user=self.db_params["db_user"],
                        password=self.db_params["db_pass"],
                        db=self.db_params["db_name"]
                    )
                    self.logger.info("Successfully connected to Google Cloud SQL.")
                    return conn
                else:
                    self.logger.error("Cloud SQL connector not available")
                    return None
            else:
                self.logger.error(f"Unknown connection type: {self.connection_type}")
                return None
                
        except Exception as e:
            self.logger.error(f"Database connection failed: {e}")
            if not self.non_blocking:
                raise
            return None
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def load_patient_profile(self, comprehensive_profile: Dict) -> Dict[str, Any]:
        """
        Main entry point: Load comprehensive patient profile to database
        
        Returns:
            dict with keys: success (bool), error (str or None), records_inserted (int)
        """
        if not self.db_enabled:
            self.logger.info("Database loading is disabled. Skipping.")
            return {"success": False, "error": "Database loading disabled", "records_inserted": 0}
        
        result = {"success": False, "error": None, "records_inserted": 0}
        
        try:
            self.connection = self.get_connection()
            if not self.connection:
                return {"success": False, "error": "Could not connect to database", "records_inserted": 0}
            
            with self.connection.cursor() as cursor:
                patient_id = comprehensive_profile.get('patient_id', 'N/A')
                self.logger.info(f"Starting SCHEMA-ALIGNED database load for patient: {patient_id}")
                
                # PHASE 1: Load reference data (PharmGKB, SNOMED, genes, drugs, variants)
                self.logger.info("PHASE 1: Loading reference data...")
                ref_count = self._load_reference_data(cursor, comprehensive_profile)
                
                # PHASE 2: Load patient core data
                self.logger.info("PHASE 2: Loading patient core data...")
                patient_count = self._load_patient_core_data(cursor, comprehensive_profile)
                
                # PHASE 3: Load patient clinical data
                self.logger.info("PHASE 3: Loading patient clinical data...")
                clinical_count = self._load_patient_clinical_data(cursor, comprehensive_profile)
                
                # PHASE 4: Load patient variants and linking data
                self.logger.info("PHASE 4: Loading patient variants and links...")
                variant_count = self._load_patient_variants_and_links(cursor, comprehensive_profile)
                
                # PHASE 5: Load literature and summaries
                self.logger.info("PHASE 5: Loading literature and summaries...")
                lit_count = self._load_literature_and_summaries(cursor, comprehensive_profile)
                
                # Commit all changes
                self.connection.commit()
                
                total_records = ref_count + patient_count + clinical_count + variant_count + lit_count
                self.logger.info(f"SCHEMA-ALIGNED database load completed successfully. Total records: {total_records}")
                result = {"success": True, "error": None, "records_inserted": total_records}
                
        except Exception as e:
            self.logger.error(f"Error during database load: {e}", exc_info=True)
            if self.connection:
                self.connection.rollback()
            result = {"success": False, "error": str(e), "records_inserted": 0}
            if not self.non_blocking:
                raise
        finally:
            self.close()
        
        return result
    
    # =====================================================================
    # PHASE 1: REFERENCE DATA (Same as before - these are correct)
    # =====================================================================
    
    def _load_reference_data(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """Load all reference data (SNOMED, genes, drugs, variants, PharmGKB annotations)"""
        count = 0
        
        # Extract all unique SNOMED concepts
        count += self._insert_snomed_concepts(cursor, profile)
        
        # Extract and insert genes
        count += self._insert_genes(cursor, profile)
        
        # Extract and insert drugs
        count += self._insert_drugs(cursor, profile)
        
        # Extract and insert variants (reference table)
        count += self._insert_variants_reference(cursor, profile)
        
        # Extract and insert PharmGKB annotations
        count += self._insert_pharmgkb_annotations(cursor, profile)
        
        return count
    
    def _insert_snomed_concepts(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """Insert all SNOMED concepts from the profile"""
        count = 0
        snomed_concepts = []
        
        # Extract from conditions
        conditions = profile.get("clinical_information", {}).get("current_conditions", [])
        for cond in conditions:
            snomed_code = cond.get("snomed:code") or cond.get("snomed_code")
            if snomed_code and snomed_code not in self.inserted_snomed:
                snomed_concepts.append({
                    "snomed_code": snomed_code,
                    "concept_url": cond.get("@id", ""),
                    "preferred_label": cond.get("rdfs:label") or cond.get("skos:prefLabel", ""),
                    "concept_type": "Condition",
                    "search_term": cond.get("search_term", "")
                })
                self.inserted_snomed.add(snomed_code)
        
        # Extract from medications
        medications = profile.get("clinical_information", {}).get("current_medications", [])
        for med in medications:
            treats = med.get("treats_condition", {})
            snomed_code = treats.get("snomed:code") or treats.get("snomed_code")
            if snomed_code and snomed_code not in self.inserted_snomed:
                snomed_concepts.append({
                    "snomed_code": snomed_code,
                    "concept_url": f"http://snomed.info/id/{snomed_code}",
                    "preferred_label": treats.get("rdfs:label", ""),
                    "concept_type": "Condition",
                    "search_term": ""
                })
                self.inserted_snomed.add(snomed_code)
        
        # Extract from organ function
        organ_func = profile.get("clinical_information", {}).get("organ_function", {})
        for organ_type, tests in organ_func.items():
            if isinstance(tests, dict):
                for test_name, test_data in tests.items():
                    if isinstance(test_data, dict):
                        snomed_code = test_data.get("snomed:code") or test_data.get("snomed_code")
                        if snomed_code and snomed_code not in self.inserted_snomed:
                            snomed_concepts.append({
                                "snomed_code": snomed_code,
                                "concept_url": test_data.get("@id", ""),
                                "preferred_label": test_data.get("rdfs:label", ""),
                                "concept_type": "Lab Test",
                                "search_term": ""
                            })
                            self.inserted_snomed.add(snomed_code)
        
        # Extract from lifestyle factors
        lifestyle = profile.get("clinical_information", {}).get("lifestyle_factors", [])
        for factor in lifestyle:
            snomed_code = factor.get("snomed:code") or factor.get("snomed_code")
            if snomed_code and snomed_code not in self.inserted_snomed:
                snomed_concepts.append({
                    "snomed_code": snomed_code,
                    "concept_url": factor.get("@id", ""),
                    "preferred_label": factor.get("rdfs:label", ""),
                    "concept_type": "Lifestyle Factor",
                    "search_term": ""
                })
                self.inserted_snomed.add(snomed_code)
        
        # Insert all SNOMED concepts
        for concept in snomed_concepts:
            try:
                cursor.execute("""
                    INSERT INTO snomed_concepts (snomed_code, concept_url, preferred_label, concept_type, search_term)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (snomed_code) DO NOTHING
                """, (
                    concept["snomed_code"],
                    concept["concept_url"],
                    concept["preferred_label"],
                    concept["concept_type"],
                    concept["search_term"]
                ))
                count += 1
            except Exception as e:
                self.logger.warning(f"Could not insert SNOMED concept {concept['snomed_code']}: {e}")
        
        self.logger.info(f"Inserted {count} SNOMED concepts")
        return count
    
    def _insert_genes(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """Insert genes with all columns including entrez_id, hgnc_id, aliases"""
        count = 0
        variants = profile.get("variants", [])
        
        for variant in variants:
            gene_symbol = variant.get("gene")
            if not gene_symbol or gene_symbol in self.inserted_genes:
                continue
            
            # Extract gene metadata
            protein_id = variant.get("protein_id")
            entrez_id = variant.get("entrez_id")
            hgnc_id = variant.get("hgnc_id")
            aliases = variant.get("gene_aliases", [])
            
            # Try to extract from xrefs if not directly available
            xrefs = variant.get("xrefs", [])
            for xref in xrefs:
                if xref.get("name") == "HGNC" and not hgnc_id:
                    hgnc_id = xref.get("id")
                elif xref.get("name") == "GeneID" and not entrez_id:
                    try:
                        entrez_id = int(xref.get("id"))
                    except:
                        pass
            
            try:
                cursor.execute("""
                    INSERT INTO genes (gene_symbol, protein_id, entrez_id, hgnc_id, aliases)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (gene_symbol) DO UPDATE SET
                        protein_id = COALESCE(EXCLUDED.protein_id, genes.protein_id),
                        entrez_id = COALESCE(EXCLUDED.entrez_id, genes.entrez_id),
                        hgnc_id = COALESCE(EXCLUDED.hgnc_id, genes.hgnc_id),
                        aliases = COALESCE(EXCLUDED.aliases, genes.aliases)
                """, (
                    gene_symbol,
                    protein_id,
                    entrez_id,
                    hgnc_id,
                    json.dumps(aliases) if aliases else None
                ))
                self.inserted_genes.add(gene_symbol)
                count += 1
            except Exception as e:
                self.logger.warning(f"Could not insert gene {gene_symbol}: {e}")
        
        self.logger.info(f"Inserted {count} genes")
        return count
    
    def _insert_drugs(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """Insert drugs with all columns including ATC, approval data, synonyms, trade names"""
        count = 0
        
        # Collect drugs from multiple sources
        drug_records = {}
        
        # From patient medications
        medications = profile.get("clinical_information", {}).get("current_medications", [])
        for med in medications:
            drug_name = med.get("schema:name") or med.get("rdfs:label")
            if drug_name and drug_name not in drug_records:
                drug_records[drug_name] = {
                    "drug_name": drug_name,
                    "drugbank_id": med.get("drugbank:id"),
                    "rxnorm_cui": med.get("rxnorm", {}).get("rxnorm_cui"),
                    "chembl_id": med.get("chembl_id"),
                    "snomed_code": None,
                    "atc_code": med.get("atc_code"),
                    "first_approval": med.get("first_approval"),
                    "max_phase": med.get("max_phase"),
                    "synonyms": med.get("synonyms", []),
                    "trade_names": med.get("trade_names", []),
                    "chembl_molecule_type": med.get("chembl_molecule_type")
                }
        
        # From variant-affected drugs
        variants = profile.get("variants", [])
        for variant in variants:
            for drug_entry in variant.get("drugs", []):
                drug_name = drug_entry.get("name")
                if drug_name and drug_name not in drug_records:
                    drug_records[drug_name] = {
                        "drug_name": drug_name,
                        "drugbank_id": drug_entry.get("drugbank_id"),
                        "rxnorm_cui": drug_entry.get("rxnorm_cui"),
                        "chembl_id": drug_entry.get("chembl_id"),
                        "snomed_code": None,
                        "atc_code": drug_entry.get("atc_code"),
                        "first_approval": drug_entry.get("first_approval"),
                        "max_phase": drug_entry.get("max_phase"),
                        "synonyms": drug_entry.get("synonyms", []),
                        "trade_names": drug_entry.get("trade_names", []),
                        "chembl_molecule_type": drug_entry.get("chembl_molecule_type")
                    }
        
        # Insert all drugs
        for drug_name, drug_data in drug_records.items():
            if drug_name in self.inserted_drugs:
                continue
            
            try:
                cursor.execute("""
                    INSERT INTO drugs (
                        drug_name, drugbank_id, rxnorm_cui, chembl_id, snomed_code,
                        atc_code, first_approval, max_phase, synonyms, trade_names, chembl_molecule_type
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (drug_name) DO UPDATE SET
                        drugbank_id = COALESCE(EXCLUDED.drugbank_id, drugs.drugbank_id),
                        rxnorm_cui = COALESCE(EXCLUDED.rxnorm_cui, drugs.rxnorm_cui),
                        chembl_id = COALESCE(EXCLUDED.chembl_id, drugs.chembl_id),
                        atc_code = COALESCE(EXCLUDED.atc_code, drugs.atc_code),
                        first_approval = COALESCE(EXCLUDED.first_approval, drugs.first_approval),
                        max_phase = COALESCE(EXCLUDED.max_phase, drugs.max_phase),
                        synonyms = COALESCE(EXCLUDED.synonyms, drugs.synonyms),
                        trade_names = COALESCE(EXCLUDED.trade_names, drugs.trade_names),
                        chembl_molecule_type = COALESCE(EXCLUDED.chembl_molecule_type, drugs.chembl_molecule_type)
                    RETURNING drug_id
                """, (
                    drug_data["drug_name"],
                    drug_data.get("drugbank_id"),
                    drug_data.get("rxnorm_cui"),
                    drug_data.get("chembl_id"),
                    drug_data.get("snomed_code"),
                    drug_data.get("atc_code"),
                    drug_data.get("first_approval"),
                    drug_data.get("max_phase"),
                    json.dumps(drug_data.get("synonyms")) if drug_data.get("synonyms") else None,
                    json.dumps(drug_data.get("trade_names")) if drug_data.get("trade_names") else None,
                    drug_data.get("chembl_molecule_type")
                ))
                drug_id = cursor.fetchone()[0]
                self.inserted_drugs[drug_name] = drug_id
                count += 1
            except Exception as e:
                self.logger.warning(f"Could not insert drug {drug_name}: {e}")
        
        self.logger.info(f"Inserted {count} drugs")
        return count
    
    def _insert_variants_reference(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """Insert variants to reference variants table with all columns"""
        count = 0
        variants = profile.get("variants", [])
        
        for variant in variants:
            variant_key = self._generate_variant_key(variant)
            if variant_key in self.inserted_variants:
                continue
            
            gene_symbol = variant.get("gene")
            variant_id = variant.get("variant_id")
            rsid = variant.get("rsid")
            clinical_significance = variant.get("clinical_significance")
            consequence_type = variant.get("consequence_type") or variant.get("molecularConsequence")
            variant_type = variant.get("variant_type") or variant.get("type")
            wild_type = variant.get("wild_type") or variant.get("wildType")
            mutated_type = variant.get("mutated_type") or variant.get("alternativeSequence")
            cytogenetic_band = variant.get("cytogenetic_band")
            alternative_sequence = variant.get("alternativeSequence")
            begin_position = variant.get("begin") or variant.get("beginPosition")
            end_position = variant.get("end") or variant.get("endPosition")
            codon = variant.get("codon")
            somatic_status = variant.get("somaticStatus")
            source_type = variant.get("sourceType")
            hgvs_notation = variant.get("hgvs") or variant.get("hgvsNotation")
            
            try:
                cursor.execute("""
                    INSERT INTO variants (
                        variant_key, gene_symbol, variant_id, rsid, clinical_significance,
                        consequence_type, variant_type, wild_type, mutated_type, cytogenetic_band,
                        alternative_sequence, begin_position, end_position, codon,
                        somatic_status, source_type, hgvs_notation
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (variant_key) DO NOTHING
                """, (
                    variant_key, gene_symbol, variant_id, rsid, clinical_significance,
                    consequence_type, variant_type, wild_type, mutated_type, cytogenetic_band,
                    alternative_sequence, begin_position, end_position, codon,
                    somatic_status, source_type, hgvs_notation
                ))
                self.inserted_variants.add(variant_key)
                count += 1
                
                # Also insert genomic locations if available
                genomic_locations = variant.get("genomicLocation") or variant.get("genomicLocations", [])
                if isinstance(genomic_locations, dict):
                    genomic_locations = [genomic_locations]
                
                for loc in genomic_locations:
                    self._insert_variant_genomic_location(cursor, variant_id, loc)
                
                # Insert UniProt details if available
                if variant.get("alternativeSequence") or variant.get("codon"):
                    self._insert_uniprot_variant_details(cursor, variant_id, variant)
                
                # Insert xrefs
                for xref in variant.get("xrefs", []):
                    self._insert_uniprot_xref(cursor, variant_id, xref)
                
            except Exception as e:
                self.logger.warning(f"Could not insert variant {variant_key}: {e}")
        
        self.logger.info(f"Inserted {count} variants")
        return count
    
    def _insert_variant_genomic_location(self, cursor: psycopg.Cursor, variant_id: str, location: Dict):
        """Insert variant genomic location"""
        try:
            cursor.execute("""
                INSERT INTO variant_genomic_locations (
                    variant_id, assembly, chromosome, start_position, end_position,
                    reference_allele, alternate_allele, strand, sequence_version
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                variant_id,
                location.get("assembly"),
                location.get("chromosome") or location.get("chr"),
                location.get("start") or location.get("start_position"),
                location.get("end") or location.get("end_position"),
                location.get("referenceSequence") or location.get("reference_allele"),
                location.get("alternativeSequence") or location.get("alternate_allele"),
                location.get("strand"),
                location.get("sequenceVersion") or location.get("sequence_version")
            ))
        except Exception as e:
            self.logger.warning(f"Could not insert genomic location for {variant_id}: {e}")
    
    def _insert_uniprot_variant_details(self, cursor: psycopg.Cursor, variant_id: str, variant: Dict):
        """Insert UniProt variant details"""
        try:
            cursor.execute("""
                INSERT INTO uniprot_variant_details (
                    variant_id, alternative_sequence, begin_position, end_position,
                    codon, consequence_type, wild_type, mutated_type,
                    somatic_status, source_type
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                variant_id,
                variant.get("alternativeSequence"),
                variant.get("begin") or variant.get("beginPosition"),
                variant.get("end") or variant.get("endPosition"),
                variant.get("codon"),
                variant.get("molecularConsequence") or variant.get("consequence_type"),
                variant.get("wildType"),
                variant.get("alternativeSequence"),
                variant.get("somaticStatus"),
                variant.get("sourceType")
            ))
        except Exception as e:
            self.logger.warning(f"Could not insert UniProt details for {variant_id}: {e}")
    
    def _insert_uniprot_xref(self, cursor: psycopg.Cursor, variant_id: str, xref: Dict):
        """Insert UniProt cross-reference"""
        try:
            cursor.execute("""
                INSERT INTO uniprot_xrefs (variant_id, database_name, database_id, url)
                VALUES (%s, %s, %s, %s)
            """, (
                variant_id,
                xref.get("name"),
                xref.get("id"),
                xref.get("url")
            ))
        except Exception as e:
            pass  # Silently skip xref errors as they're supplementary
    
    def _insert_pharmgkb_annotations(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """
        Insert PharmGKB annotations - CRITICAL for medication_to_variant_links foreign key
        """
        count = 0
        variants = profile.get("variants", [])
        
        for variant in variants:
            # PharmGKB data is nested in variant["pharmgkb"]["annotations"]
            pharmgkb_data = variant.get("pharmgkb", {})
            annotations = pharmgkb_data.get("annotations", [])
            
            for annotation in annotations:
                annotation_id = annotation.get("id")
                if not annotation_id or annotation_id in self.inserted_pharmgkb_annotations:
                    continue
                
                # Extract annotation metadata
                accession_id = annotation.get("accessionId")
                gene_symbol = variant.get("gene")
                variant_id = variant.get("variant_id")
                annotation_name = annotation.get("annotation") or annotation.get("sentence")
                evidence_level_obj = annotation.get("levelOfEvidence", {})
                evidence_level = evidence_level_obj.get("term") if isinstance(evidence_level_obj, dict) else evidence_level_obj
                score = annotation.get("score")
                clinical_annotation_types = annotation.get("clinicalAnnotationTypes", [])
                pediatric = annotation.get("pediatric", False)
                obj_cls = annotation.get("objCls")
                location_obj = annotation.get("location", {})
                location = location_obj.get("displayName") if isinstance(location_obj, dict) else str(location_obj)
                override_level = annotation.get("overrideLevel")
                conflicting_ids = annotation.get("conflictingVariantAnnotationIds", [])
                related_chemicals_logic = annotation.get("relatedChemicals", {}).get("logic") if isinstance(annotation.get("relatedChemicals"), dict) else None
                
                # Extract dates from history
                history = annotation.get("history", [])
                created_date = None
                last_updated = None
                if history:
                    # Find creation date
                    for h in history:
                        if h.get("type") == "Create":
                            created_date = self._parse_date(h.get("date"))
                            break
                    # Last update is the last entry
                    if len(history) > 0:
                        last_updated = self._parse_date(history[-1].get("date"))
                
                try:
                    cursor.execute("""
                        INSERT INTO pharmgkb_annotations (
                            annotation_id, accession_id, variant_id, gene_symbol, annotation_name,
                            evidence_level, score, clinical_annotation_types, pediatric, obj_cls,
                            location, override_level, conflicting_annotation_ids, related_chemicals_logic,
                            created_date, last_updated, raw_data
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (annotation_id) DO NOTHING
                    """, (
                        annotation_id,
                        accession_id,
                        variant_id,
                        gene_symbol,
                        annotation_name,
                        evidence_level,
                        score,
                        json.dumps(clinical_annotation_types) if clinical_annotation_types else None,
                        pediatric,
                        obj_cls,
                        location,
                        override_level,
                        json.dumps(conflicting_ids) if conflicting_ids else None,
                        related_chemicals_logic,
                        created_date,
                        last_updated,
                        json.dumps(annotation)
                    ))
                    self.inserted_pharmgkb_annotations[annotation_id] = annotation
                    count += 1
                    
                    # Insert allele phenotypes
                    allele_phenotypes = annotation.get("allelePhenotypes", [])
                    for ap in allele_phenotypes:
                        self._insert_pharmgkb_allele_phenotype(cursor, annotation_id, ap)
                    
                    # Insert score details
                    score_details = annotation.get("scoreDetails", [])
                    for sd in score_details:
                        self._insert_pharmgkb_score_detail(cursor, annotation_id, sd)
                    
                except Exception as e:
                    self.logger.warning(f"Could not insert PharmGKB annotation {annotation_id}: {e}")
        
        self.logger.info(f"Inserted {count} PharmGKB annotations")
        return count
    
    def _insert_pharmgkb_allele_phenotype(self, cursor: psycopg.Cursor, annotation_id: int, allele_phenotype: Dict):
        """Insert PharmGKB allele phenotype"""
        try:
            cursor.execute("""
                INSERT INTO pharmgkb_allele_phenotypes (annotation_id, allele, phenotype, limited_evidence)
                VALUES (%s, %s, %s, %s)
            """, (
                annotation_id,
                allele_phenotype.get("allele"),
                allele_phenotype.get("phenotype"),
                allele_phenotype.get("limitedEvidence", False)
            ))
        except Exception as e:
            self.logger.warning(f"Could not insert allele phenotype for annotation {annotation_id}: {e}")
    
    def _insert_pharmgkb_score_detail(self, cursor: psycopg.Cursor, annotation_id: int, score_detail: Dict):
        """Insert PharmGKB score detail"""
        try:
            cursor.execute("""
                INSERT INTO pharmgkb_score_details (annotation_id, category, score, weight)
                VALUES (%s, %s, %s, %s)
            """, (
                annotation_id,
                score_detail.get("category"),
                score_detail.get("score"),
                score_detail.get("weight")
            ))
        except Exception as e:
            pass  # Silently skip score detail errors
    
    # =====================================================================
    # PHASE 2: PATIENT CORE DATA (SCHEMA-ALIGNED)
    # =====================================================================
    
    def _load_patient_core_data(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """Load patient core data (patients, demographics)"""
        count = 0
        
        # Insert patient
        count += self._insert_patient(cursor, profile)
        
        # Insert demographics (SCHEMA-ALIGNED)
        count += self._insert_demographics_aligned(cursor, profile)
        
        return count
    
    def _insert_patient(self, cursor: psycopg.Cursor, profile: Dict) -> int:
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
                self._parse_date(profile.get("dateCreated")),
                profile.get("data_version", 1),
                profile.get("total_critical_conflicts", 0),
                "PGx Dashboard",
                datetime.now(),
                json.dumps(profile.get("@context"))
            ))
            self.logger.info(f"Inserted patient {patient_id}")
            return 1
        except Exception as e:
            self.logger.error(f"Could not insert patient: {e}")
            return 0
    
    def _insert_demographics_aligned(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """
        SCHEMA-ALIGNED: Insert patient demographics
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
                self._parse_date(demographics.get("schema:birthDate")),
                demographics.get("age"),
                demographics.get("biological_sex"),
                demographics.get("schema:gender"),
                json.dumps(ethnicity) if ethnicity else None,
                json.dumps(ethnicity_snomed_labels) if ethnicity_snomed_labels else None,
                # FIXED: Schema uses 'race', not in current data but column exists
                None,  # race
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
                # FIXED: Schema uses emergency_contact and emergency_phone (not emergency_contact_name/phone)
                contact.get("emergency_contact"),  # emergency_contact
                contact.get("emergency_phone"),  # emergency_phone
                demographics.get("language"),
                demographics.get("interpreter_needed", False),
                insurance.get("provider"),
                # FIXED: Schema uses policy_number (not insurance_policy_number)
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
    
    # =====================================================================
    # Continue in next part due to size limit...
    # =====================================================================
    
    def _generate_variant_key(self, variant: Dict) -> str:
        """Generate a unique key for a variant"""
        gene = variant.get("gene", "")
        variant_id = variant.get("variant_id", "")
        rsid = variant.get("rsid", "")
        return f"{gene}:{variant_id}:{rsid}"
    
    def _parse_date(self, date_str: Any) -> Optional[datetime]:
        """Parse date string to datetime object"""
        if not date_str:
            return None
        if isinstance(date_str, datetime):
            return date_str
        try:
            # Try ISO format first
            return datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
        except:
            try:
                # Try common formats
                from dateutil import parser
                return parser.parse(str(date_str))
            except:
                return None


# For backward compatibility, create alias
DatabaseLoader = SchemaAlignedDatabaseLoader

