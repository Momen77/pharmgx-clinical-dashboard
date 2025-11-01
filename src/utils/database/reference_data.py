"""
Reference Data Loader
Handles: SNOMED concepts, genes, drugs, variants, PharmGKB annotations
"""

import json
import logging
from typing import Dict, List
import psycopg
from .utils import parse_date


class ReferenceDataLoader:
    """Loads reference data into the database"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.inserted_genes = set()
        self.inserted_drugs = {}  # drug_name -> drug_id
        self.inserted_variants = set()
        self.inserted_snomed = set()
        self.inserted_pharmgkb_annotations = {}
    
    def load_all(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """Load all reference data"""
        count = 0
        count += self.insert_snomed_concepts(cursor, profile)
        count += self.insert_genes(cursor, profile)
        count += self.insert_drugs(cursor, profile)
        count += self.insert_variants_reference(cursor, profile)
        count += self.insert_pharmgkb_annotations(cursor, profile)
        return count
    
    def insert_snomed_concepts(self, cursor: psycopg.Cursor, profile: Dict) -> int:
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
        
        self.logger.info(f"✓ Inserted {count} SNOMED concepts")
        return count
    
    def insert_genes(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """Insert genes with all columns"""
        count = 0
        variants = profile.get("variants", [])
        
        for variant in variants:
            gene_symbol = variant.get("gene")
            if not gene_symbol or gene_symbol in self.inserted_genes:
                continue
            
            protein_id = variant.get("protein_id")
            entrez_id = variant.get("entrez_id")
            hgnc_id = variant.get("hgnc_id")
            aliases = variant.get("gene_aliases", [])
            
            # Try to extract from xrefs
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
        
        self.logger.info(f"✓ Inserted {count} genes")
        return count
    
    def insert_drugs(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """Insert drugs with all columns"""
        count = 0
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
        
        self.logger.info(f"✓ Inserted {count} drugs")
        return count
    
    def insert_variants_reference(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """Insert variants to reference variants table"""
        count = 0
        variants = profile.get("variants", [])
        
        for variant in variants:
            from .utils import generate_variant_key
            variant_key = generate_variant_key(variant)
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
                
                # Also insert related tables
                genomic_locations = variant.get("genomicLocation") or variant.get("genomicLocations", [])
                if isinstance(genomic_locations, dict):
                    genomic_locations = [genomic_locations]
                
                for loc in genomic_locations:
                    self._insert_genomic_location(cursor, variant_id, loc)
                
                if variant.get("alternativeSequence") or variant.get("codon"):
                    self._insert_uniprot_details(cursor, variant_id, variant)
                
                for xref in variant.get("xrefs", []):
                    self._insert_uniprot_xref(cursor, variant_id, xref)
                
            except Exception as e:
                self.logger.warning(f"Could not insert variant {variant_key}: {e}")
        
        self.logger.info(f"✓ Inserted {count} variants")
        return count
    
    def _insert_genomic_location(self, cursor, variant_id, location):
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
            pass
    
    def _insert_uniprot_details(self, cursor, variant_id, variant):
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
            pass
    
    def _insert_uniprot_xref(self, cursor, variant_id, xref):
        """Insert UniProt cross-reference"""
        try:
            cursor.execute("""
                INSERT INTO uniprot_xrefs (variant_id, database_name, database_id, url)
                VALUES (%s, %s, %s, %s)
            """, (variant_id, xref.get("name"), xref.get("id"), xref.get("url")))
        except:
            pass
    
    def insert_pharmgkb_annotations(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """Insert PharmGKB annotations - CRITICAL for medication_to_variant_links"""
        count = 0
        variants = profile.get("variants", [])
        
        for variant in variants:
            pharmgkb_data = variant.get("pharmgkb", {})
            annotations = pharmgkb_data.get("annotations", [])
            
            for annotation in annotations:
                annotation_id = annotation.get("id")
                if not annotation_id or annotation_id in self.inserted_pharmgkb_annotations:
                    continue
                
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
                    for h in history:
                        if h.get("type") == "Create":
                            created_date = parse_date(h.get("date"))
                            break
                    if len(history) > 0:
                        last_updated = parse_date(history[-1].get("date"))
                
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
                        annotation_id, accession_id, variant_id, gene_symbol, annotation_name,
                        evidence_level, score,
                        json.dumps(clinical_annotation_types) if clinical_annotation_types else None,
                        pediatric, obj_cls, location, override_level,
                        json.dumps(conflicting_ids) if conflicting_ids else None,
                        related_chemicals_logic, created_date, last_updated,
                        json.dumps(annotation)
                    ))
                    self.inserted_pharmgkb_annotations[annotation_id] = annotation
                    count += 1
                    
                    # Insert allele phenotypes
                    for ap in annotation.get("allelePhenotypes", []):
                        self._insert_allele_phenotype(cursor, annotation_id, ap)
                    
                    # Insert score details
                    for sd in annotation.get("scoreDetails", []):
                        self._insert_score_detail(cursor, annotation_id, sd)
                    
                except Exception as e:
                    self.logger.warning(f"Could not insert PharmGKB annotation {annotation_id}: {e}")
        
        self.logger.info(f"✓ Inserted {count} PharmGKB annotations")
        return count
    
    def _insert_allele_phenotype(self, cursor, annotation_id, ap):
        """Insert PharmGKB allele phenotype"""
        try:
            cursor.execute("""
                INSERT INTO pharmgkb_allele_phenotypes (annotation_id, allele, phenotype, limited_evidence)
                VALUES (%s, %s, %s, %s)
            """, (annotation_id, ap.get("allele"), ap.get("phenotype"), ap.get("limitedEvidence", False)))
        except:
            pass
    
    def _insert_score_detail(self, cursor, annotation_id, sd):
        """Insert PharmGKB score detail"""
        try:
            cursor.execute("""
                INSERT INTO pharmgkb_score_details (annotation_id, category, score, weight)
                VALUES (%s, %s, %s, %s)
            """, (annotation_id, sd.get("category"), sd.get("score"), sd.get("weight")))
        except:
            pass

