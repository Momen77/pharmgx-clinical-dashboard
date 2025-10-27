"""
JSON-LD Exporter
Exports knowledge graph as JSON-LD
"""
import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime


class JSONLDExporter:
    """Exports knowledge graph to JSON-LD format"""
    
    def __init__(self):
        """Initialize JSON-LD exporter"""
        self.output_dir = Path("output/json")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def build_context(self) -> Dict:
        """Build JSON-LD @context"""
        return {
            "@vocab": "http://schema.org/",
            "foaf": "http://xmlns.com/foaf/0.1/",
            "sio": "http://semanticscience.org/resource/",
            "obo": "http://purl.obolibrary.org/obo/",
            "dbsnp": "https://identifiers.org/dbsnp:",
            "uniprot": "https://identifiers.org/uniprot:",
            "rxnorm": "https://identifiers.org/rxnorm:",
            "snomed": "http://snomed.info/id/",
            "clinvar": "https://identifiers.org/clinvar:",
            "chembl": "https://www.ebi.ac.uk/chembl/compound_report_card/",
            "hasVariant": "sio:SIO_000008",
            "hasGenotype": "sio:SIO_000228",
            "affectsDrug": "sio:SIO_000253",
            "associatedWithDisease": "sio:SIO_000668",
            "hasEvidence": "sio:SIO_000772",
            "hasBioactivity": "sio:SIO_000008",
            "hasMechanism": "sio:SIO_000017"
        }
    
    def build_patient_node(self, patient_data: Dict, genotype_id: str) -> Dict:
        """Build patient node for JSON-LD"""
        # Handle both old and new patient data formats
        identifier = patient_data.get("identifier") or patient_data.get("foaf:identifier") or patient_data.get("schema:identifier")
        name = patient_data.get("name") or patient_data.get("foaf:name") or patient_data.get("schema:name")
        description = patient_data.get("description") or patient_data.get("schema:description")
        date_created = patient_data.get("dateCreated") or patient_data.get("schema:dateCreated", {}).get("@value")
        
        return {
            "@id": patient_data["@id"],
            "@type": ["foaf:Person", "Patient"],
            "identifier": identifier,
            "name": name,
            "dateCreated": date_created,
            "description": description,
            "hasGenotype": {"@id": genotype_id}
        }
    
    def build_genotype_node(self, gene_symbol: str, variants: List[Dict], phenotype_info: Dict = None) -> Dict:
        """Build genotype node for JSON-LD"""
        genotype_id = f"http://pgx-kg.org/genotype/geno_{gene_symbol.lower()}_001"
        
        variant_refs = []
        for variant in variants:
            rsid = self._get_rsid(variant)
            if rsid:
                variant_refs.append({"@id": f"dbsnp:{rsid}"})
        
        # Calculate summary stats
        drug_response = sum(1 for v in variants if self._has_drug_response(v))
        pathogenic = sum(1 for v in variants if self._is_pathogenic(v))
        affected_drugs = self._count_affected_drugs(variants)
        
        genotype_node = {
            "@id": genotype_id,
            "@type": "obo:GENO_0000536",
            "label": f"Pharmacogenomics Genotype Profile for {gene_symbol}",
            "dateCreated": datetime.now().date().isoformat(),
            "description": f"Genetic profile containing {len(variants)} clinically significant variants",
            "hasVariant": variant_refs,
            "summary": {
                "totalVariants": len(variants),
                "drugResponseVariants": drug_response,
                "pathogenicVariants": pathogenic,
                "affectedDrugsCount": affected_drugs
            }
        }
        
        # Add metabolizer phenotype if available
        if phenotype_info:
            genotype_node["metabolizerPhenotype"] = phenotype_info.get("phenotype", "Not determined")
            genotype_node["diplotype"] = phenotype_info.get("diplotype", "Unknown/Unknown")
            genotype_node["functionality"] = phenotype_info.get("functionality", "Unknown/Unknown")
            if phenotype_info.get("star_alleles"):
                genotype_node["starAlleles"] = phenotype_info["star_alleles"]
        
        return genotype_node
    
    def build_variant_nodes(self, variants: List[Dict], gene_symbol: str, protein_id: str) -> List[Dict]:
        """Build variant nodes for JSON-LD"""
        variant_nodes = []
        
        for variant in variants:
            rsid = self._get_rsid(variant)
            if not rsid:
                continue
            
            node = {
                "@id": f"dbsnp:{rsid}",
                "@type": "obo:SO_0001583",
                "identifier": f"rs{rsid}",
                "gene": {"@id": f"uniprot:{protein_id}"},
                "label": f"{gene_symbol} (rs{rsid})"
            }
            
            # Add protein change
            protein_change = self._get_protein_change(variant)
            if protein_change:
                node["proteinChange"] = protein_change
            
            # Add clinical significance
            clin_sigs = [sig["type"] for sig in variant.get("clinicalSignificances", [])]
            if clin_sigs:
                node["clinicalSignificance"] = clin_sigs[0]
            
            # Add ClinVar data
            if "clinvar" in variant:
                node["clinvar"] = self._build_clinvar_node(variant["clinvar"])
            
            # Add phenotypes with SNOMED
            if "phenotypes_snomed" in variant:
                node["phenotypes"] = self._build_phenotype_nodes(variant["phenotypes_snomed"])
            
            # Add drugs
            if "pharmgkb" in variant and "drugs" in variant["pharmgkb"]:
                node["affectsDrug"] = self._build_drug_nodes(variant["pharmgkb"]["drugs"])
            
            # Add clinical findings (phenotypes)
            if "phenotypes_snomed" in variant:
                node["associatedWithClinicalFinding"] = self._build_clinical_finding_nodes(variant["phenotypes_snomed"])
            
            # Add direct disease associations
            if "disease_associations" in variant:
                node["associatedWithDisease"] = self._build_disease_association_nodes(variant["disease_associations"])
            
            # Add comprehensive disease mappings
            if "phenotypes_comprehensive" in variant:
                comprehensive_diseases = self._build_disease_nodes_from_comprehensive(variant["phenotypes_comprehensive"])
                if "associatedWithDisease" in node:
                    # Merge with existing disease associations
                    existing_codes = {d.get("@id") for d in node["associatedWithDisease"]}
                    for disease in comprehensive_diseases:
                        if disease.get("@id") not in existing_codes:
                            node["associatedWithDisease"].append(disease)
                else:
                    node["associatedWithDisease"] = comprehensive_diseases
            
            # Add literature
            if "literature" in variant:
                node["literature"] = self._build_literature_nodes(variant["literature"])
            
            variant_nodes.append(node)
        
        return variant_nodes
    
    def build_gene_node(self, protein_id: str, gene_symbol: str, gene_info: Dict) -> Dict:
        """Build gene node for JSON-LD"""
        node = {
            "@id": f"uniprot:{protein_id}",
            "@type": "obo:SO_0000704",
            "identifier": protein_id,
            "label": gene_symbol,
            "name": gene_symbol
        }
        
        if gene_info:
            if "gene_name" in gene_info:
                node["alternateName"] = gene_info["gene_name"]
            if "ncbi_gene_id" in gene_info:
                node["ncbiGene"] = {"@id": f"https://identifiers.org/ncbigene:{gene_info['ncbi_gene_id']}"}
        
        return node
    
    def _get_rsid(self, variant: Dict) -> str:
        """Extract rsID from variant"""
        for xref in variant.get("xrefs", []):
            if xref.get("name") == "dbSNP":
                return xref.get("id", "").replace("rs", "")
        return None
    
    def _get_protein_change(self, variant: Dict) -> str:
        """Extract protein change from variant"""
        for loc in variant.get("locations", []):
            if "loc" in loc and loc["loc"].startswith("p."):
                return loc["loc"]
        return None
    
    def _has_drug_response(self, variant: Dict) -> bool:
        """Check if variant affects drug response"""
        for sig in variant.get("clinicalSignificances", []):
            if "drug" in sig["type"].lower() or "response" in sig["type"].lower():
                return True
        return False
    
    def _is_pathogenic(self, variant: Dict) -> bool:
        """Check if variant is pathogenic"""
        for sig in variant.get("clinicalSignificances", []):
            if "pathogenic" in sig["type"].lower():
                return True
        return False
    
    def _count_affected_drugs(self, variants: List[Dict]) -> int:
        """Count unique affected drugs"""
        drugs = set()
        for variant in variants:
            if "pharmgkb" in variant and "drugs" in variant["pharmgkb"]:
                for drug in variant["pharmgkb"]["drugs"]:
                    drugs.add(drug["name"])
        return len(drugs)
    
    def _build_clinvar_node(self, clinvar_data: Dict) -> Dict:
        """Build ClinVar sub-node"""
        node = {
            "@id": f"clinvar:{clinvar_data.get('clinvar_id', '')}",
            "clinicalSignificance": clinvar_data.get("clinical_significance"),
            "reviewStatus": clinvar_data.get("review_status"),
            "starRating": clinvar_data.get("star_rating", 0)
        }
        
        # Add evidence interpretation if available
        if clinvar_data.get("evidence_interpretation"):
            node["evidenceInterpretation"] = clinvar_data["evidence_interpretation"]
        
        return node
    
    def _build_phenotype_nodes(self, phenotypes: List[Dict]) -> List[Dict]:
        """Build phenotype nodes with SNOMED"""
        nodes = []
        for pheno in phenotypes:
            node = {"text": pheno["text"]}
            if pheno.get("snomed"):
                node["snomed"] = {
                    "@id": f"snomed:{pheno['snomed']['code']}",
                    "label": pheno['snomed']['label']
                }
            nodes.append(node)
        return nodes
    
    def _build_drug_nodes(self, drugs: List[Dict]) -> List[Dict]:
        """Build drug nodes with ChEMBL and RxNorm data"""
        nodes = []
        for drug in drugs[:5]:  # Limit to 5
            node = {"name": drug["name"]}
            
            # Prefer ChEMBL ID if available
            if drug.get("chembl_data") and drug["chembl_data"].get("chembl_id"):
                chembl_id = drug["chembl_data"]["chembl_id"]
                node["@id"] = f"https://www.ebi.ac.uk/chembl/compound_report_card/{chembl_id}/"
                node["chemblId"] = chembl_id
                
                # Add ChEMBL compound info including ADMET properties
                compound_info = drug["chembl_data"].get("compound_info", {})
                if compound_info.get("pref_name"):
                    node["preferredName"] = compound_info["pref_name"]
                if compound_info.get("molecule_type"):
                    node["moleculeType"] = compound_info["molecule_type"]
                if compound_info.get("max_phase"):
                    node["clinicalPhase"] = compound_info["max_phase"]
                if compound_info.get("molecular_weight"):
                    node["molecularWeight"] = compound_info["molecular_weight"]
                # ADMET properties
                if compound_info.get("alogp"):
                    node["alogP"] = compound_info["alogp"]  # Partition coefficient (absorption)
                if compound_info.get("hbd"):
                    node["hydrogenBondDonors"] = compound_info["hbd"]  # Distribution/absorption
                if compound_info.get("hba"):
                    node["hydrogenBondAcceptors"] = compound_info["hba"]  # Distribution/absorption
                if compound_info.get("psa"):
                    node["polarSurfaceArea"] = compound_info["psa"]  # Absorption/Bioavailability
                if compound_info.get("rtb"):
                    node["rotatableBonds"] = compound_info["rtb"]  # Flexibility (distribution)
                if compound_info.get("num_ro5_violations") is not None:
                    node["lipinskiViolations"] = compound_info["num_ro5_violations"]  # Drug-likeness
                
                # Add pharmacogenomic bioactivities with target ChEMBL IDs
                pgx_bioactivities = drug["chembl_data"].get("pgx_bioactivities", [])
                if pgx_bioactivities:
                    node["pgxBioactivities"] = []
                    for bioactivity in pgx_bioactivities[:5]:  # Top 5 for better coverage
                        bio_node = {
                            "targetChemblId": bioactivity.get("target_chembl_id"),
                            "targetName": bioactivity.get("target_name"),
                            "targetType": bioactivity.get("target_type"),
                            "targetGeneSymbol": bioactivity.get("target_gene_symbol"),
                            "assayType": bioactivity.get("assay_type"),
                            "bioactivityType": bioactivity.get("bioactivity_type")
                        }
                        if bioactivity.get("value") and bioactivity.get("units"):
                            value_str = f"{bioactivity['value']} {bioactivity['units']}"
                            if bioactivity.get("relation"):
                                value_str = f"{bioactivity['relation']} {value_str}"
                            bio_node["value"] = value_str
                        if bioactivity.get("assay_description"):
                            bio_node["assayDescription"] = bioactivity["assay_description"][:200]
                        node["pgxBioactivities"].append(bio_node)
                
                # Add mechanism of action
                mechanisms = drug["chembl_data"].get("mechanism_of_action", [])
                if mechanisms:
                    node["mechanismOfAction"] = []
                    for mech in mechanisms[:2]:  # Top 2
                        mech_node = {
                            "description": mech.get("mechanism_of_action"),
                            "targetName": mech.get("target_name"),
                            "actionType": mech.get("action_type")
                        }
                        node["mechanismOfAction"].append(mech_node)
            
            # Add RxNorm if available
            elif drug.get("rxnorm"):
                node["@id"] = f"rxnorm:{drug['rxnorm']['rxnorm_cui']}"
                node["rxnormCui"] = drug["rxnorm"]["rxnorm_cui"]
            
            # Add PharmGKB recommendation
            if drug.get("recommendation"):
                node["recommendation"] = drug["recommendation"]
            if drug.get("evidence_level"):
                node["evidenceLevel"] = drug["evidence_level"]
            # Add evidence interpretation if available
            if drug.get("evidence_interpretation"):
                node["evidenceInterpretation"] = drug["evidence_interpretation"]
            
            nodes.append(node)
        return nodes
    
    def _build_clinical_finding_nodes(self, phenotypes: List[Dict]) -> List[Dict]:
        """Build clinical finding nodes with SNOMED"""
        nodes = []
        for phenotype in phenotypes:
            # Handle both old and new data structures
            phenotype_text = phenotype.get("phenotype_text") or phenotype.get("text", "")
            
            # Use full phenotype text from finding if available, otherwise use truncated version
            finding = phenotype.get("snomed_clinical_finding") or phenotype.get("snomed")
            if finding and finding.get("phenotype_text"):
                full_phenotype_text = finding["phenotype_text"]
            else:
                full_phenotype_text = phenotype_text
            
            node = {
                "phenotype_text": full_phenotype_text  # Store full text, not truncated
            }
            
            # Handle both old and new SNOMED field names
            if finding:
                node["@id"] = f"snomed:{finding['code']}"
                node["label"] = finding['label']
                if finding.get("match_type"):
                    node["match_type"] = finding["match_type"]
                # Use full search_term from finding if available
                if finding.get("search_term"):
                    node["search_term"] = finding["search_term"]
                elif finding.get("phenotype_text"):
                    node["search_term"] = finding["phenotype_text"]
                # Include full post-coordinated expression for FHIR compatibility
                if finding.get("expression"):
                    node["snomedExpression"] = finding["expression"]
                # Include attributes for machine-readable processing
                if finding.get("attributes"):
                    node["attributes"] = finding["attributes"]
            nodes.append(node)
        return nodes
    
    def _build_disease_nodes_from_comprehensive(self, comprehensive_mappings: List[Dict]) -> List[Dict]:
        """Build disease nodes from comprehensive phenotype mappings"""
        disease_nodes = []
        
        for mapping in comprehensive_mappings:
            # Add extracted diseases
            for disease_mapping in mapping.get("extracted_diseases", []):
                if disease_mapping.get("snomed_mapping"):
                    snomed = disease_mapping["snomed_mapping"]
                    disease_nodes.append({
                        "@id": f"snomed:{snomed['code']}",
                        "label": snomed["label"],
                        "extractedFrom": disease_mapping["extracted_text"],
                        "source": "text_extraction"
                    })
            
            # Add diseases from SNOMED hierarchy
            hierarchy = mapping.get("snomed_disease_hierarchy")
            if hierarchy:
                for disease_ancestor in hierarchy.get("disease_ancestors", []):
                    disease_nodes.append({
                        "@id": f"snomed:{disease_ancestor['code']}",
                        "label": disease_ancestor["label"],
                        "source": "snomed_hierarchy",
                        "derivedFromClinicalFinding": hierarchy["clinical_finding_code"]
                    })
        
        # Remove duplicates based on SNOMED code
        seen_codes = set()
        unique_diseases = []
        for disease in disease_nodes:
            code = disease["@id"]
            if code not in seen_codes:
                seen_codes.add(code)
                unique_diseases.append(disease)
        
        return unique_diseases
    
    def _build_disease_association_nodes(self, disease_associations: List[Dict]) -> List[Dict]:
        """Build disease nodes from direct ClinVar and PharmGKB associations"""
        disease_nodes = []
        
        for disease_assoc in disease_associations:
            if disease_assoc.get("snomed_mapping"):
                snomed = disease_assoc["snomed_mapping"]
                disease_nodes.append({
                    "@id": f"snomed:{snomed['code']}",
                    "label": snomed["label"],
                    "originalName": disease_assoc["disease_name"],
                    "source": disease_assoc["source"],
                    "context": disease_assoc.get("original_phenotype", "")
                })
            else:
                # Disease without SNOMED mapping
                disease_name = disease_assoc["disease_name"]
                disease_nodes.append({
                    "@id": f"http://pgx-kg.org/disease/{disease_name.replace(' ', '_').lower()}",
                    "label": disease_name,
                    "originalName": disease_name,
                    "source": disease_assoc["source"],
                    "context": disease_assoc.get("original_phenotype", ""),
                    "mapped": False
                })
        
        # Remove duplicates based on disease name
        seen_names = set()
        unique_diseases = []
        for disease in disease_nodes:
            name = disease.get("originalName", "").lower()
            if name not in seen_names:
                seen_names.add(name)
                unique_diseases.append(disease)
        
        return unique_diseases
    
    def _build_literature_nodes(self, literature: Dict) -> Dict:
        """Build literature evidence nodes with full text URLs"""
        nodes = {}
        
        # Gene publications (UniProt PubMed evidence)
        if literature.get("gene_publications"):
            nodes["genePublications"] = [
                {
                    "pmid": pub.get("pmid"),
                    "pmcid": pub.get("pmcid"),
                    "doi": pub.get("doi"),
                    "title": pub.get("title"),
                    "authors": pub.get("authors", []),
                    "journal": pub.get("journal"),
                    "year": pub.get("pub_year"),
                    "abstract": pub.get("abstract", "")[:500] + "..." if pub.get("abstract") and len(pub.get("abstract", "")) > 500 else pub.get("abstract", ""),
                    "citationCount": pub.get("citation_count", 0),
                    "url": pub.get("url"),
                    "fullTextUrl": pub.get("full_text_url"),
                    "pdfUrl": pub.get("pdf_url"),
                    "openAccess": pub.get("open_access", False),
                    "source": pub.get("source", "UniProt"),
                    "evidenceCode": pub.get("evidence_code")
                }
                for pub in literature.get("gene_publications", [])[:5]  # Up to 5 publications
            ]
        
        # Variant-specific publications
        if literature.get("variant_specific_publications"):
            nodes["variantPublications"] = [
                {
                    "pmid": pub.get("pmid"),
                    "pmcid": pub.get("pmcid"),
                    "doi": pub.get("doi"),
                    "title": pub.get("title"),
                    "authors": pub.get("authors", []),
                    "journal": pub.get("journal"),
                    "year": pub.get("pub_year"),
                    "abstract": pub.get("abstract", "")[:500] + "..." if pub.get("abstract") and len(pub.get("abstract", "")) > 500 else pub.get("abstract", ""),
                    "citationCount": pub.get("citation_count", 0),
                    "url": pub.get("url"),
                    "fullTextUrl": pub.get("full_text_url"),
                    "pdfUrl": pub.get("pdf_url"),
                    "openAccess": pub.get("open_access", False),
                    "source": pub.get("source", "UniProt"),
                    "evidenceCode": pub.get("evidence_code"),
                    "searchVariant": pub.get("search_variant")
                }
                for pub in literature.get("variant_specific_publications", [])[:5]
            ]
        
        # Drug-specific publications
        if literature.get("drug_publications"):
            nodes["drugPublications"] = {}
            for drug_name, pubs in literature.get("drug_publications", {}).items():
                nodes["drugPublications"][drug_name] = [
                    {
                        "pmid": pub.get("pmid"),
                        "pmcid": pub.get("pmcid"),
                        "doi": pub.get("doi"),
                        "title": pub.get("title"),
                        "authors": pub.get("authors", []),
                        "journal": pub.get("journal"),
                        "year": pub.get("pub_year"),
                        "abstract": pub.get("abstract", "")[:500] + "..." if pub.get("abstract") and len(pub.get("abstract", "")) > 500 else pub.get("abstract", ""),
                        "citationCount": pub.get("citation_count", 0),
                        "url": pub.get("url"),
                        "fullTextUrl": pub.get("full_text_url"),
                        "pdfUrl": pub.get("pdf_url"),
                        "openAccess": pub.get("open_access", False),
                        "searchTerms": pub.get("search_terms")
                    }
                    for pub in pubs[:3]  # Up to 3 per drug
                ]
        
        return nodes if nodes else {"genePublications": []}
    
    def export(self, enriched_data: Dict, patient_data: Dict, gene_symbol: str) -> str:
        """Export complete JSON-LD knowledge graph"""
        genotype_id = f"http://pgx-kg.org/genotype/geno_{gene_symbol.lower()}_001"
        
        # Build JSON-LD structure
        jsonld = {
            "@context": self.build_context(),
            "@graph": [
                self.build_patient_node(patient_data, genotype_id),
                self.build_genotype_node(
                    gene_symbol, 
                    enriched_data.get("variants", []),
                    enriched_data.get("metabolizer_phenotype")
                ),
                *self.build_variant_nodes(
                    enriched_data.get("variants", [])[:20],  # Limit to 20
                    gene_symbol,
                    enriched_data["protein_id"]
                ),
                self.build_gene_node(
                    enriched_data["protein_id"],
                    gene_symbol,
                    enriched_data.get("hgnc", {})
                )
            ]
        }
        
        # Save
        output_file = self.output_dir / f"{gene_symbol}_knowledge_graph.jsonld"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(jsonld, f, indent=2)
        
        print(f"   JSON-LD saved: {output_file}")
        return str(output_file)
    
    def run_pipeline(self, gene_symbol: str, phase3_file: str = None, 
                     patient_file: str = None) -> str:
        """Execute JSON-LD export"""
        print(f"Exporting JSON-LD...")
        
        # Load data
        if not phase3_file:
            phase3_file = f"data/phase3/{gene_symbol}_enriched.json"
        
        with open(phase3_file, 'r', encoding='utf-8') as f:
            enriched_data = json.load(f)
        
        if not patient_file:
            patient_file = f"data/phase1/{gene_symbol}_virtual_patient.json"
        
        with open(patient_file, 'r', encoding='utf-8') as f:
            patient_data = json.load(f)
        
        return self.export(enriched_data, patient_data, gene_symbol)

