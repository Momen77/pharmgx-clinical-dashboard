"""
RDF Graph Builder
Converts enriched JSON into RDF Turtle format
"""
import json
from pathlib import Path
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD
from datetime import datetime
from typing import Dict, List
import sys
sys.path.append(str(Path(__file__).parent.parent))


class RDFGraphBuilder:
    """Builds RDF knowledge graphs from enriched data"""
    
    def __init__(self):
        """Initialize RDF graph builder"""
        self.graph = Graph()
        self._bind_namespaces()
        self.output_dir = Path("output/rdf")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _bind_namespaces(self):
        """Bind standard namespaces"""
        # Standard ontologies
        self.graph.bind("foaf", Namespace("http://xmlns.com/foaf/0.1/"))
        self.graph.bind("schema", Namespace("http://schema.org/"))
        self.graph.bind("sio", Namespace("http://semanticscience.org/resource/"))
        self.graph.bind("obo", Namespace("http://purl.obolibrary.org/obo/"))
        self.graph.bind("dcterms", Namespace("http://purl.org/dc/terms/"))
        
        # Identifier systems
        self.graph.bind("dbsnp", Namespace("https://identifiers.org/dbsnp:"))
        self.graph.bind("uniprot", Namespace("https://identifiers.org/uniprot:"))
        self.graph.bind("rxnorm", Namespace("https://identifiers.org/rxnorm:"))
        self.graph.bind("snomed", Namespace("http://snomed.info/id/"))
        self.graph.bind("clinvar", Namespace("https://identifiers.org/clinvar:"))
        self.graph.bind("ncbigene", Namespace("https://identifiers.org/ncbigene:"))
        self.graph.bind("pharmgkb", Namespace("https://www.pharmgkb.org/"))
        self.graph.bind("pubmed", Namespace("https://pubmed.ncbi.nlm.nih.gov/"))
        self.graph.bind("chembl", Namespace("https://www.ebi.ac.uk/chembl/compound_report_card/"))
        
        # Project namespaces
        self.graph.bind("pgx", Namespace("http://pgx-kg.org/"))
        self.graph.bind("patient", Namespace("http://pgx-kg.org/patient/"))
        self.graph.bind("genotype", Namespace("http://pgx-kg.org/genotype/"))
        
        # Store as instance variables for easy access
        self.FOAF = Namespace("http://xmlns.com/foaf/0.1/")
        self.SCHEMA = Namespace("http://schema.org/")
        self.SIO = Namespace("http://semanticscience.org/resource/")
        self.OBO = Namespace("http://purl.obolibrary.org/obo/")
        self.DCTERMS = Namespace("http://purl.org/dc/terms/")
        self.DBSNP = Namespace("https://identifiers.org/dbsnp:")
        self.UNIPROT = Namespace("https://identifiers.org/uniprot:")
        self.RXNORM = Namespace("https://identifiers.org/rxnorm:")
        self.SNOMED = Namespace("http://snomed.info/id/")
        self.CLINVAR = Namespace("https://identifiers.org/clinvar:")
        self.PUBMED = Namespace("https://pubmed.ncbi.nlm.nih.gov/")
        self.CHEMBL = Namespace("https://www.ebi.ac.uk/chembl/compound_report_card/")
        self.PATIENT_NS = Namespace("http://pgx-kg.org/patient/")
        self.GENOTYPE_NS = Namespace("http://pgx-kg.org/genotype/")
    
    def add_virtual_patient(self, patient_data: Dict, genotype_uri: URIRef) -> URIRef:
        """Add virtual patient to graph"""
        patient_uri = URIRef(patient_data["@id"])
        
        self.graph.add((patient_uri, RDF.type, self.FOAF.Person))
        self.graph.add((patient_uri, RDF.type, self.SCHEMA.Patient))
        
        # Handle both old and new patient data formats
        identifier = patient_data.get("identifier") or patient_data.get("foaf:identifier") or patient_data.get("schema:identifier")
        name = patient_data.get("name") or patient_data.get("foaf:name") or patient_data.get("schema:name")
        description = patient_data.get("description") or patient_data.get("schema:description")
        date_created = patient_data.get("dateCreated") or patient_data.get("schema:dateCreated", {}).get("@value")
        
        if identifier:
            self.graph.add((patient_uri, self.SCHEMA.identifier, Literal(identifier)))
        if name:
            self.graph.add((patient_uri, self.SCHEMA.name, Literal(name)))
        if description:
            self.graph.add((patient_uri, self.SCHEMA.description, Literal(description)))
        if date_created:
            self.graph.add((patient_uri, self.SCHEMA.dateCreated, Literal(date_created, datatype=XSD.dateTime)))
        
        # Link to genotype
        self.graph.add((patient_uri, self.SIO["SIO_000228"], genotype_uri))  # has role
        
        return patient_uri
    
    def add_genotype(self, gene_symbol: str, variant_uris: List[URIRef]) -> URIRef:
        """Add genotype profile to graph"""
        genotype_id = f"geno_{gene_symbol.lower()}_001"
        genotype_uri = self.GENOTYPE_NS[genotype_id]
        
        self.graph.add((genotype_uri, RDF.type, self.OBO["GENO_0000536"]))  # genotype
        self.graph.add((genotype_uri, RDFS.label, Literal(f"Pharmacogenomics Genotype Profile for {gene_symbol}")))
        self.graph.add((genotype_uri, self.DCTERMS.created, Literal(datetime.now().date().isoformat(), datatype=XSD.date)))
        
        # Link to variants
        for variant_uri in variant_uris:
            self.graph.add((genotype_uri, self.SIO["SIO_000008"], variant_uri))  # has attribute
        
        return genotype_uri
    
    def add_chembl_drug_data(self, drug_uri: URIRef, chembl_data: Dict, drug_name: str):
        """Add ChEMBL bioactivity and target data to drug node"""
        compound_info = chembl_data.get("compound_info", {})
        
        # Add compound properties
        self.graph.add((drug_uri, RDF.type, self.SCHEMA.Drug))
        self.graph.add((drug_uri, self.SCHEMA.name, Literal(drug_name)))
        
        if compound_info.get("pref_name"):
            self.graph.add((drug_uri, self.SCHEMA.alternateName, Literal(compound_info["pref_name"])))
        
        if compound_info.get("molecule_type"):
            self.graph.add((drug_uri, self.SIO["SIO_000300"], Literal(compound_info["molecule_type"])))  # has value
        
        if compound_info.get("max_phase"):
            phase_desc = f"Clinical development phase: {compound_info['max_phase']}"
            self.graph.add((drug_uri, self.SCHEMA.description, Literal(phase_desc)))
        
        if compound_info.get("molecular_weight"):
            mw_literal = Literal(compound_info["molecular_weight"], datatype=XSD.decimal)
            self.graph.add((drug_uri, self.SIO["SIO_001117"], mw_literal))  # has molecular weight
        
        # Add pharmacogenomic bioactivities
        for bioactivity in chembl_data.get("pgx_bioactivities", []):
            if bioactivity.get("target_name") and bioactivity.get("bioactivity_type"):
                # Create bioactivity node
                bioactivity_id = f"bioactivity_{chembl_data['chembl_id']}_{bioactivity.get('target_chembl_id', 'unknown')}"
                bioactivity_uri = URIRef(f"http://pgx-kg.org/bioactivity/{bioactivity_id}")
                
                self.graph.add((drug_uri, self.SIO["SIO_000008"], bioactivity_uri))  # has attribute
                self.graph.add((bioactivity_uri, RDF.type, self.SIO["SIO_001007"]))  # bioassay
                self.graph.add((bioactivity_uri, RDFS.label, Literal(f"{bioactivity['bioactivity_type']} against {bioactivity['target_name']}")))
                
                if bioactivity.get("value") and bioactivity.get("units"):
                    value_desc = f"{bioactivity['value']} {bioactivity['units']}"
                    if bioactivity.get("relation"):
                        value_desc = f"{bioactivity['relation']} {value_desc}"
                    self.graph.add((bioactivity_uri, self.SIO["SIO_000300"], Literal(value_desc)))
                
                if bioactivity.get("assay_description"):
                    self.graph.add((bioactivity_uri, self.SCHEMA.description, Literal(bioactivity["assay_description"])))
        
        # Add mechanism of action
        for mechanism in chembl_data.get("mechanism_of_action", []):
            if mechanism.get("mechanism_of_action"):
                moa_id = f"moa_{chembl_data['chembl_id']}_{hash(mechanism['mechanism_of_action']) % 10000}"
                moa_uri = URIRef(f"http://pgx-kg.org/mechanism/{moa_id}")
                
                self.graph.add((drug_uri, self.SIO["SIO_000017"], moa_uri))  # has part (mechanism)
                self.graph.add((moa_uri, RDF.type, self.SIO["SIO_000006"]))  # process
                self.graph.add((moa_uri, RDFS.label, Literal(mechanism["mechanism_of_action"])))
                
                if mechanism.get("target_name"):
                    self.graph.add((moa_uri, self.SCHEMA.description, Literal(f"Target: {mechanism['target_name']}")))
                
                if mechanism.get("action_type"):
                    self.graph.add((moa_uri, self.SIO["SIO_000300"], Literal(mechanism["action_type"])))
    
    def add_variant(self, variant: Dict, gene_uri: URIRef) -> URIRef:
        """Add variant to graph"""
        # Get rsID
        rsid = None
        for xref in variant.get("xrefs", []):
            if xref.get("name") == "dbSNP":
                rsid = xref.get("id", "").replace("rs", "")
                break
        
        if not rsid:
            return None
        
        variant_uri = self.DBSNP[rsid]
        
        # Basic variant info
        self.graph.add((variant_uri, RDF.type, self.OBO["SO_0001583"]))  # SNV
        self.graph.add((variant_uri, self.SCHEMA.identifier, Literal(f"rs{rsid}")))
        
        # Link to gene
        self.graph.add((variant_uri, self.OBO["GENO_0000408"], gene_uri))  # has reference sequence
        
        # Add protein change
        for loc in variant.get("locations", []):
            if "loc" in loc and loc["loc"].startswith("p."):
                self.graph.add((variant_uri, self.SIO["SIO_000974"], Literal(loc["loc"])))
        
        # Add clinical significance
        for clin_sig in variant.get("clinicalSignificances", []):
            self.graph.add((variant_uri, self.SIO["SIO_000614"], Literal(clin_sig["type"])))
        
        # Add ClinVar data
        if "clinvar" in variant:
            clinvar_id = variant["clinvar"].get("clinvar_id")
            if clinvar_id:
                clinvar_uri = self.CLINVAR[clinvar_id]
                self.graph.add((variant_uri, RDFS.seeAlso, clinvar_uri))
        
        # Add drugs with ChEMBL and RxNorm data
        if "pharmgkb" in variant and "drugs" in variant["pharmgkb"]:
            for drug in variant["pharmgkb"]["drugs"]:
                drug_uri = None
                
                # Prefer ChEMBL URI if available
                if "chembl_data" in drug and drug["chembl_data"].get("chembl_id"):
                    chembl_id = drug["chembl_data"]["chembl_id"]
                    drug_uri = self.CHEMBL[chembl_id]
                    self.graph.add((variant_uri, self.SIO["SIO_000253"], drug_uri))  # has source (affects drug)
                    
                    # Add ChEMBL drug details
                    self.add_chembl_drug_data(drug_uri, drug["chembl_data"], drug["name"])
                
                # Also add RxNorm if available
                elif "rxnorm" in drug:
                    rxnorm_cui = drug["rxnorm"]["rxnorm_cui"]
                    drug_uri = self.RXNORM[rxnorm_cui]
                    self.graph.add((variant_uri, self.SIO["SIO_000253"], drug_uri))  # has source (affects drug)
                
                # Add basic drug details
                if drug_uri:
                    self.graph.add((drug_uri, RDFS.label, Literal(drug["name"])))
                    if drug.get("recommendation"):
                        self.graph.add((drug_uri, self.SCHEMA.description, Literal(drug["recommendation"])))
        
        # Add phenotypes with SNOMED CT Clinical Findings
        if "phenotypes_snomed" in variant:
            for phenotype in variant["phenotypes_snomed"]:
                # Handle both old and new data structures
                finding = phenotype.get("snomed_clinical_finding") or phenotype.get("snomed")
                phenotype_text = phenotype.get("phenotype_text") or phenotype.get("text", "")
                
                if finding and finding.get("code"):
                    finding_uri = self.SNOMED[finding["code"]]
                    self.graph.add((variant_uri, self.SIO["SIO_000668"], finding_uri))  # has clinical finding
                    self.graph.add((finding_uri, RDFS.label, Literal(finding["label"])))
                    # Add the original phenotype text as description
                    if phenotype_text:
                        description = phenotype_text[:200] + "..." if len(phenotype_text) > 200 else phenotype_text
                        self.graph.add((finding_uri, self.SCHEMA.description, Literal(description)))
        
        # Add direct disease associations from ClinVar and PharmGKB
        if "disease_associations" in variant:
            for disease_assoc in variant["disease_associations"]:
                if disease_assoc.get("snomed_mapping") and disease_assoc["snomed_mapping"].get("code"):
                    disease_uri = self.SNOMED[disease_assoc["snomed_mapping"]["code"]]
                    self.graph.add((variant_uri, self.SIO["SIO_000001"], disease_uri))  # is associated with disease
                    self.graph.add((disease_uri, RDFS.label, Literal(disease_assoc["snomed_mapping"]["label"])))
                    
                    # Add source information
                    source_desc = f"Source: {disease_assoc['source']}"
                    if disease_assoc.get("original_phenotype"):
                        source_desc += f" | Context: {disease_assoc['original_phenotype']}"
                    self.graph.add((disease_uri, self.SCHEMA.description, Literal(source_desc)))
                else:
                    # Even without SNOMED mapping, add the disease name
                    disease_name = disease_assoc.get("disease_name", "")
                    if disease_name:
                        # Create a local URI for unmapped diseases
                        disease_uri = URIRef(f"http://pgx-kg.org/disease/{disease_name.replace(' ', '_').lower()}")
                        self.graph.add((variant_uri, self.SIO["SIO_000001"], disease_uri))
                        self.graph.add((disease_uri, RDFS.label, Literal(disease_name)))
                        self.graph.add((disease_uri, self.SCHEMA.description, Literal(f"Source: {disease_assoc['source']} (unmapped)")))
        
        # Add comprehensive disease mappings
        if "phenotypes_comprehensive" in variant:
            for comprehensive in variant["phenotypes_comprehensive"]:
                # Add PharmGKB-specific diseases (prioritized)
                for disease_mapping in comprehensive.get("pharmgkb_diseases", []):
                    if disease_mapping.get("snomed_mapping") and disease_mapping["snomed_mapping"].get("code"):
                        disease_uri = self.SNOMED[disease_mapping["snomed_mapping"]["code"]]
                        self.graph.add((variant_uri, self.SIO["SIO_000001"], disease_uri))  # is associated with disease
                        self.graph.add((disease_uri, RDFS.label, Literal(disease_mapping["snomed_mapping"]["label"])))
                        self.graph.add((disease_uri, self.SCHEMA.description, Literal(f"PharmGKB extracted: {disease_mapping['extracted_text']}")))
                
                # Add general extracted diseases
                for disease_mapping in comprehensive.get("extracted_diseases", []):
                    if disease_mapping.get("snomed_mapping") and disease_mapping["snomed_mapping"].get("code"):
                        disease_uri = self.SNOMED[disease_mapping["snomed_mapping"]["code"]]
                        self.graph.add((variant_uri, self.SIO["SIO_000001"], disease_uri))  # is associated with disease
                        self.graph.add((disease_uri, RDFS.label, Literal(disease_mapping["snomed_mapping"]["label"])))
                        self.graph.add((disease_uri, self.SCHEMA.description, Literal(f"General extraction: {disease_mapping['extracted_text']}")))
                
                # Add disease hierarchy from clinical findings
                hierarchy = comprehensive.get("snomed_disease_hierarchy")
                if hierarchy:
                    for disease_ancestor in hierarchy.get("disease_ancestors", []):
                        disease_uri = self.SNOMED[disease_ancestor["code"]]
                        self.graph.add((variant_uri, self.SIO["SIO_000001"], disease_uri))  # is associated with disease
                        self.graph.add((disease_uri, RDFS.label, Literal(disease_ancestor["label"])))
                        self.graph.add((disease_uri, self.SCHEMA.description, Literal(f"Disease hierarchy from clinical finding: {hierarchy['clinical_finding_code']}")))
        
        # Add literature evidence
        if "literature" in variant:
            for pub in variant["literature"].get("gene_publications", [])[:3]:  # Top 3
                if pub.get("pmid"):
                    pub_uri = self.PUBMED[pub["pmid"]]
                    self.graph.add((variant_uri, self.SIO["SIO_000772"], pub_uri))  # has evidence
                    self.graph.add((pub_uri, self.DCTERMS.title, Literal(pub.get("title", ""))))
        
        return variant_uri
    
    def add_gene(self, protein_id: str, gene_symbol: str, gene_info: Dict = None) -> URIRef:
        """Add gene to graph"""
        gene_uri = self.UNIPROT[protein_id]
        
        self.graph.add((gene_uri, RDF.type, self.OBO["SO_0000704"]))  # gene
        self.graph.add((gene_uri, RDFS.label, Literal(gene_symbol)))
        self.graph.add((gene_uri, self.SCHEMA.identifier, Literal(protein_id)))
        self.graph.add((gene_uri, self.SCHEMA.name, Literal(gene_symbol)))
        
        if gene_info:
            if "gene_name" in gene_info:
                self.graph.add((gene_uri, self.SCHEMA.alternateName, Literal(gene_info["gene_name"])))
            if "ncbi_gene_id" in gene_info:
                ncbi_uri = URIRef(f"https://identifiers.org/ncbigene:{gene_info['ncbi_gene_id']}")
                self.graph.add((gene_uri, RDFS.seeAlso, ncbi_uri))
        
        return gene_uri
    
    def build_from_enriched_data(self, enriched_data: Dict, patient_data: Dict) -> Graph:
        """Build complete RDF graph from enriched data"""
        gene_symbol = enriched_data["gene_symbol"]
        protein_id = enriched_data["protein_id"]
        
        # Add gene
        gene_info = enriched_data.get("hgnc", {})
        gene_uri = self.add_gene(protein_id, gene_symbol, gene_info)
        
        # Add variants
        variant_uris = []
        for variant in enriched_data.get("variants", [])[:20]:  # Limit to 20
            variant_uri = self.add_variant(variant, gene_uri)
            if variant_uri:
                variant_uris.append(variant_uri)
        
        # Add genotype
        genotype_uri = self.add_genotype(gene_symbol, variant_uris)
        
        # Add patient
        patient_uri = self.add_virtual_patient(patient_data, genotype_uri)
        
        return self.graph
    
    def save(self, gene_symbol: str, format: str = "turtle"):
        """Save graph to file"""
        output_file = self.output_dir / f"{gene_symbol}_knowledge_graph.ttl"
        self.graph.serialize(destination=str(output_file), format=format, encoding="utf-8")
        print(f"   RDF graph saved: {output_file}")
        return output_file
    
    def run_pipeline(self, gene_symbol: str, phase3_file: str = None, 
                     patient_file: str = None) -> str:
        """Execute Phase 4: RDF graph building"""
        print(f"\n{'='*60}")
        print(f"Phase 4: RDF Knowledge Graph Assembly for {gene_symbol}")
        print(f"{'='*60}\n")
        
        # Load Phase 3 data
        if not phase3_file:
            phase3_file = f"data/phase3/{gene_symbol}_enriched.json"
        
        with open(phase3_file, 'r', encoding='utf-8') as f:
            enriched_data = json.load(f)
        
        # Load patient data
        if not patient_file:
            patient_file = f"data/phase1/{gene_symbol}_virtual_patient.json"
        
        with open(patient_file, 'r', encoding='utf-8') as f:
            patient_data = json.load(f)
        
        print(f"Loaded enriched data with {enriched_data['total_variants']} variants")
        
        # Build graph
        print("Building RDF graph...")
        self.build_from_enriched_data(enriched_data, patient_data)
        
        # Save
        output_file = self.save(gene_symbol)
        
        print(f"\nPhase 4 Complete!")
        print(f"   Total triples: {len(self.graph)}")
        
        return str(output_file)


if __name__ == "__main__":
    builder = RDFGraphBuilder()
    output = builder.run_pipeline("CYP2D6")
    print(f"\n   Output: {output}")

