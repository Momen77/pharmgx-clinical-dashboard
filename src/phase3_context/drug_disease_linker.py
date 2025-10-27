"""
Drug & Disease Linker
Orchestrates Phase 3: Drug and disease context enrichment
"""
import json
from pathlib import Path
from typing import Dict
import sys
sys.path.append(str(Path(__file__).parent.parent))

from phase3_context.identifier_mapper import IdentifierMapper
from phase3_context.openfda_client import OpenFDAClient
from phase3_context.chembl_client import ChEMBLClient
from phase3_context.europepmc_client import EuropePMCClient
from phase2_clinical.bioportal_client import BioPortalClient


class DrugDiseaseLinker:
    """Links variants to drugs, diseases, and literature"""
    
    def __init__(self, bioportal_api_key: str = None):
        """
        Initialize drug-disease linker
        
        Args:
            bioportal_api_key: BioPortal API key for SNOMED CT
        """
        self.identifier_mapper = IdentifierMapper()
        self.openfda = OpenFDAClient()
        self.chembl = ChEMBLClient()
        self.europepmc = EuropePMCClient()
        self.bioportal = BioPortalClient(bioportal_api_key) if bioportal_api_key else None
        self.output_dir = Path("data/phase3")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_clinvar_diseases(self, variant: dict) -> list:
        """Extract diseases directly from ClinVar phenotype data"""
        diseases = []
        
        if "clinvar" in variant and "phenotypes" in variant["clinvar"]:
            for phenotype in variant["clinvar"]["phenotypes"]:
                # ClinVar phenotypes are often disease names directly
                if phenotype and len(phenotype.strip()) > 3:
                    # Map to SNOMED if BioPortal is available
                    if self.bioportal:
                        snomed_mapping = self.bioportal.search_snomed(phenotype)
                        diseases.append({
                            "disease_name": phenotype,
                            "snomed_mapping": snomed_mapping,
                            "source": "clinvar_phenotype"
                        })
                    else:
                        diseases.append({
                            "disease_name": phenotype,
                            "snomed_mapping": None,
                            "source": "clinvar_phenotype"
                        })
        
        return diseases
    
    def extract_pharmgkb_disease_associations(self, variant: dict) -> list:
        """Extract disease associations from PharmGKB phenotype data"""
        diseases = []
        
        if "pharmgkb" in variant and "phenotypes" in variant["pharmgkb"]:
            for phenotype in variant["pharmgkb"]["phenotypes"]:
                # Use the enhanced PharmGKB disease extraction
                if self.bioportal:
                    pharmgkb_diseases = self.bioportal.extract_pharmgkb_diseases(phenotype)
                    for disease in pharmgkb_diseases:
                        snomed_mapping = self.bioportal.search_snomed(disease)
                        diseases.append({
                            "disease_name": disease,
                            "snomed_mapping": snomed_mapping,
                            "source": "pharmgkb_phenotype",
                            "original_phenotype": phenotype[:100] + "..." if len(phenotype) > 100 else phenotype
                        })
        
        return diseases
    
    def map_phenotypes_to_snomed_clinical_findings(self, variants: list) -> list:
        """Map phenotype descriptions to SNOMED CT Clinical Findings and extract diseases"""
        if not self.bioportal:
            print("   WARNING: Skipping SNOMED CT mapping (no BioPortal API key)")
            return variants
        
        print("\nMapping phenotypes to SNOMED CT Clinical Findings and extracting diseases...")
        
        for variant in variants:
            # Extract diseases from multiple sources
            all_diseases = []
            
            # 1. Extract from ClinVar phenotypes (direct disease names)
            clinvar_diseases = self.extract_clinvar_diseases(variant)
            all_diseases.extend(clinvar_diseases)
            
            # 2. Extract from PharmGKB phenotypes (pharmacogenomic contexts)
            pharmgkb_diseases = self.extract_pharmgkb_disease_associations(variant)
            all_diseases.extend(pharmgkb_diseases)
            
            # Store all disease associations
            variant["disease_associations"] = all_diseases
            
            # Process ClinVar phenotypes for comprehensive mapping
            if "clinvar" in variant:
                phenotypes = variant["clinvar"].get("phenotypes", [])
                
                if phenotypes:
                    comprehensive_mappings = []
                    # Extract gene symbol from variant
                    gene_symbol = variant.get("gene_symbol") or variant.get("geneSymbol")
                    
                    for phenotype in phenotypes:
                        # Extract drug name from phenotype text if available
                        drug_name = self._extract_drug_from_phenotype(phenotype, variant)
                        
                        # Use the new comprehensive mapping with gene and drug context
                        comprehensive_mapping = self.bioportal.map_phenotype_to_diseases(
                            phenotype, gene_symbol=gene_symbol, drug_name=drug_name
                        )
                        comprehensive_mappings.append(comprehensive_mapping)
                    
                    variant["phenotypes_comprehensive"] = comprehensive_mappings
                    
                    # Keep backward compatibility with old format
                    snomed_clinical_findings = []
                    for mapping in comprehensive_mappings:
                        if mapping.get("clinical_finding"):
                            snomed_clinical_findings.append({
                                "phenotype_text": mapping["phenotype_text"],
                                "snomed_clinical_finding": mapping["clinical_finding"]
                            })
                    variant["phenotypes_snomed"] = snomed_clinical_findings
            
            # Process PharmGKB phenotypes for comprehensive mapping
            if "pharmgkb" in variant and "phenotypes" in variant["pharmgkb"]:
                pharmgkb_comprehensive = []
                gene_symbol = variant.get("gene_symbol") or variant.get("geneSymbol")
                
                for phenotype in variant["pharmgkb"]["phenotypes"]:
                    # Extract drug name from PharmGKB drugs if available
                    drug_name = self._extract_drug_from_phenotype(phenotype, variant)
                    
                    comprehensive_mapping = self.bioportal.map_phenotype_to_diseases(
                        phenotype, gene_symbol=gene_symbol, drug_name=drug_name
                    )
                    pharmgkb_comprehensive.append(comprehensive_mapping)
                
                variant["pharmgkb_phenotypes_comprehensive"] = pharmgkb_comprehensive
        
        return variants
    
    def _extract_drug_from_phenotype(self, phenotype_text: str, variant: dict) -> str:
        """Extract drug name from phenotype text or variant's drug associations"""
        import re
        
        # First, try to find drug in PharmGKB drugs list (most reliable)
        if "pharmgkb" in variant and "drugs" in variant["pharmgkb"]:
            phenotype_lower = phenotype_text.lower()
            # Sort drugs by length (longest first) to match multi-word drugs first
            drugs = sorted(variant["pharmgkb"]["drugs"], 
                          key=lambda d: len(d.get("name", "")), reverse=True)
            for drug in drugs:
                drug_name = drug.get("name", "")
                if drug_name:
                    drug_name_lower = drug_name.lower()
                    # Check for whole word match to avoid partial matches
                    if drug_name_lower in phenotype_lower:
                        # Verify it's not part of a longer word
                        pattern = r'\b' + re.escape(drug_name_lower) + r'\b'
                        if re.search(pattern, phenotype_lower):
                            return drug_name  # Return original case
        
        # Fallback: try to extract drug name from phenotype text using common patterns
        # Look for patterns like "treated with X" or "X clearance" or "response to X"
        patterns = [
            r'treated with ([A-Z][a-z]+(?:\s+[a-z]+)?)',  # "treated with Clopidogrel"
            r'([A-Z][a-z]+(?:\s+[a-z]+)?)\s+clearance',  # "Clopidogrel clearance"
            r'response to\s+([A-Z][a-z]+(?:\s+[a-z]+)?)',  # "response to Clopidogrel"
            r'metabolism of\s+([A-Z][a-z]+(?:\s+[a-z]+)?)',  # "metabolism of Clopidogrel"
            r'concentrations of\s+([A-Z][a-z]+(?:\s+[a-z]+)?)',  # "concentrations of Clopidogrel"
            r'([A-Z][a-z]+(?:\s+[a-z]+)?)\s+therapy',  # "Clopidogrel therapy"
            r'when treated with\s+([A-Z][a-z]+(?:\s+[a-z]+)?)',  # "when treated with Clopidogrel"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, phenotype_text, re.IGNORECASE)
            if match:
                potential_drug = match.group(1)
                # Filter out common non-drug words
                if potential_drug.lower() not in ["patients", "may", "have", "the", "a", "an", "this", "that"]:
                    return potential_drug
        
        return None
    
    def map_adverse_reactions_to_snomed(self, variants: list) -> list:
        """Map adverse reactions to SNOMED CT"""
        if not self.bioportal:
            return variants
        
        print("\nMapping adverse reactions to SNOMED CT...")
        
        for variant in variants:
            if "pharmgkb" not in variant or "drugs" not in variant["pharmgkb"]:
                continue
            
            for drug in variant["pharmgkb"]["drugs"]:
                if "fda_label" not in drug:
                    continue
                
                # Extract adverse reactions from FDA label
                adverse_text = drug["fda_label"].get("adverse_reactions", "")
                
                if adverse_text and len(adverse_text) > 0:
                    # Simple extraction: look for common adverse reactions
                    common_reactions = ["myopathy", "bleeding", "rash", "nausea", "hepatotoxicity"]
                    
                    found_reactions = []
                    for reaction in common_reactions:
                        if reaction.lower() in adverse_text.lower():
                            snomed_mapping = self.bioportal.map_adverse_reaction(reaction)
                            found_reactions.append({
                                "reaction": reaction,
                                "snomed": snomed_mapping
                            })
                    
                    if found_reactions:
                        drug["adverse_reactions_snomed"] = found_reactions
        
        return variants
    
    def run_pipeline(self, gene_symbol: str, phase2_file: str = None) -> Dict:
        """
        Execute Phase 3: Drug & disease enrichment pipeline
        
        Args:
            gene_symbol: Gene symbol
            phase2_file: Path to Phase 2 output file
            
        Returns:
            Enriched data
        """
        print(f"\n{'='*60}")
        print(f"Phase 3: Drug & Disease Context for {gene_symbol}")
        print(f"{'='*60}\n")
        
        # Load Phase 2 data
        if not phase2_file:
            phase2_file = f"data/phase2/{gene_symbol}_clinical.json"
        
        phase2_path = Path(phase2_file)
        if not phase2_path.exists():
            raise FileNotFoundError(f"Phase 2 output not found: {phase2_file}")
        
        with open(phase2_path, 'r', encoding='utf-8') as f:
            phase2_data = json.load(f)
        
        print(f"Loaded {phase2_data['total_variants']} variants from Phase 2")
        
        # Load configuration to check feature flags
        from utils.config import Config
        config = Config()
        
        # Enrich with ChEMBL bioactivity data (if enabled)
        if config.config.get("features", {}).get("enable_chembl", True):
            print("\nEnriching with ChEMBL bioactivity data...")
            phase2_data["variants"] = self.chembl.enrich_drugs_with_chembl_data(
                phase2_data["variants"]
            )
        else:
            print("\nSkipping ChEMBL enrichment (disabled in config)")
        
        # Enrich with OpenFDA drug labels (if enabled)
        if config.config.get("features", {}).get("enable_openfda", False):
            print("\nEnriching with OpenFDA drug labels...")
            phase2_data["variants"] = self.openfda.enrich_drugs_with_fda_data(
                phase2_data["variants"]
            )
        else:
            print("\nSkipping OpenFDA enrichment (disabled in config)")
        
        # Enrich with literature from Europe PMC (if enabled)
        if config.config.get("features", {}).get("enable_europepmc", True):
            print("\nEnriching with literature evidence...")
            phase2_data["variants"] = self.europepmc.enrich_with_literature(
                gene_symbol,
                phase2_data["variants"]
            )
        else:
            print("\nSkipping Europe PMC enrichment (disabled in config)")
        
        # Map identifiers (RxNorm, HGNC)
        print("\nMapping identifiers...")
        phase2_data = self.identifier_mapper.enrich_with_identifiers(phase2_data)
        
        # Map phenotypes to SNOMED CT Clinical Findings
        phase2_data["variants"] = self.map_phenotypes_to_snomed_clinical_findings(phase2_data["variants"])
        
        # Map adverse reactions to SNOMED CT
        phase2_data["variants"] = self.map_adverse_reactions_to_snomed(phase2_data["variants"])
        
        # Save output
        output_file = self.output_dir / f"{gene_symbol}_enriched.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(phase2_data, f, indent=2)
        
        print(f"\nPhase 3 Complete!")
        print(f"   Enriched data saved: {output_file}")
        
        return phase2_data


if __name__ == "__main__":
    # Test the module
    from utils.config import Config
    
    config = Config()
    linker = DrugDiseaseLinker(bioportal_api_key=config.bioportal_api_key)
    
    result = linker.run_pipeline("CYP2D6")
    print(f"\n   Total variants: {result['total_variants']}")

