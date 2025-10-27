"""
PGx-KG Main Pipeline
Orchestrates all 5 phases to build pharmacogenomics knowledge graphs
"""
import argparse
import sys
import json
import random
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.append(str(Path(__file__).parent))

from utils.config import Config
from utils.dynamic_clinical_generator import DynamicClinicalGenerator
from utils.variant_phenotype_linker import VariantPhenotypeLinker
from phase1_discovery.variant_discoverer import VariantDiscoverer
from phase2_clinical.clinical_validator import ClinicalValidator
from phase3_context.drug_disease_linker import DrugDiseaseLinker
from phase4_rdf.graph_builder import RDFGraphBuilder
from phase5_export.json_exporter import JSONLDExporter
from phase5_export.html_reporter import HTMLReporter


class PGxKGPipeline:
    """Main pipeline orchestrator"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize pipeline
        
        Args:
            config_path: Path to configuration file
        """
        self.config = Config(config_path)
        
        # Initialize phase modules
        self.phase1 = VariantDiscoverer()
        self.phase2 = ClinicalValidator(
            ncbi_email=self.config.ncbi_email,
            ncbi_api_key=self.config.ncbi_api_key,
            bioportal_api_key=self.config.bioportal_api_key
        )
        self.phase3 = DrugDiseaseLinker(
            bioportal_api_key=self.config.bioportal_api_key
        )
        self.phase4 = RDFGraphBuilder()
        self.phase5_jsonld = JSONLDExporter()
        self.phase5_html = HTMLReporter()
        
        # Dynamic clinical data generator
        self.dynamic_clinical = DynamicClinicalGenerator(
            bioportal_api_key=self.config.bioportal_api_key
        )
        
        # Variant-phenotype-drug linker with conflict detection
        self.variant_linker = VariantPhenotypeLinker(
            bioportal_api_key=self.config.bioportal_api_key
        )
    
    def run(self, gene_symbol: str, protein_id: str = None):
        """
        Run complete pipeline for a gene
        
        Args:
            gene_symbol: Gene symbol (e.g., CYP2D6)
            protein_id: Optional UniProt ID (will be fetched if not provided)
        """
        start_time = datetime.now()
        
        print(f"\n{'='*70}")
        print(f"PGx-KG: Pharmacogenomics Knowledge Graph Builder")
        print(f"{'='*70}")
        print(f"Gene: {gene_symbol}")
        print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}\n")
        
        try:
            # Phase 1: Variant Discovery
            print("PHASE 1: Variant Discovery")
            print("-" * 70)
            phase1_result = self.phase1.run_pipeline(gene_symbol, protein_id)
            protein_id = phase1_result["protein_id"]
            
            # Phase 2: Clinical Validation
            print(f"\n{'='*70}")
            print("PHASE 2: Clinical Validation")
            print("-" * 70)
            self.phase2.run_pipeline(gene_symbol)
            
            # Phase 3: Drug & Disease Context
            print(f"\n{'='*70}")
            print("PHASE 3: Drug & Disease Context")
            print("-" * 70)
            self.phase3.run_pipeline(gene_symbol)
            
            # Phase 4: RDF Graph Assembly
            print(f"\n{'='*70}")
            print("PHASE 4: RDF Knowledge Graph Assembly")
            print("-" * 70)
            rdf_output = self.phase4.run_pipeline(gene_symbol)
            
            # Phase 5: Export & Visualization
            print(f"\n{'='*70}")
            print("PHASE 5: Export & Visualization")
            print("-" * 70)
            jsonld_output = self.phase5_jsonld.run_pipeline(gene_symbol)
            html_output = self.phase5_html.run_pipeline(gene_symbol)
            
            # Summary
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            print(f"\n{'='*70}")
            print("PIPELINE COMPLETE!")
            print(f"{'='*70}")
            print(f"\nGene: {gene_symbol}")
            print(f"Protein ID: {protein_id}")
            print(f"Duration: {duration:.1f} seconds")
            print(f"\nOutputs:")
            print(f"  RDF Turtle:  {rdf_output}")
            print(f"  JSON-LD:     {jsonld_output}")
            print(f"  HTML Report: {html_output}")
            print(f"\nVariants processed: {phase1_result['total_variants']}")
            print(f"{'='*70}\n")
            
            return {
                "success": True,
                "gene": gene_symbol,
                "protein_id": protein_id,
                "duration": duration,
                "outputs": {
                    "rdf": rdf_output,
                    "jsonld": jsonld_output,
                    "html": html_output
                }
            }
            
        except Exception as e:
            print(f"\n{'='*70}")
            print(f"PIPELINE FAILED")
            print(f"{'='*70}")
            print(f"Error: {str(e)}")
            print(f"{'='*70}\n")
            
            import traceback
            traceback.print_exc()
            
            return {
                "success": False,
                "gene": gene_symbol,
                "error": str(e)
            }
    
    def run_multi_gene(self, gene_symbols: list) -> dict:
        """
        Run pipeline for multiple genes to create comprehensive patient profile
        
        Args:
            gene_symbols: List of gene symbols (e.g., ['CYP2D6', 'CYP2C19', 'CYP3A4'])
            
        Returns:
            Dictionary with results for all genes
        """
        start_time = datetime.now()
        
        print(f"\n{'='*70}")
        print(f"PGx-KG: Multi-Gene Pharmacogenomics Knowledge Graph Builder")
        print(f"{'='*70}")
        print(f"Genes: {', '.join(gene_symbols)}")
        print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}\n")
        
        results = {}
        all_variants = []
        all_drugs = set()
        all_diseases = set()
        patient_id = f"comprehensive_patient_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            # Process each gene individually
            for i, gene_symbol in enumerate(gene_symbols, 1):
                print(f"\n{'='*70}")
                print(f"PROCESSING GENE {i}/{len(gene_symbols)}: {gene_symbol}")
                print(f"{'='*70}")
                
                # Run single-gene pipeline
                gene_result = self.run(gene_symbol)
                results[gene_symbol] = gene_result
                
                if gene_result["success"]:
                    # Collect variants from this gene
                    gene_variants = self._extract_gene_variants(gene_symbol)
                    all_variants.extend(gene_variants)
                    
                    # Collect drugs and diseases
                    gene_drugs, gene_diseases = self._extract_drugs_diseases(gene_symbol)
                    all_drugs.update(gene_drugs)
                    all_diseases.update(gene_diseases)
                else:
                    print(f"WARNING: Failed to process {gene_symbol}: {gene_result.get('error', 'Unknown error')}")
            
            # Create comprehensive patient profile
            print(f"\n{'='*70}")
            print("CREATING COMPREHENSIVE PATIENT PROFILE")
            print(f"{'='*70}")
            
            comprehensive_profile = self._create_comprehensive_profile(
                patient_id, gene_symbols, all_variants, all_drugs, all_diseases
            )
            
            # Link patient profile to variants and detect conflicts
            print(f"\n{'='*70}")
            print("LINKING PATIENT PROFILE TO VARIANTS")
            print(f"{'='*70}")
            linking_results = self.variant_linker.link_patient_profile_to_variants(
                patient_profile=comprehensive_profile,
                variants=all_variants
            )
            
            # Add linking results to comprehensive profile
            comprehensive_profile["variant_linking"] = linking_results
            
            # Generate comprehensive outputs
            comprehensive_outputs = self._generate_comprehensive_outputs(
                patient_id, comprehensive_profile, results
            )
            
            # Summary
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            print(f"\n{'='*70}")
            print("MULTI-GENE PIPELINE COMPLETE!")
            print(f"{'='*70}")
            print(f"\nGenes processed: {len(gene_symbols)}")
            print(f"Total variants: {len(all_variants)}")
            print(f"Affected drugs: {len(all_drugs)}")
            print(f"Associated diseases: {len(all_diseases)}")
            
            # Display conflict summary if available
            if "variant_linking" in comprehensive_profile:
                linking_summary = comprehensive_profile["variant_linking"].get("summary", {})
                conflicts_summary = linking_summary.get("conflicts", {})
                print(f"\n{'='*70}")
                print("VARIANT LINKING & CONFLICT ANALYSIS")
                print(f"{'='*70}")
                print(f"Total conflicts detected: {conflicts_summary.get('total', 0)}")
                print(f"  ⚠️  Critical: {conflicts_summary.get('critical', 0)}")
                print(f"  ⚠️  Warnings: {conflicts_summary.get('warnings', 0)}")
                print(f"  ℹ️  Info: {conflicts_summary.get('info', 0)}")
                
                links_summary = linking_summary.get("total_links", {})
                print(f"\nLinks created:")
                print(f"  💊 Medication-to-Variant: {links_summary.get('medication_to_variant', 0)}")
                print(f"  🏥 Condition-to-Disease: {links_summary.get('condition_to_disease', 0)}")
                print(f"  🧬 Variant-to-Phenotype: {links_summary.get('variant_to_phenotype', 0)}")
                print(f"  💉 Drug-to-Variant: {links_summary.get('drug_to_variant', 0)}")
            
            print(f"\nDuration: {duration:.1f} seconds")
            print(f"\nComprehensive outputs:")
            for output_type, path in comprehensive_outputs.items():
                print(f"  {output_type}: {path}")
            print(f"{'='*70}\n")
            
            return {
                "success": True,
                "patient_id": patient_id,
                "genes": gene_symbols,
                "total_variants": len(all_variants),
                "affected_drugs": len(all_drugs),
                "associated_diseases": len(all_diseases),
                "duration": duration,
                "gene_results": results,
                "comprehensive_outputs": comprehensive_outputs
            }
            
        except Exception as e:
            print(f"\n{'='*70}")
            print(f"MULTI-GENE PIPELINE FAILED")
            print(f"{'='*70}")
            print(f"Error: {str(e)}")
            print(f"{'='*70}\n")
            
            import traceback
            traceback.print_exc()
            
            return {
                "success": False,
                "genes": gene_symbols,
                "error": str(e),
                "partial_results": results
            }
    
    def _extract_gene_variants(self, gene_symbol: str) -> list:
        """Extract variants from a processed gene"""
        try:
            # Load Phase 2 data (enriched variants)
            phase2_file = f"data/phase2/{gene_symbol}_clinical.json"
            with open(phase2_file, 'r', encoding='utf-8') as f:
                phase2_data = json.load(f)
            
            # Load Phase 3 data (enriched with literature)
            phase3_file = f"data/phase3/{gene_symbol}_enriched.json"
            phase3_data = {}
            try:
                with open(phase3_file, 'r', encoding='utf-8') as f:
                    phase3_data = json.load(f)
            except FileNotFoundError:
                print(f"Warning: Phase 3 file not found for {gene_symbol}")
            
            variants = []
            for i, variant in enumerate(phase2_data.get("variants", [])):
                # Get corresponding Phase 3 variant (with literature)
                phase3_variant = {}
                if "variants" in phase3_data and i < len(phase3_data["variants"]):
                    phase3_variant = phase3_data["variants"][i]
                
                variant_info = {
                    "gene": gene_symbol,
                    "protein_id": phase2_data.get("protein_id"),
                    "variant_id": self._extract_variant_id(variant),
                    "rsid": self._extract_rsid(variant),
                    "clinical_significance": self._get_clinical_significance(variant),
                    "drugs": self._extract_variant_drugs(variant),
                    "diseases": self._extract_variant_diseases(variant),
                    "literature": phase3_variant.get("literature", {}),
                    "raw_data": variant
                }
                variants.append(variant_info)
            
            return variants
            
        except Exception as e:
            print(f"Warning: Could not extract variants for {gene_symbol}: {e}")
            return []
    
    def _extract_drugs_diseases(self, gene_symbol: str) -> tuple:
        """Extract unique drugs and diseases from a gene"""
        drugs = set()
        diseases = set()
        
        try:
            # Load Phase 3 data (enriched with drugs/diseases)
            phase3_file = f"data/phase3/{gene_symbol}_enriched.json"
            with open(phase3_file, 'r', encoding='utf-8') as f:
                phase3_data = json.load(f)
            
            for variant in phase3_data.get("variants", []):
                # Extract drugs
                if "pharmgkb" in variant and "drugs" in variant["pharmgkb"]:
                    for drug in variant["pharmgkb"]["drugs"]:
                        drugs.add(drug.get("name", "Unknown"))
                
                # Extract diseases from ClinVar
                if "clinvar" in variant and "phenotypes" in variant["clinvar"]:
                    for phenotype in variant["clinvar"]["phenotypes"]:
                        diseases.add(phenotype)
            
            # Also extract gene-level phenotypes (often more comprehensive)
            gene_phenotypes = phase3_data.get("gene_level_phenotypes", [])
            for phenotype in gene_phenotypes:
                # Extract disease/condition names from phenotype descriptions
                # Look for key disease terms
                phenotype_lower = phenotype.lower()
                if any(term in phenotype_lower for term in ["disease", "disorder", "syndrome", "cancer", "toxicity", "deficiency"]):
                    # Extract the key disease term (simplified)
                    if "toxicity" in phenotype_lower:
                        diseases.add("Drug toxicity")
                    elif "deficiency" in phenotype_lower:
                        diseases.add("Enzyme deficiency")
                    elif "cancer" in phenotype_lower:
                        diseases.add("Cancer")
                    else:
                        # Add the phenotype as a potential disease
                        diseases.add(phenotype[:100])  # Truncate long descriptions
                
        except Exception as e:
            print(f"Warning: Could not extract drugs/diseases for {gene_symbol}: {e}")
        
        return drugs, diseases
    
    def _extract_variant_id(self, variant: dict) -> str:
        """Extract the best available variant identifier"""
        # Try different identifier sources in order of preference
        
        # 1. Try ftId (if available)
        if variant.get("ftId"):
            return variant["ftId"]
        
        # 2. Try dbSNP rsID
        for xref in variant.get("xrefs", []):
            if xref.get("name") == "dbSNP" and xref.get("id"):
                return xref["id"]
        
        # 3. Try ClinVar ID
        for xref in variant.get("xrefs", []):
            if xref.get("name") == "ClinVar" and xref.get("id"):
                return xref["id"]
        
        # 4. Try genomic location
        genomic_locations = variant.get("genomicLocation", [])
        if genomic_locations:
            return genomic_locations[0]
        
        # 5. Try protein change
        locations = variant.get("locations", [])
        for loc in locations:
            if loc.get("loc") and loc["loc"].startswith("p."):
                return loc["loc"]
        
        # 6. Fallback to position-based ID
        begin = variant.get("begin")
        end = variant.get("end")
        alt_seq = variant.get("alternativeSequence")
        if begin and alt_seq:
            return f"pos_{begin}_{alt_seq}"
        
        return "Unknown"
    
    def _extract_rsid(self, variant: dict) -> str:
        """Extract rsID from variant"""
        for xref in variant.get("xrefs", []):
            if xref.get("name") == "dbSNP":
                return xref.get("id", "").replace("rs", "")
        return None
    
    def _get_clinical_significance(self, variant: dict) -> str:
        """Get clinical significance from variant"""
        clin_sigs = [sig["type"] for sig in variant.get("clinicalSignificances", [])]
        return clin_sigs[0] if clin_sigs else "Unknown"
    
    def _extract_variant_drugs(self, variant: dict) -> list:
        """Extract drugs affected by variant with SNOMED CT codes"""
        drugs = []
        if "pharmgkb" in variant and "drugs" in variant["pharmgkb"]:
            for drug in variant["pharmgkb"]["drugs"]:
                drug_name = drug.get("name")
                drug_info = {
                    "name": drug_name,
                    "recommendation": drug.get("recommendation", "")[:100] + "..." if len(drug.get("recommendation", "")) > 100 else drug.get("recommendation", ""),
                    "evidence_level": drug.get("evidence_level", "")
                }
                
                # Add SNOMED CT code if available from linker
                if self.variant_linker and drug_name:
                    snomed_data = self.variant_linker._search_drug_snomed(drug_name)
                    if snomed_data:
                        drug_info["snomed:code"] = snomed_data.get("code")
                        drug_info["snomed:uri"] = f"http://snomed.info/id/{snomed_data.get('code')}"
                
                drugs.append(drug_info)
        return drugs
    
    def _extract_variant_diseases(self, variant: dict) -> list:
        """Extract diseases associated with variant"""
        diseases = []
        
        # Extract from ClinVar
        if "clinvar" in variant and "phenotypes" in variant["clinvar"]:
            for phenotype in variant["clinvar"]["phenotypes"]:
                disease_info = {"name": phenotype, "source": "ClinVar"}
                
                # Add SNOMED CT code if available
                if self.variant_linker:
                    snomed_data = self.variant_linker._search_snomed(phenotype)
                    if snomed_data:
                        disease_info["snomed:code"] = snomed_data.get("code")
                        disease_info["snomed:uri"] = f"http://snomed.info/id/{snomed_data.get('code')}"
                
                diseases.append(disease_info)
        
        # Extract from PharmGKB phenotypes (often more informative)
        if "pharmgkb" in variant and "phenotypes" in variant["pharmgkb"]:
            for phenotype in variant["pharmgkb"]["phenotypes"]:
                # Extract disease-related terms from phenotype descriptions
                phenotype_lower = phenotype.lower()
                if any(term in phenotype_lower for term in ["disease", "disorder", "syndrome", "toxicity", "adverse"]):
                    disease_info = {
                        "name": phenotype[:80],  # Truncate for readability
                        "source": "PharmGKB"
                    }
                    
                    # Add SNOMED CT code if available
                    if self.variant_linker:
                        snomed_data = self.variant_linker._search_snomed(phenotype)
                        if snomed_data:
                            disease_info["snomed:code"] = snomed_data.get("code")
                            disease_info["snomed:uri"] = f"http://snomed.info/id/{snomed_data.get('code')}"
                    
                    diseases.append(disease_info)
        
        return diseases
    
    def _create_comprehensive_profile(self, patient_id: str, genes: list, variants: list, drugs: set, diseases: set) -> dict:
        """Create comprehensive patient profile with enhanced clinical information"""
        # Generate clinical information
        clinical_info = self._generate_clinical_information(patient_id)
        
        profile = {
            "@context": {
                "foaf": "http://xmlns.com/foaf/0.1/",
                "schema": "http://schema.org/",
                "pgx": "http://pgx-kg.org/",
                "sdisco": "http://ugent.be/sdisco/",
                "snomed": "http://snomed.info/id/",
                "drugbank": "https://go.drugbank.com/drugs/",
                "ugent": "http://ugent.be/person/",
                "dbsnp": "https://identifiers.org/dbsnp/",
                "ncbigene": "https://identifiers.org/ncbigene/",
                "clinpgx": "https://www.clinpgx.org/haplotype/",
                "gn": "http://www.geonames.org/ontology#",
                "skos": "http://www.w3.org/2004/02/skos/core#",
                "xsd": "http://www.w3.org/2001/XMLSchema#"
            },
            "@id": f"http://ugent.be/person/{patient_id}",
            "@type": ["foaf:Person", "schema:Person", "schema:Patient"],
            "identifier": patient_id,
            "name": f"Comprehensive Pharmacogenomics Patient Profile",
            "description": f"Multi-gene pharmacogenomics profile covering {len(genes)} genes with {len(variants)} variants",
            "dateCreated": datetime.now().isoformat(),
            
            # Enhanced Clinical Information
            "clinical_information": clinical_info,
            
            "pharmacogenomics_profile": {
                "genes_analyzed": genes,
                "total_variants": len(variants),
                "variants_by_gene": {gene: len([v for v in variants if v["gene"] == gene]) for gene in genes},
                "affected_drugs": list(drugs),
                "associated_diseases": list(diseases),
                "clinical_summary": self._generate_clinical_summary(variants),
                "literature_summary": self._generate_literature_summary(variants)
            },
            "variants": variants,
            "dataSource": "EMBL-EBI Proteins API + UniProt + ClinVar + PharmGKB + OpenFDA + Europe PMC"
        }
        
        return profile
    
    def _generate_clinical_information(self, patient_id: str) -> dict:
        """Generate comprehensive clinical information for patient profile using dynamic APIs"""
        # Use patient_id as seed for reproducibility (same patient_id = same clinical data)
        random.seed(hash(patient_id) % (2**32))
        
        # Generate demographics first (needed for age/lifestyle)
        demographics = self._generate_demographics()
        age = demographics.get("age", 50)
        
        # Generate lifestyle factors
        lifestyle_factors = self._generate_lifestyle_factors()
        
        # DYNAMIC: Query SNOMED CT for conditions based on age and lifestyle
        print("\n🔄 Dynamically querying SNOMED CT for conditions...")
        conditions = self.dynamic_clinical.get_conditions_by_age_lifestyle(age, lifestyle_factors)
        
        # Add diagnosis dates and status to conditions
        current_date = datetime.now()
        for condition in conditions:
            years_ago = random.randint(1, 10)
            condition["diagnosis_date"] = (current_date - timedelta(days=years_ago * 365)).strftime("%Y-%m-%d")
            condition["status"] = random.choice(["active", "controlled", "remission"])
        
        # DYNAMIC: Query drug APIs for medications based on conditions
        print(f"🔄 Dynamically querying drug APIs for {len(conditions)} conditions...")
        medications = []
        for condition in conditions:
            snomed_code = condition.get("snomed:code")
            condition_label = condition.get("rdfs:label", "")
            if snomed_code:
                condition_meds = self.dynamic_clinical.get_drugs_for_condition(snomed_code, condition_label)
                medications.extend(condition_meds)
        
        return {
            "demographics": demographics,
            "current_conditions": conditions,
            "current_medications": medications,
            "organ_function": self._generate_organ_function(),
            "lifestyle_factors": lifestyle_factors
        }
    
    def _generate_demographics(self) -> dict:
        """Generate basic demographic information with random but realistic values"""
        # Common first names
        first_names = ["Emma", "James", "Sophia", "William", "Olivia", "Michael", "Isabella", "David", "Jane", "John", "Maria", "Robert"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Doe", "Wilson", "Martinez", "Anderson"]
        
        # Random selection
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        
        # Random age between 25-75
        age = random.randint(25, 75)
        birth_year = datetime.now().year - age
        birth_month = random.randint(1, 12)
        birth_day = random.randint(1, 28)  # Use 28 to avoid month-end issues
        birth_date = f"{birth_year}-{birth_month:02d}-{birth_day:02d}"
        
        # Random gender
        gender = random.choice(["http://schema.org/Male", "http://schema.org/Female"])
        
        # Random weight and height (realistic ranges)
        if gender == "http://schema.org/Female":
            weight_kg = round(random.uniform(50, 90), 1)
            height_cm = round(random.uniform(150, 175), 1)
        else:
            weight_kg = round(random.uniform(60, 100), 1)
            height_cm = round(random.uniform(160, 190), 1)
        
        # Random birthplaces (European cities)
        birthplaces = [
            {"id": "2800866", "name": "Brussels", "alt": "Bruxelles"},
            {"id": "2797656", "name": "Ghent", "alt": "Gent"},
            {"id": "2950159", "name": "Berlin", "alt": "Berlin"},
            {"id": "2988507", "name": "Paris", "alt": "Paris"},
            {"id": "3117735", "name": "Madrid", "alt": "Madrid"},
            {"id": "3169070", "name": "Rome", "alt": "Roma"}
        ]
        birthplace = random.choice(birthplaces)
        
        return {
            "@id": "http://ugent.be/person/demographics",
            "foaf:firstName": first_name,
            "foaf:familyName": last_name,
            "schema:givenName": first_name,
            "schema:familyName": last_name,
            "schema:birthDate": birth_date,
            "schema:birthPlace": {
                "@id": f"https://www.geonames.org/{birthplace['id']}",
                "gn:name": birthplace["name"],
                "gn:alternateName": birthplace["alt"]
            },
            "schema:gender": gender,
            "schema:weight": {
                "@type": "schema:QuantitativeValue",
                "schema:value": weight_kg,
                "schema:unitCode": "kg",
                "schema:unitText": "kilograms"
            },
            "schema:height": {
                "@type": "schema:QuantitativeValue",
                "schema:value": height_cm,
                "schema:unitCode": "cm",
                "schema:unitText": "centimeters"
            },
            "age": age,
            "note": "Randomly generated demographics for virtual patient"
        }
    
    def _generate_current_conditions(self) -> list:
        """Generate current medical conditions using SNOMED CT - randomly selects conditions"""
        # Comprehensive conditions database with SNOMED CT codes
        conditions_db = [
            {
                "@id": "http://snomed.info/id/44054006",
                "@type": "sdisco:Condition",
                "snomed:code": "44054006",
                "rdfs:label": "Diabetes mellitus type 2 (disorder)",
                "skos:prefLabel": "Diabetes mellitus type 2 (disorder)",
                "skos:altLabel": ["Type 2 diabetes mellitus", "Diabetes mellitus type 2"],
                "skos:definition": "A type of diabetes mellitus that is characterized by insulin resistance or desensitization and increased blood glucose levels.",
                "probability": 0.15
            },
            {
                "@id": "http://snomed.info/id/254837009",
                "@type": "sdisco:Condition",
                "snomed:code": "254837009",
                "rdfs:label": "Hypertension (disorder)",
                "skos:prefLabel": "Hypertension (disorder)",
                "skos:altLabel": ["High blood pressure"],
                "skos:definition": "Persistent high arterial blood pressure",
                "probability": 0.25
            },
            {
                "@id": "http://snomed.info/id/372244006",
                "@type": "sdisco:Condition",
                "snomed:code": "372244006",
                "rdfs:label": "Asthma (disorder)",
                "skos:prefLabel": "Asthma (disorder)",
                "skos:altLabel": ["Asthma"],
                "skos:definition": "Chronic inflammatory disease of the airways",
                "probability": 0.12
            },
            {
                "@id": "http://snomed.info/id/38341003",
                "@type": "sdisco:Condition",
                "snomed:code": "38341003",
                "rdfs:label": "Hypertensive disorder (disorder)",
                "skos:prefLabel": "Hypertensive disorder (disorder)",
                "skos:altLabel": ["Hypertension"],
                "skos:definition": "High blood pressure condition",
                "probability": 0.18
            },
            {
                "@id": "http://snomed.info/id/73211009",
                "@type": "sdisco:Condition",
                "snomed:code": "73211009",
                "rdfs:label": "Diabetes mellitus (disorder)",
                "skos:prefLabel": "Diabetes mellitus (disorder)",
                "skos:altLabel": ["Diabetes"],
                "skos:definition": "Chronic metabolic disorder characterized by hyperglycemia",
                "probability": 0.10
            },
            {
                "@id": "http://snomed.info/id/26889001",
                "@type": "sdisco:Condition",
                "snomed:code": "26889001",
                "rdfs:label": "Chronic obstructive pulmonary disease (disorder)",
                "skos:prefLabel": "COPD (disorder)",
                "skos:altLabel": ["COPD", "Chronic obstructive pulmonary disease"],
                "skos:definition": "Chronic progressive lung disease characterized by airflow limitation",
                "probability": 0.08
            },
            {
                "@id": "http://snomed.info/id/10742861000119102",
                "@type": "sdisco:Condition",
                "snomed:code": "10742861000119102",
                "rdfs:label": "Dyslipidemia (disorder)",
                "skos:prefLabel": "Dyslipidemia (disorder)",
                "skos:altLabel": ["High cholesterol", "Hyperlipidemia"],
                "skos:definition": "Abnormal amount of lipids in the blood",
                "probability": 0.20
            },
            {
                "@id": "http://snomed.info/id/49436004",
                "@type": "sdisco:Condition",
                "snomed:code": "49436004",
                "rdfs:label": "Atrial fibrillation (disorder)",
                "skos:prefLabel": "Atrial fibrillation (disorder)",
                "skos:altLabel": ["AFib", "Atrial fibrillation"],
                "skos:definition": "Irregular heart rhythm",
                "probability": 0.08
            },
            {
                "@id": "http://snomed.info/id/363418016",
                "@type": "sdisco:Condition",
                "snomed:code": "363418016",
                "rdfs:label": "Depression (disorder)",
                "skos:prefLabel": "Depression (disorder)",
                "skos:altLabel": ["Major depressive disorder", "MDD"],
                "skos:definition": "Mood disorder characterized by persistent sadness",
                "probability": 0.12
            },
            {
                "@id": "http://snomed.info/id/35489007",
                "@type": "sdisco:Condition",
                "snomed:code": "35489007",
                "rdfs:label": "Chronic kidney disease (disorder)",
                "skos:prefLabel": "Chronic kidney disease (disorder)",
                "skos:altLabel": ["CKD", "Chronic kidney disease"],
                "skos:definition": "Progressive loss of kidney function over time",
                "probability": 0.08
            },
            {
                "@id": "http://snomed.info/id/363478007",
                "@type": "sdisco:Condition",
                "snomed:code": "363478007",
                "rdfs:label": "Anxiety disorder (disorder)",
                "skos:prefLabel": "Anxiety disorder (disorder)",
                "skos:altLabel": ["Anxiety", "Generalized anxiety disorder"],
                "skos:definition": "Mental health disorder characterized by excessive worry",
                "probability": 0.10
            },
            {
                "@id": "http://snomed.info/id/363346000",
                "@type": "sdisco:Condition",
                "snomed:code": "363346000",
                "rdfs:label": "Breast cancer (disorder)",
                "skos:prefLabel": "Breast cancer (disorder)",
                "skos:altLabel": ["Breast cancer", "Carcinoma of breast"],
                "skos:definition": "Malignant neoplasm of breast tissue",
                "probability": 0.05
            },
            {
                "@id": "http://snomed.info/id/266430006",
                "@type": "sdisco:Condition",
                "snomed:code": "266430006",
                "rdfs:label": "Gastroesophageal reflux disease (disorder)",
                "skos:prefLabel": "GERD (disorder)",
                "skos:altLabel": ["GERD", "Gastroesophageal reflux"],
                "skos:definition": "Chronic digestive disease where stomach acid flows back into esophagus",
                "probability": 0.15
            },
            {
                "@id": "http://snomed.info/id/161891005",
                "@type": "sdisco:Condition",
                "snomed:code": "161891005",
                "rdfs:label": "Osteoarthritis (disorder)",
                "skos:prefLabel": "Osteoarthritis (disorder)",
                "skos:altLabel": ["OA", "Osteoarthritis"],
                "skos:definition": "Degenerative joint disease",
                "probability": 0.12
            },
            {
                "@id": "http://snomed.info/id/4855003",
                "@type": "sdisco:Condition",
                "snomed:code": "4855003",
                "rdfs:label": "Hypothyroidism (disorder)",
                "skos:prefLabel": "Hypothyroidism (disorder)",
                "skos:altLabel": ["Underactive thyroid", "Hypothyroidism"],
                "skos:definition": "Underactive thyroid gland",
                "probability": 0.10
            }
        ]
        
        # Select conditions based on probability
        selected_conditions = []
        current_date = datetime.now()
        
        for condition in conditions_db:
            if random.random() < condition.get("probability", 0.0):
                # Generate random diagnosis date (1-10 years ago)
                years_ago = random.randint(1, 10)
                diagnosis_date = (current_date - timedelta(days=years_ago * 365)).strftime("%Y-%m-%d")
                
                condition_copy = condition.copy()
                condition_copy.pop("probability")  # Remove probability from output
                condition_copy["diagnosis_date"] = diagnosis_date
                condition_copy["status"] = random.choice(["active", "controlled", "remission"])
                selected_conditions.append(condition_copy)
        
        return selected_conditions
    
    def _get_condition_drug_mapping(self) -> dict:
        """Returns mapping of SNOMED CT condition codes to their associated medications"""
        return {
            "44054006": [  # Diabetes mellitus type 2
                {"drugbank_id": "DB00619", "name": "Metformin", "doses": [500, 850, 1000], "unit": "mg", "frequency": "Twice daily", "protocol": "First-line treatment for type 2 diabetes"},
                {"drugbank_id": "DB00030", "name": "Insulin glargine", "doses": [10, 20, 30], "unit": "units", "frequency": "Once daily", "protocol": "Long-acting insulin for type 2 diabetes"},
                {"drugbank_id": "DB01261", "name": "Glipizide", "doses": [5, 10], "unit": "mg", "frequency": "Twice daily", "protocol": "Sulfonylurea for type 2 diabetes"}
            ],
            "254837009": [  # Hypertension
                {"drugbank_id": "DB01175", "name": "Lisinopril", "doses": [5, 10, 20], "unit": "mg", "frequency": "Once daily", "protocol": "ACE inhibitor - first-line for hypertension"},
                {"drugbank_id": "DB00472", "name": "Amlodipine", "doses": [5, 10], "unit": "mg", "frequency": "Once daily", "protocol": "Calcium channel blocker for hypertension"},
                {"drugbank_id": "DB00366", "name": "Losartan", "doses": [25, 50, 100], "unit": "mg", "frequency": "Once daily", "protocol": "ARB for hypertension"}
            ],
            "38341003": [  # Hypertensive disorder
                {"drugbank_id": "DB00321", "name": "Hydrochlorothiazide", "doses": [12.5, 25], "unit": "mg", "frequency": "Once daily", "protocol": "Thiazide diuretic for hypertension"},
                {"drugbank_id": "DB00678", "name": "Metoprolol", "doses": [25, 50, 100], "unit": "mg", "frequency": "Twice daily", "protocol": "Beta-blocker for hypertension"}
            ],
            "372244006": [  # Asthma
                {"drugbank_id": "DB14761", "name": "Albuterol", "doses": [90, 180], "unit": "mcg", "frequency": "As needed", "protocol": "Short-acting beta-agonist for acute asthma"},
                {"drugbank_id": "DB01264", "name": "Fluticasone", "doses": [110, 220], "unit": "mcg", "frequency": "Twice daily", "protocol": "Inhaled corticosteroid for asthma control"},
                {"drugbank_id": "DB01167", "name": "Montelukast", "doses": [10], "unit": "mg", "frequency": "Once daily", "protocol": "Leukotriene receptor antagonist for asthma"}
            ],
            "26889001": [  # COPD
                {"drugbank_id": "DB14761", "name": "Albuterol", "doses": [90, 180], "unit": "mcg", "frequency": "As needed", "protocol": "Bronchodilator for COPD"},
                {"drugbank_id": "DB01193", "name": "Tiotropium", "doses": [18], "unit": "mcg", "frequency": "Once daily", "protocol": "Long-acting anticholinergic for COPD"}
            ],
            "10742861000119102": [  # Dyslipidemia
                {"drugbank_id": "DB00655", "name": "Atorvastatin", "doses": [10, 20, 40, 80], "unit": "mg", "frequency": "Once daily", "protocol": "Statin therapy for hyperlipidemia"},
                {"drugbank_id": "DB00641", "name": "Simvastatin", "doses": [10, 20, 40], "unit": "mg", "frequency": "Once daily", "protocol": "Statin for cholesterol management"}
            ],
            "49436004": [  # Atrial fibrillation
                {"drugbank_id": "DB00366", "name": "Warfarin", "doses": [2.5, 5, 7.5], "unit": "mg", "frequency": "Once daily", "protocol": "Anticoagulant for stroke prevention in AFib"},
                {"drugbank_id": "DB01274", "name": "Apixaban", "doses": [2.5, 5], "unit": "mg", "frequency": "Twice daily", "protocol": "DOAC for stroke prevention in AFib"}
            ],
            "363418016": [  # Depression
                {"drugbank_id": "DB00264", "name": "Sertraline", "doses": [50, 100, 200], "unit": "mg", "frequency": "Once daily", "protocol": "SSRI - first-line for depression"},
                {"drugbank_id": "DB00715", "name": "Citalopram", "doses": [20, 40], "unit": "mg", "frequency": "Once daily", "protocol": "SSRI for depression"},
                {"drugbank_id": "DB00261", "name": "Escitalopram", "doses": [10, 20], "unit": "mg", "frequency": "Once daily", "protocol": "SSRI for depression"}
            ],
            "35489007": [  # Chronic kidney disease
                {"drugbank_id": "DB01175", "name": "Lisinopril", "doses": [5, 10, 20], "unit": "mg", "frequency": "Once daily", "protocol": "ACE inhibitor for CKD - slows progression"},
                {"drugbank_id": "DB00366", "name": "Losartan", "doses": [25, 50, 100], "unit": "mg", "frequency": "Once daily", "protocol": "ARB for CKD protection"}
            ],
            "363478007": [  # Anxiety disorder
                {"drugbank_id": "DB00856", "name": "Alprazolam", "doses": [0.25, 0.5, 1], "unit": "mg", "frequency": "Three times daily", "protocol": "Benzodiazepine for anxiety"},
                {"drugbank_id": "DB00264", "name": "Sertraline", "doses": [50, 100], "unit": "mg", "frequency": "Once daily", "protocol": "SSRI for anxiety disorders"}
            ],
            "363346000": [  # Breast cancer
                {"drugbank_id": "DB01001", "name": "Tamoxifen", "doses": [20], "unit": "mg", "frequency": "Once daily", "protocol": "Hormone therapy for breast cancer", "pgx_note": "Metabolized by CYP2D6"},
                {"drugbank_id": "DB01273", "name": "Anastrozole", "doses": [1], "unit": "mg", "frequency": "Once daily", "protocol": "Aromatase inhibitor for breast cancer"},
                {"drugbank_id": "DB00392", "name": "Letrozole", "doses": [2.5], "unit": "mg", "frequency": "Once daily", "protocol": "Aromatase inhibitor for breast cancer"}
            ],
            "266430006": [  # GERD
                {"drugbank_id": "DB00738", "name": "Omeprazole", "doses": [20, 40], "unit": "mg", "frequency": "Once daily", "protocol": "PPI for GERD"},
                {"drugbank_id": "DB01120", "name": "Pantoprazole", "doses": [20, 40], "unit": "mg", "frequency": "Once daily", "protocol": "PPI for GERD management"}
            ],
            "161891005": [  # Osteoarthritis
                {"drugbank_id": "DB01229", "name": "Celecoxib", "doses": [100, 200], "unit": "mg", "frequency": "Twice daily", "protocol": "COX-2 inhibitor for osteoarthritis"},
                {"drugbank_id": "DB00454", "name": "Ibuprofen", "doses": [400, 600, 800], "unit": "mg", "frequency": "Three times daily", "protocol": "NSAID for osteoarthritis pain"}
            ],
            "4855003": [  # Hypothyroidism
                {"drugbank_id": "DB00651", "name": "Levothyroxine", "doses": [25, 50, 75, 100], "unit": "mcg", "frequency": "Once daily", "protocol": "Thyroid hormone replacement"}
            ]
        }
    
    def _generate_current_medications(self, conditions: list) -> list:
        """Generate medication list based on patient's conditions - medications are linked to conditions"""
        if not conditions:
            return []  # No conditions = no medications
        
        drug_mapping = self._get_condition_drug_mapping()
        selected_medications = []
        current_date = datetime.now()
        seen_drug_ids = set()  # Avoid duplicate medications
        
        # For each condition, randomly select 1-2 medications from its medication list
        for condition in conditions:
            snomed_code = condition.get("snomed:code")
            if not snomed_code or snomed_code not in drug_mapping:
                continue
            
            condition_meds = drug_mapping[snomed_code]
            # Select 1-2 medications for this condition (80% chance of 1 med, 20% chance of 2)
            num_meds = 1 if random.random() < 0.8 else 2
            num_meds = min(num_meds, len(condition_meds))
            
            selected_for_condition = random.sample(condition_meds, num_meds)
            
            for med_info in selected_for_condition:
                drugbank_id = med_info["drugbank_id"]
                
                # Skip if already added (for conditions that share medications)
                if drugbank_id in seen_drug_ids:
                    continue
                
                seen_drug_ids.add(drugbank_id)
                
                # Generate random start date (1 month to 2 years ago, or condition diagnosis date if more recent)
                condition_date = datetime.strptime(condition.get("diagnosis_date", current_date.strftime("%Y-%m-%d")), "%Y-%m-%d")
                days_ago = random.randint(30, 730)  # 1 month to 2 years
                start_date = max(
                    (current_date - timedelta(days=days_ago)).strftime("%Y-%m-%d"),
                    condition.get("diagnosis_date", current_date.strftime("%Y-%m-%d"))
                )
                
                # Random dose selection
                dose_value = random.choice(med_info["doses"])
                
                # Build medication object
                medication = {
                    "@id": f"https://go.drugbank.com/drugs/{drugbank_id}",
                    "@type": "sdisco:Medication",
                    "drugbank:id": drugbank_id,
                    "rdfs:label": med_info["name"],
                    "schema:name": med_info["name"],
                    "schema:dosageForm": "tablet" if med_info["unit"] in ["mg", "mcg"] else "injection" if med_info["unit"] == "units" else "inhaler",
                    "schema:doseValue": dose_value,
                    "schema:doseUnit": med_info["unit"],
                    "schema:frequency": med_info["frequency"],
                    "start_date": start_date,
                    "purpose": condition.get("rdfs:label", "Unknown condition"),
                    "protocol": med_info.get("protocol", ""),
                    "treats_condition": {
                        "@id": condition.get("@id"),
                        "snomed:code": snomed_code,
                        "rdfs:label": condition.get("rdfs:label")
                    }
                }
                
                # Add PGx note if present
                if "pgx_note" in med_info:
                    medication["note"] = med_info["pgx_note"]
                
                selected_medications.append(medication)
        
        return selected_medications
    
    def _generate_organ_function(self) -> dict:
        """Generate organ function test results with random but realistic values"""
        test_date = (datetime.now() - timedelta(days=random.randint(1, 90))).strftime("%Y-%m-%d")
        
        # Kidney function - normal range: 90-120 mL/min/1.73m²
        # Occasionally abnormal (15% chance of mild reduction)
        if random.random() < 0.15:
            creatinine_clearance = round(random.uniform(60, 89), 1)
            status_kidney = "mild_reduction"
        else:
            creatinine_clearance = round(random.uniform(90, 120), 1)
            status_kidney = "normal"
        
        serum_creatinine = round(random.uniform(0.6, 1.1), 2)
        
        # Liver function - normal ALT: 7-56 U/L, AST: 10-40 U/L
        # Occasionally elevated (10% chance)
        if random.random() < 0.10:
            alt_value = round(random.uniform(57, 100), 0)
            ast_value = round(random.uniform(41, 80), 0)
            status_liver = "elevated"
        else:
            alt_value = round(random.uniform(10, 50), 0)
            ast_value = round(random.uniform(15, 38), 0)
            status_liver = "normal"
        
        bilirubin_total = round(random.uniform(0.3, 1.0), 2)
        
        return {
            "kidney_function": {
                "creatinine_clearance": {
                    "@id": "http://snomed.info/id/102001005",
                    "snomed:code": "102001005",
                    "rdfs:label": "Creatinine clearance test",
                    "value": creatinine_clearance,
                    "unit": "mL/min/1.73m²",
                    "date": test_date,
                    "normal_range": "90-120 mL/min/1.73m²",
                    "status": status_kidney
                },
                "serum_creatinine": {
                    "value": serum_creatinine,
                    "unit": "mg/dL",
                    "date": test_date,
                    "normal_range": "0.6-1.1 mg/dL",
                    "status": "normal" if serum_creatinine <= 1.1 else "elevated"
                }
            },
            "liver_function": {
                "alt": {
                    "@id": "http://snomed.info/id/102711005",
                    "snomed:code": "102711005",
                    "rdfs:label": "Alanine aminotransferase measurement",
                    "value": alt_value,
                    "unit": "U/L",
                    "date": test_date,
                    "normal_range": "7-56 U/L",
                    "status": status_liver
                },
                "ast": {
                    "@id": "http://snomed.info/id/102712005",
                    "snomed:code": "102712005",
                    "rdfs:label": "Aspartate aminotransferase measurement",
                    "value": ast_value,
                    "unit": "U/L",
                    "date": test_date,
                    "normal_range": "10-40 U/L",
                    "status": status_liver
                },
                "bilirubin_total": {
                    "value": bilirubin_total,
                    "unit": "mg/dL",
                    "date": test_date,
                    "normal_range": "0.1-1.2 mg/dL",
                    "status": "normal" if bilirubin_total <= 1.2 else "elevated"
                }
            },
            "note": "Critical for drug dosing - particularly important for drugs cleared by kidney/liver"
        }
    
    def _generate_lifestyle_factors(self) -> list:
        """Generate lifestyle factors affecting drug metabolism - randomly selected"""
        factors = []
        
        # Smoking status
        smoking_options = [
            {
                "@id": "http://snomed.info/id/228150001",
                "@type": "sdisco:LifestyleFactor",
                "snomed:code": "228150001",
                "rdfs:label": "Non-smoker",
                "skos:prefLabel": "Non-smoker",
                "factor_type": "smoking",
                "status": "never",
                "note": "No CYP1A2 induction from smoking",
                "probability": 0.75  # 75% non-smokers
            },
            {
                "@id": "http://snomed.info/id/77176002",
                "@type": "sdisco:LifestyleFactor",
                "snomed:code": "77176002",
                "rdfs:label": "Smoker",
                "skos:prefLabel": "Smoker",
                "factor_type": "smoking",
                "status": "current",
                "frequency": f"{random.randint(5, 30)} cigarettes/day",
                "note": "CYP1A2 induction from smoking",
                "probability": 0.25  # 25% smokers
            }
        ]
        
        # Alcohol consumption
        alcohol_options = [
            {
                "@id": "http://snomed.info/id/228149004",
                "@type": "sdisco:LifestyleFactor",
                "snomed:code": "228149004",
                "rdfs:label": "Drinks alcohol",
                "skos:prefLabel": "Drinks alcohol",
                "factor_type": "alcohol",
                "status": "occasional",
                "frequency": "2-3 drinks per week",
                "note": "Minimal CYP2E1 induction",
                "probability": 0.60  # 60% occasional drinkers
            },
            {
                "@id": "http://snomed.info/id/160244002",
                "@type": "sdisco:LifestyleFactor",
                "snomed:code": "160244002",
                "rdfs:label": "Never drinks alcohol",
                "skos:prefLabel": "Never drinks alcohol",
                "factor_type": "alcohol",
                "status": "never",
                "note": "No CYP2E1 induction",
                "probability": 0.40  # 40% non-drinkers
            }
        ]
        
        # Select smoking status
        smoking_choice = random.choices(smoking_options, weights=[s["probability"] for s in smoking_options])[0]
        smoking_copy = smoking_choice.copy()
        smoking_copy.pop("probability")
        factors.append(smoking_copy)
        
        # Select alcohol status
        alcohol_choice = random.choices(alcohol_options, weights=[a["probability"] for a in alcohol_options])[0]
        alcohol_copy = alcohol_choice.copy()
        alcohol_copy.pop("probability")
        factors.append(alcohol_copy)
        
        # Grapefruit consumption (10% consume regularly, 20% avoid)
        if random.random() < 0.20:
            factors.append({
                "@id": "http://snomed.info/id/226529007",
                "@type": "sdisco:LifestyleFactor",
                "snomed:code": "226529007",
                "rdfs:label": "Grapefruit",
                "skos:prefLabel": "Grapefruit",
                "factor_type": "diet",
                "status": "avoid",
                "note": "Avoids grapefruit juice consumption (CYP3A4 inhibitor)"
            })
        elif random.random() < 0.10:
            factors.append({
                "@id": "http://snomed.info/id/226529007",
                "@type": "sdisco:LifestyleFactor",
                "snomed:code": "226529007",
                "rdfs:label": "Grapefruit",
                "skos:prefLabel": "Grapefruit",
                "factor_type": "diet",
                "status": "regular",
                "frequency": "Daily grapefruit juice consumption",
                "note": "WARNING: CYP3A4 inhibition - may affect drug metabolism"
            })
        
        return factors
    
    def _generate_clinical_summary(self, variants: list) -> dict:
        """Generate clinical summary from variants"""
        summary = {
            "total_variants": len(variants),
            "by_significance": {},
            "drug_response_variants": 0,
            "pathogenic_variants": 0,
            "high_impact_genes": []
        }
        
        gene_impact = {}
        
        for variant in variants:
            # Count by significance
            sig = variant.get("clinical_significance", "Unknown")
            summary["by_significance"][sig] = summary["by_significance"].get(sig, 0) + 1
            
            # Count special categories
            if "drug response" in sig.lower():
                summary["drug_response_variants"] += 1
            if "pathogenic" in sig.lower():
                summary["pathogenic_variants"] += 1
            
            # Track gene impact
            gene = variant.get("gene")
            if gene:
                gene_impact[gene] = gene_impact.get(gene, 0) + len(variant.get("drugs", []))
        
        # Identify high-impact genes (>3 drug interactions)
        summary["high_impact_genes"] = [gene for gene, impact in gene_impact.items() if impact > 3]
        
        return summary
    
    def _generate_literature_summary(self, variants: list) -> dict:
        """Generate literature summary from variants with enhanced variant-specific data"""
        total_publications = 0
        total_gene_pubs = 0
        total_variant_pubs = 0
        total_drug_pubs = 0
        genes_with_literature = set()
        drugs_with_literature = set()
        variants_with_literature = set()
        top_publications = []
        
        for variant in variants:
            literature = variant.get("literature", {})
            variant_id = variant.get("variant_id", "Unknown")
            gene = variant.get("gene")
            
            # Count gene publications
            gene_pubs = literature.get("gene_publications", [])
            total_gene_pubs += len(gene_pubs)
            
            # Count variant-specific publications (NEW)
            variant_pubs = literature.get("variant_specific_publications", [])
            total_variant_pubs += len(variant_pubs)
            
            if gene_pubs or variant_pubs:
                genes_with_literature.add(gene)
                
            if variant_pubs:
                variants_with_literature.add(f"{gene}:{variant_id}")
                
            # Collect top publications from gene-level sources
            for pub in gene_pubs:
                if pub.get("citation_count", 0) > 50:  # Lowered threshold for more results
                    top_publications.append({
                        "pmid": pub.get("pmid"),
                        "title": pub.get("title", "")[:100] + "..." if len(pub.get("title", "")) > 100 else pub.get("title", ""),
                        "citation_count": pub.get("citation_count", 0),
                        "gene": gene,
                        "variant": None,  # Gene-level publications don't have specific variants
                        "search_type": "gene-level"
                    })
            
            # Collect top publications from variant-specific sources
            for pub in variant_pubs:
                if pub.get("citation_count", 0) > 50:
                    # Check if this publication has a search_variant field from the Europe PMC client
                    search_variant = pub.get("search_variant", variant_id)
                    top_publications.append({
                        "pmid": pub.get("pmid"),
                        "title": pub.get("title", "")[:100] + "..." if len(pub.get("title", "")) > 100 else pub.get("title", ""),
                        "citation_count": pub.get("citation_count", 0),
                        "gene": gene,
                        "variant": search_variant,  # Use the actual variant that was searched
                        "search_type": "variant-specific"
                    })
            
            # Count drug publications
            drug_pubs = literature.get("drug_publications", {})
            for drug, pubs in drug_pubs.items():
                total_drug_pubs += len(pubs)
                if pubs:
                    drugs_with_literature.add(drug)
                    
                # Add drug-specific publications to top list
                for pub in pubs:
                    if pub.get("citation_count", 0) > 20:  # Lower threshold for drug studies
                        # Get the actual variant used in the search
                        search_terms = pub.get("search_terms", "")
                        search_variant = variant_id
                        if "+" in search_terms:
                            # Extract variant from search_terms like "rs1602591357 + tramadol"
                            parts = search_terms.split(" + ")
                            if len(parts) >= 2:
                                search_variant = parts[0]
                        
                        top_publications.append({
                            "pmid": pub.get("pmid"),
                            "title": pub.get("title", "")[:100] + "..." if len(pub.get("title", "")) > 100 else pub.get("title", ""),
                            "citation_count": pub.get("citation_count", 0),
                            "gene": gene,
                            "variant": search_variant,  # Use the actual variant from search
                            "drug": drug,
                            "search_type": "variant-drug"
                        })
        
        total_publications = total_gene_pubs + total_variant_pubs + total_drug_pubs
        
        # Sort top publications by citation count
        top_publications.sort(key=lambda x: x.get("citation_count", 0), reverse=True)
        
        return {
            "total_publications": total_publications,
            "gene_publications": total_gene_pubs,
            "variant_specific_publications": total_variant_pubs,  # NEW
            "drug_publications": total_drug_pubs,
            "genes_with_literature": len(genes_with_literature),
            "variants_with_literature": len(variants_with_literature),  # NEW
            "drugs_with_literature": len(drugs_with_literature),
            "top_publications": top_publications[:10],  # Top 10 most cited
            "search_specificity": {  # NEW - shows search quality
                "variant_specific_coverage": f"{len(variants_with_literature)}/{len(variants)} variants",
                "drug_interaction_coverage": f"{len(drugs_with_literature)} drugs",
                "high_impact_studies": len([p for p in top_publications if p.get("citation_count", 0) > 100])
            },
            "coverage": {
                "genes_covered": list(genes_with_literature),
                "variants_covered": list(variants_with_literature)[:10],  # NEW
                "drugs_covered": list(drugs_with_literature)[:10]
            }
        }
    
    def _generate_comprehensive_outputs(self, patient_id: str, profile: dict, gene_results: dict) -> dict:
        """Generate comprehensive output files"""
        from pathlib import Path
        import json
        
        outputs = {}
        
        # Create comprehensive output directory
        comp_dir = Path("output/comprehensive")
        comp_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Comprehensive JSON-LD
        jsonld_file = comp_dir / f"{patient_id}_comprehensive.jsonld"
        with open(jsonld_file, 'w', encoding='utf-8') as f:
            json.dump(profile, f, indent=2)
        outputs["Comprehensive JSON-LD"] = str(jsonld_file)
        
        # 2. Summary report
        summary_file = comp_dir / f"{patient_id}_summary.json"
        summary = {
            "patient_id": patient_id,
            "analysis_date": datetime.now().isoformat(),
            "genes_analyzed": profile["pharmacogenomics_profile"]["genes_analyzed"],
            "clinical_summary": profile["pharmacogenomics_profile"]["clinical_summary"],
            "drug_interactions": len(profile["pharmacogenomics_profile"]["affected_drugs"]),
            "disease_associations": len(profile["pharmacogenomics_profile"]["associated_diseases"]),
            "gene_results": {gene: {"success": result["success"], "variants": result.get("variants_processed", 0)} for gene, result in gene_results.items()}
        }
        
        # Add variant linking summary if available
        if "variant_linking" in profile:
            linking = profile["variant_linking"]
            summary["variant_linking"] = linking.get("summary", {})
            summary["conflicts"] = linking.get("conflicts", [])
            summary["total_conflicts"] = len(linking.get("conflicts", []))
            summary["critical_conflicts"] = len([c for c in linking.get("conflicts", []) if c.get("severity") == "CRITICAL"])
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        outputs["Summary Report"] = str(summary_file)
        
        # 3. Drug interaction matrix
        drug_matrix_file = comp_dir / f"{patient_id}_drug_matrix.json"
        drug_matrix = self._create_drug_matrix(profile["variants"])
        with open(drug_matrix_file, 'w', encoding='utf-8') as f:
            json.dump(drug_matrix, f, indent=2)
        outputs["Drug Interaction Matrix"] = str(drug_matrix_file)
        
        # 4. Conflict report (if available)
        if "variant_linking" in profile:
            conflict_file = comp_dir / f"{patient_id}_conflicts.json"
            conflict_data = {
                "conflicts": profile["variant_linking"].get("conflicts", []),
                "links": profile["variant_linking"].get("links", {}),
                "summary": profile["variant_linking"].get("summary", {})
            }
            with open(conflict_file, 'w', encoding='utf-8') as f:
                json.dump(conflict_data, f, indent=2)
            outputs["Conflict Report"] = str(conflict_file)
        
        return outputs
    
    def _create_drug_matrix(self, variants: list) -> dict:
        """Create drug-gene interaction matrix"""
        matrix = {}
        
        for variant in variants:
            gene = variant.get("gene")
            for drug_info in variant.get("drugs", []):
                drug_name = drug_info.get("name")
                if drug_name and gene:
                    if drug_name not in matrix:
                        matrix[drug_name] = {}
                    
                    matrix[drug_name][gene] = {
                        "variant": variant.get("variant_id"),
                        "recommendation": drug_info.get("recommendation"),
                        "evidence_level": drug_info.get("evidence_level"),
                        "clinical_significance": variant.get("clinical_significance")
                    }
        
        return matrix


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="PGx-KG: Build pharmacogenomics knowledge graphs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single gene analysis
  python src/main.py --gene CYP2D6
  python src/main.py --gene CYP2C19 --protein P33261
  
  # Multi-gene comprehensive analysis
  python src/main.py --genes CYP2D6 CYP2C19 CYP3A4
  python src/main.py --genes CYP2D6 CYP2C19 CYP3A4 DPYD TPMT
  
  # Custom configuration
  python src/main.py --gene CYP3A4 --config custom_config.yaml

For more information, see README.md
        """
    )
    
    parser.add_argument(
        "--gene",
        help="Single gene symbol (e.g., CYP2D6, CYP2C19)"
    )
    
    parser.add_argument(
        "--genes",
        nargs="+",
        help="Multiple gene symbols (e.g., --genes CYP2D6 CYP2C19 CYP3A4)"
    )
    
    parser.add_argument(
        "--protein",
        help="UniProt protein ID (optional, will be fetched if not provided)"
    )
    
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.gene and not args.genes:
        parser.error("Must specify either --gene or --genes")
    
    if args.gene and args.genes:
        parser.error("Cannot specify both --gene and --genes")
    
    # Run pipeline
    pipeline = PGxKGPipeline(config_path=args.config)
    
    if args.genes:
        # Multi-gene mode
        result = pipeline.run_multi_gene(args.genes)
    else:
        # Single-gene mode
        result = pipeline.run(args.gene, args.protein)
    
    # Exit with appropriate code
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()

