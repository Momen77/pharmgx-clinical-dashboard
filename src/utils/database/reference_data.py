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
        count += self.insert_variant_predictions(cursor, profile)
        count += self.insert_clinvar_submissions(cursor, profile)
        count += self.insert_recommended_tests(cursor, profile)
        count += self.insert_snomed_mappings(cursor, profile)
        count += self.insert_source_metadata(cursor, profile)
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
            self.logger.debug(f"Could not insert genomic location for {variant_id}: {e}")
    
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
            self.logger.debug(f"Could not insert UniProt details for {variant_id}: {e}")
    
    def _insert_uniprot_xref(self, cursor, variant_id, xref):
        """Insert UniProt cross-reference"""
        try:
            cursor.execute("""
                INSERT INTO uniprot_xrefs (variant_id, database_name, database_id, url)
                VALUES (%s, %s, %s, %s)
            """, (variant_id, xref.get("name"), xref.get("id"), xref.get("url")))
        except Exception as e:
            self.logger.debug(f"Could not insert UniProt xref for {variant_id}: {e}")
    
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
                    
                    # Insert allele phenotypes (will also insert genotypes)
                    for ap in annotation.get("allelePhenotypes", []):
                        self._insert_allele_phenotype(cursor, annotation_id, ap)
                    
                    # Insert score details
                    for sd in annotation.get("scoreDetails", []):
                        self._insert_score_detail(cursor, annotation_id, sd)
                    
                    # Insert annotation history
                    if history:
                        self._insert_annotation_history(cursor, annotation_id, history)
                    
                    # Insert related chemicals and links
                    related_chemicals = annotation.get("relatedChemicals", [])
                    if isinstance(related_chemicals, list):
                        for chem in related_chemicals:
                            self._insert_pharmgkb_chemical_and_link(cursor, annotation_id, chem)
                    
                    # Insert related guidelines and links
                    related_guidelines = annotation.get("relatedGuidelines", [])
                    if isinstance(related_guidelines, list):
                        for guideline in related_guidelines:
                            self._insert_pharmgkb_guideline_and_link(cursor, annotation_id, guideline)
                    
                    # Insert related labels and links
                    related_labels = annotation.get("relatedLabels", [])
                    if isinstance(related_labels, list):
                        for label in related_labels:
                            self._insert_pharmgkb_label_and_link(cursor, annotation_id, label)
                    
                    # Insert related diseases and links
                    related_diseases = annotation.get("relatedDiseases", [])
                    if isinstance(related_diseases, list):
                        for disease in related_diseases:
                            self._insert_pharmgkb_disease_and_link(cursor, annotation_id, disease)
                    
                    # Insert related variations and links
                    related_variations = annotation.get("relatedVariations", [])
                    if isinstance(related_variations, list):
                        for variation in related_variations:
                            self._insert_pharmgkb_variation_and_link(cursor, annotation_id, variation)
                    
                except Exception as e:
                    self.logger.warning(f"Could not insert PharmGKB annotation {annotation_id}: {e}")
        
        self.logger.info(f"✓ Inserted {count} PharmGKB annotations")
        return count
    
    def _insert_allele_phenotype(self, cursor, annotation_id, ap):
        """Insert PharmGKB allele phenotype and associated genotypes"""
        try:
            # Get phenotype text (can be string or dict)
            phenotype_text = ap.get("phenotypeText") or ap.get("phenotype", "")
            if isinstance(phenotype_text, dict):
                phenotype_text = phenotype_text.get("text", "") or str(phenotype_text)
            
            cursor.execute("""
                INSERT INTO pharmgkb_allele_phenotypes (annotation_id, allele, genotype, phenotype_text, limited_evidence)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING phenotype_id
            """, (
                annotation_id,
                ap.get("allele"),
                ap.get("genotype"),
                str(phenotype_text),
                ap.get("limitedEvidence", False)
            ))
            
            phenotype_id = cursor.fetchone()[0]
            
            # Insert genotypes if present
            genotypes = ap.get("genotypes", []) or ap.get("genotypeNotations", [])
            if isinstance(genotypes, list):
                for genotype in genotypes:
                    if isinstance(genotype, dict):
                        genotype_notation = genotype.get("notation") or genotype.get("genotype") or str(genotype)
                        notation_system = genotype.get("notationSystem") or genotype.get("system") or "PharmGKB"
                    else:
                        genotype_notation = str(genotype)
                        notation_system = "PharmGKB"
                    
                    try:
                        cursor.execute("""
                            INSERT INTO pharmgkb_allele_genotypes (phenotype_id, genotype_notation, notation_system)
                            VALUES (%s, %s, %s)
                            ON CONFLICT DO NOTHING
                        """, (phenotype_id, genotype_notation, notation_system))
                    except Exception as e:
                        self.logger.debug(f"Could not insert genotype {genotype_notation}: {e}")
            
        except Exception as e:
            self.logger.debug(f"Could not insert allele phenotype: {e}")
    
    def _insert_score_detail(self, cursor, annotation_id, sd):
        """Insert PharmGKB score detail"""
        try:
            cursor.execute("""
                INSERT INTO pharmgkb_score_details (annotation_id, category, score, weight)
                VALUES (%s, %s, %s, %s)
            """, (annotation_id, sd.get("category"), sd.get("score"), sd.get("weight")))
        except:
            pass
    
    def _insert_annotation_history(self, cursor, annotation_id, history):
        """Insert PharmGKB annotation history"""
        for h in history:
            try:
                version = h.get("version") or len(history)  # Use index as version if not provided
                change_type = h.get("type") or h.get("changeType") or "Update"
                history_date = parse_date(h.get("date"))
                
                cursor.execute("""
                    INSERT INTO pharmgkb_annotation_history (
                        annotation_id, accession_id, version, history_date, change_type
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (
                    annotation_id,
                    h.get("accessionId") or h.get("accession_id"),
                    version,
                    history_date,
                    change_type
                ))
            except Exception as e:
                self.logger.debug(f"Could not insert annotation history: {e}")
    
    def _insert_pharmgkb_chemical_and_link(self, cursor, annotation_id, chem):
        """Insert PharmGKB chemical and link to annotation"""
        try:
            pharmgkb_id = chem.get("pharmgkbId") or chem.get("id")
            if not pharmgkb_id:
                return
            
            # Insert or get chemical
            cursor.execute("""
                INSERT INTO pharmgkb_chemicals (pharmgkb_id, name, obj_cls)
                VALUES (%s, %s, %s)
                ON CONFLICT (pharmgkb_id) DO UPDATE SET
                    name = COALESCE(EXCLUDED.name, pharmgkb_chemicals.name),
                    obj_cls = COALESCE(EXCLUDED.obj_cls, pharmgkb_chemicals.obj_cls)
                RETURNING chemical_id
            """, (
                pharmgkb_id,
                chem.get("name"),
                chem.get("objCls") or chem.get("obj_cls")
            ))
            
            chemical_id = cursor.fetchone()[0]
            
            # Insert link
            cursor.execute("""
                INSERT INTO pharmgkb_annotation_chemicals (annotation_id, chemical_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (annotation_id, chemical_id))
            
        except Exception as e:
            self.logger.debug(f"Could not insert chemical {chem.get('name')}: {e}")
    
    def _insert_pharmgkb_guideline_and_link(self, cursor, annotation_id, guideline):
        """Insert PharmGKB guideline and link to annotation"""
        try:
            pharmgkb_id = guideline.get("pharmgkbId") or guideline.get("id")
            if not pharmgkb_id:
                return
            
            # Insert or get guideline
            cursor.execute("""
                INSERT INTO pharmgkb_guidelines (pharmgkb_id, name, source, url, obj_cls)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (pharmgkb_id) DO UPDATE SET
                    name = COALESCE(EXCLUDED.name, pharmgkb_guidelines.name),
                    source = COALESCE(EXCLUDED.source, pharmgkb_guidelines.source),
                    url = COALESCE(EXCLUDED.url, pharmgkb_guidelines.url)
                RETURNING guideline_id
            """, (
                pharmgkb_id,
                guideline.get("name"),
                guideline.get("source"),
                guideline.get("url"),
                guideline.get("objCls") or guideline.get("obj_cls")
            ))
            
            guideline_id = cursor.fetchone()[0]
            
            # Insert link
            cursor.execute("""
                INSERT INTO pharmgkb_annotation_guidelines (annotation_id, guideline_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (annotation_id, guideline_id))
            
        except Exception as e:
            self.logger.debug(f"Could not insert guideline {guideline.get('name')}: {e}")
    
    def _insert_pharmgkb_label_and_link(self, cursor, annotation_id, label):
        """Insert PharmGKB label and link to annotation"""
        try:
            pharmgkb_id = label.get("pharmgkbId") or label.get("id")
            if not pharmgkb_id:
                return
            
            # Insert or get label
            cursor.execute("""
                INSERT INTO pharmgkb_labels (pharmgkb_id, name, source, obj_cls)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (pharmgkb_id) DO UPDATE SET
                    name = COALESCE(EXCLUDED.name, pharmgkb_labels.name),
                    source = COALESCE(EXCLUDED.source, pharmgkb_labels.source)
                RETURNING label_id
            """, (
                pharmgkb_id,
                label.get("name"),
                label.get("source"),
                label.get("objCls") or label.get("obj_cls")
            ))
            
            label_id = cursor.fetchone()[0]
            
            # Insert link
            cursor.execute("""
                INSERT INTO pharmgkb_annotation_labels (annotation_id, label_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (annotation_id, label_id))
            
        except Exception as e:
            self.logger.debug(f"Could not insert label {label.get('name')}: {e}")
    
    def _insert_pharmgkb_disease_and_link(self, cursor, annotation_id, disease):
        """Insert PharmGKB disease and link to annotation"""
        try:
            pharmgkb_id = disease.get("pharmgkbId") or disease.get("id")
            if not pharmgkb_id:
                return
            
            # Insert or get disease
            cursor.execute("""
                INSERT INTO pharmgkb_diseases (pharmgkb_id, name, obj_cls)
                VALUES (%s, %s, %s)
                ON CONFLICT (pharmgkb_id) DO UPDATE SET
                    name = COALESCE(EXCLUDED.name, pharmgkb_diseases.name)
                RETURNING disease_id
            """, (
                pharmgkb_id,
                disease.get("name"),
                disease.get("objCls") or disease.get("obj_cls")
            ))
            
            disease_id = cursor.fetchone()[0]
            
            # Insert link
            cursor.execute("""
                INSERT INTO pharmgkb_annotation_diseases (annotation_id, disease_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (annotation_id, disease_id))
            
        except Exception as e:
            self.logger.debug(f"Could not insert disease {disease.get('name')}: {e}")
    
    def _insert_pharmgkb_variation_and_link(self, cursor, annotation_id, variation):
        """Insert PharmGKB variation and link to annotation"""
        try:
            pharmgkb_id = variation.get("pharmgkbId") or variation.get("id")
            if not pharmgkb_id:
                return
            
            # Insert or get variation
            cursor.execute("""
                INSERT INTO pharmgkb_variations (pharmgkb_id, name, obj_cls)
                VALUES (%s, %s, %s)
                ON CONFLICT (pharmgkb_id) DO UPDATE SET
                    name = COALESCE(EXCLUDED.name, pharmgkb_variations.name)
                RETURNING variation_id
            """, (
                pharmgkb_id,
                variation.get("name"),
                variation.get("objCls") or variation.get("obj_cls")
            ))
            
            variation_id = cursor.fetchone()[0]
            
            # Insert link
            cursor.execute("""
                INSERT INTO pharmgkb_annotation_variations (annotation_id, variation_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (annotation_id, variation_id))
            
        except Exception as e:
            self.logger.debug(f"Could not insert variation {variation.get('name')}: {e}")
    
    def insert_variant_predictions(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """✅ SCHEMA-ALIGNED: Insert variant_predictions"""
        count = 0
        variants = profile.get("variants", [])
        
        for variant in variants:
            variant_id = variant.get("variant_id")
            predictions = variant.get("predictions", []) or variant.get("prediction_scores", {})
            
            # Handle both list and dict formats
            if isinstance(predictions, dict):
                # Convert dict to list of predictions
                predictions_list = []
                for tool, pred_data in predictions.items():
                    if isinstance(pred_data, dict):
                        predictions_list.append({
                            "tool": tool,
                            "prediction": pred_data.get("prediction"),
                            "score": pred_data.get("score"),
                            "confidence": pred_data.get("confidence")
                        })
                    else:
                        predictions_list.append({
                            "tool": tool,
                            "prediction": str(pred_data),
                            "score": None,
                            "confidence": None
                        })
                predictions = predictions_list
            
            for pred in predictions:
                if not isinstance(pred, dict):
                    continue
                
                try:
                    cursor.execute("""
                        INSERT INTO variant_predictions (
                            variant_id, tool, prediction, score, confidence
                        )
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (
                        variant_id,
                        pred.get("tool") or pred.get("predictor"),
                        pred.get("prediction"),
                        pred.get("score"),
                        pred.get("confidence")
                    ))
                    count += 1
                except Exception as e:
                    self.logger.debug(f"Could not insert variant prediction: {e}")
        
        self.logger.info(f"✓ Inserted {count} variant predictions")
        return count
    
    def insert_clinvar_submissions(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """✅ SCHEMA-ALIGNED: Insert clinvar_submissions"""
        count = 0
        variants = profile.get("variants", [])
        
        for variant in variants:
            variant_id = variant.get("variant_id")
            clinvar_data = variant.get("clinvar", {})
            
            # Handle both dict and list formats
            submissions = []
            if isinstance(clinvar_data, list):
                submissions = clinvar_data
            elif isinstance(clinvar_data, dict):
                # Single submission as dict
                if clinvar_data.get("clinvar_id") or clinvar_data.get("id"):
                    submissions = [clinvar_data]
                # Or check for submissions key
                elif clinvar_data.get("submissions"):
                    submissions = clinvar_data["submissions"] if isinstance(clinvar_data["submissions"], list) else [clinvar_data["submissions"]]
            
            for submission in submissions:
                if not isinstance(submission, dict):
                    continue
                
                try:
                    cursor.execute("""
                        INSERT INTO clinvar_submissions (
                            variant_id, clinvar_id, clinical_significance,
                            review_status, last_evaluated, submitter, condition
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (
                        variant_id,
                        submission.get("clinvar_id") or submission.get("id"),
                        submission.get("clinical_significance") or submission.get("clinicalSignificance"),
                        submission.get("review_status") or submission.get("reviewStatus"),
                        parse_date(submission.get("last_evaluated") or submission.get("lastEvaluated")),
                        submission.get("submitter"),
                        submission.get("condition") or submission.get("condition_name")
                    ))
                    count += 1
                except Exception as e:
                    self.logger.debug(f"Could not insert ClinVar submission: {e}")
        
        self.logger.info(f"✓ Inserted {count} ClinVar submissions")
        return count
    
    def insert_recommended_tests(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """✅ SCHEMA-ALIGNED: Insert recommended_tests"""
        count = 0
        variants = profile.get("variants", [])
        
        for variant in variants:
            variant_id = variant.get("variant_id")
            gene_symbol = variant.get("gene")
            
            # Extract recommended tests from variant metadata
            recommended_tests = variant.get("recommended_tests", []) or variant.get("recommendedTests", [])
            
            # If variant has high clinical significance, recommend PGx testing
            clinical_significance = variant.get("clinical_significance", "").lower()
            if "pathogenic" in clinical_significance or "drug response" in clinical_significance:
                # Add default PGx test recommendation
                recommended_tests.append({
                    "test_name": f"{gene_symbol} Pharmacogenomics Testing",
                    "test_type": "Pharmacogenomic Panel",
                    "indication": f"Variant {variant_id} has {variant.get('clinical_significance', 'clinical significance')}",
                    "priority": "High" if "pathogenic" in clinical_significance else "Medium"
                })
            
            for test in recommended_tests:
                if not isinstance(test, dict):
                    continue
                
                try:
                    cursor.execute("""
                        INSERT INTO recommended_tests (
                            variant_id, gene_symbol, test_name, test_type,
                            indication, priority, lab_method, turnaround_time
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (
                        variant_id,
                        gene_symbol,
                        test.get("test_name") or test.get("name"),
                        test.get("test_type") or test.get("type"),
                        test.get("indication"),
                        test.get("priority", "Medium"),
                        test.get("lab_method") or test.get("method"),
                        test.get("turnaround_time") or test.get("turnaroundTime")
                    ))
                    count += 1
                except Exception as e:
                    self.logger.debug(f"Could not insert recommended test: {e}")
        
        self.logger.info(f"✓ Inserted {count} recommended tests")
        return count
    
    def insert_snomed_mappings(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """✅ SCHEMA-ALIGNED: Insert snomed_mappings"""
        count = 0
        
        # Map SNOMED codes from conditions
        conditions = profile.get("clinical_information", {}).get("current_conditions", [])
        for cond in conditions:
            snomed_code = cond.get("snomed:code") or cond.get("snomed_code")
            if snomed_code:
                try:
                    cursor.execute("""
                        INSERT INTO snomed_mappings (
                            mapping_type, snomed_code, label, entity_id, entity_type
                        )
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (
                        "condition",
                        snomed_code,
                        cond.get("rdfs:label") or cond.get("skos:prefLabel", ""),
                        cond.get("@id", ""),
                        "Condition"
                    ))
                    count += 1
                except Exception as e:
                    self.logger.debug(f"Could not insert SNOMED condition mapping: {e}")
        
        # Map SNOMED codes from medications (if they have SNOMED codes)
        medications = profile.get("clinical_information", {}).get("current_medications", [])
        for med in medications:
            snomed_code = med.get("snomed:code") or med.get("snomed_code")
            if snomed_code:
                drug_name = med.get("schema:name") or med.get("rdfs:label")
                try:
                    cursor.execute("""
                        INSERT INTO snomed_mappings (
                            mapping_type, snomed_code, label, entity_id, entity_type
                        )
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (
                        "medication",
                        snomed_code,
                        drug_name,
                        med.get("@id", ""),
                        "Medication"
                    ))
                    count += 1
                except Exception as e:
                    self.logger.debug(f"Could not insert SNOMED medication mapping: {e}")
        
        self.logger.info(f"✓ Inserted {count} SNOMED mappings")
        return count
    
    def insert_source_metadata(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """✅ SCHEMA-ALIGNED: Insert/update source_metadata"""
        count = 0
        
        # Define default source metadata
        sources = [
            {
                "source_name": "PharmGKB",
                "version": "2024.1",  # Default version - should be updated with actual version
                "description": "PharmGKB clinical annotations and drug-variant relationships"
            },
            {
                "source_name": "ClinVar",
                "version": "2024",
                "description": "ClinVar variant clinical significance submissions"
            },
            {
                "source_name": "gnomAD",
                "version": "v4.0",
                "description": "gnomAD population frequency data"
            },
            {
                "source_name": "UniProt",
                "version": "2024_01",
                "description": "UniProt variant and protein data"
            }
        ]
        
        from datetime import date
        for source in sources:
            try:
                cursor.execute("""
                    INSERT INTO source_metadata (
                        source_name, version, last_updated, description
                    )
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (source_name) DO UPDATE SET
                        version = EXCLUDED.version,
                        last_updated = EXCLUDED.last_updated,
                        description = EXCLUDED.description
                """, (
                    source["source_name"],
                    source["version"],
                    date.today(),
                    source["description"]
                ))
                count += 1
            except Exception as e:
                self.logger.debug(f"Could not insert source metadata for {source['source_name']}: {e}")
        
        self.logger.info(f"✓ Inserted/updated {count} source metadata records")
        return count

