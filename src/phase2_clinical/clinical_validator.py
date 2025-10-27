"""
Clinical Validator
Orchestrates Phase 2: Clinical validation and enrichment
"""
import json
from pathlib import Path
from typing import Dict, List, Optional
import sys
sys.path.append(str(Path(__file__).parent.parent))

from phase2_clinical.clinvar_client import ClinVarClient
from phase2_clinical.pharmgkb_client import PharmGKBClient
from phase2_clinical.bioportal_client import BioPortalClient


class ClinicalValidator:
    """Validates and enriches variants with clinical data"""
    
    def __init__(self, ncbi_email: str, ncbi_api_key: str = None, 
                 bioportal_api_key: str = None):
        """
        Initialize clinical validator
        
        Args:
            ncbi_email: Email for NCBI API
            ncbi_api_key: Optional NCBI API key
            bioportal_api_key: BioPortal API key for SNOMED CT mapping
        """
        self.clinvar = ClinVarClient(ncbi_email, ncbi_api_key)
        self.pharmgkb = PharmGKBClient()
        self.bioportal = BioPortalClient(bioportal_api_key) if bioportal_api_key else None
        self.output_dir = Path("data/phase2")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def enrich_variant(self, variant: Dict, gene_symbol: str) -> Dict:
        """
        Enrich a single variant with clinical data
        
        Args:
            variant: Variant dictionary
            gene_symbol: Gene symbol
            
        Returns:
            Enriched variant
        """
        # Preserve original evidences field for literature extraction in Phase 3
        original_evidences = variant.get("evidences", [])
        
        # Add ClinVar data
        print(f"   Enriching with ClinVar...")
        variant = self.clinvar.enrich_variant(variant)
        
        # Restore evidences if they were lost
        if not variant.get("evidences") and original_evidences:
            variant["evidences"] = original_evidences
        
        # Add PharmGKB data
        print(f"   Enriching with PharmGKB...")
        variant = self.pharmgkb.enrich_variant(variant, gene_symbol)
        
        # Ensure evidences are still preserved after PharmGKB enrichment
        if not variant.get("evidences") and original_evidences:
            variant["evidences"] = original_evidences
        
        # Map phenotypes to SNOMED CT with proper context
        if self.bioportal and "pharmgkb" in variant:
            print(f"   Mapping phenotypes to SNOMED CT...")
            phenotypes_mapped = []
            
            # Extract drug names from PharmGKB for context
            drug_names = []
            if "drugs" in variant["pharmgkb"]:
                drug_names = [drug.get("name") for drug in variant["pharmgkb"]["drugs"]]
            
            for phenotype in variant["pharmgkb"].get("phenotypes", []):
                # Try to extract drug name from phenotype text
                drug_name = self._extract_drug_from_phenotype(phenotype, drug_names)
                
                # Map with gene and drug context
                snomed_mapping = self.bioportal.map_phenotype(
                    phenotype, 
                    gene_symbol=gene_symbol, 
                    drug_name=drug_name
                )
                phenotypes_mapped.append({
                    "text": phenotype,
                    "snomed": snomed_mapping
                })
            variant["phenotypes_snomed"] = phenotypes_mapped
        
        # Extract recommended tests from CPIC guidelines
        if "pharmgkb" in variant:
            variant["recommended_tests"] = self._extract_recommended_tests(
                variant["pharmgkb"].get("annotations", []),
                gene_symbol
            )
        
        return variant
    
    def _extract_recommended_tests(self, annotations: List[Dict], gene_symbol: str) -> List[Dict]:
        """Extract genetic test recommendations from annotations"""
        tests = []
        
        # Standard test for pharmacogenes
        test_name = f"{gene_symbol} genotyping"
        test_info = {
            "test": test_name,
            "indication": f"Before prescribing drugs metabolized by {gene_symbol}"
        }
        
        # Map to SNOMED CT if BioPortal available
        if self.bioportal:
            snomed_mapping = self.bioportal.map_procedure(test_name)
            if snomed_mapping:
                test_info["snomed"] = snomed_mapping
        
        tests.append(test_info)
        
        return tests
    
    def _extract_drug_from_phenotype(self, phenotype_text: str, available_drugs: List[str]) -> Optional[str]:
        """Extract drug name from phenotype text"""
        import re
        phenotype_lower = phenotype_text.lower()
        
        # First, check if any available drug is mentioned in the phenotype
        for drug in available_drugs:
            if drug and drug.lower() in phenotype_lower:
                return drug
        
        # Try to extract drug name using patterns
        patterns = [
            r'treated with ([A-Z][a-z]+(?:\s+[a-z]+)?)',
            r'(\w+)\s+clearance',
            r'response to\s+(\w+)',
            r'metabolism of\s+(\w+)',
            r'concentrations of\s+(\w+)',
            r'(\w+)\s+therapy',
            r'(\w+)\s+pharmacokinetics'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, phenotype_text, re.IGNORECASE)
            if match:
                potential_drug = match.group(1)
                # Filter out common words
                if potential_drug.lower() not in ["patients", "may", "have", "the", "a", "an", "and", "or"]:
                    return potential_drug
        
        return None
    
    def run_pipeline(self, gene_symbol: str, phase1_file: str = None) -> Dict:
        """
        Execute Phase 2: Clinical validation pipeline
        
        Args:
            gene_symbol: Gene symbol
            phase1_file: Path to Phase 1 output file
            
        Returns:
            Enriched clinical data
        """
        print(f"\n{'='*60}")
        print(f"Phase 2: Clinical Validation for {gene_symbol}")
        print(f"{'='*60}\n")
        
        # Load Phase 1 data
        if not phase1_file:
            phase1_file = f"data/phase1/{gene_symbol}_variants.json"
        
        phase1_path = Path(phase1_file)
        if not phase1_path.exists():
            raise FileNotFoundError(f"Phase 1 output not found: {phase1_file}")
        
        with open(phase1_path, 'r', encoding='utf-8') as f:
            phase1_data = json.load(f)
        
        print(f"Loaded {phase1_data['total_variants']} total variants from Phase 1")
        
        # Get selected diplotype variants (realistic patient profile)
        selected_diplotype = phase1_data.get("selected_diplotype", {})
        diplotype_variants = selected_diplotype.get("variants", [])
        
        print(f"Processing {len(diplotype_variants)} variants from selected diplotype:")
        print(f"   {selected_diplotype.get('description', 'No description')}")
        
        # Enrich each variant in the diplotype
        enriched_variants = []
        for i, variant in enumerate(diplotype_variants, 1):
            print(f"\nDiplotype Variant {i}/{len(diplotype_variants)}: {variant.get('ftId', 'Unknown')}")
            enriched = self.enrich_variant(variant, gene_symbol)
            enriched_variants.append(enriched)
        
        # Determine metabolizer phenotype from diplotype
        print(f"\nDetermining metabolizer phenotype for {gene_symbol}...")
        phenotype_info = self.pharmgkb.determine_metabolizer_phenotype(gene_symbol, enriched_variants)
        print(f"   Diplotype: {phenotype_info.get('diplotype', 'Unknown')}")
        print(f"   Phenotype: {phenotype_info.get('phenotype', 'Unknown')}")
        print(f"   Functionality: {phenotype_info.get('functionality', 'Unknown')}")
        
        # Compile output
        # Extract gene-level phenotypes (these are often more comprehensive than variant-specific ones)
        print(f"\nExtracting gene-level phenotypes for {gene_symbol}...")
        gene_annotations = self.pharmgkb.get_gene_annotations(gene_symbol)
        gene_phenotypes = self.pharmgkb.extract_phenotypes_from_annotations(gene_annotations)
        print(f"   Found {len(gene_phenotypes)} gene-level phenotypes")
        
        # Map gene phenotypes to SNOMED CT
        gene_phenotypes_snomed = []
        if self.bioportal and gene_phenotypes:
            print(f"   Mapping gene phenotypes to SNOMED CT...")
            for phenotype in gene_phenotypes[:10]:  # Limit to 10 to avoid too many API calls
                # Extract drug name from phenotype if available
                drug_name = self._extract_drug_from_phenotype(phenotype, [])
                snomed_mapping = self.bioportal.map_phenotype(
                    phenotype, 
                    gene_symbol=gene_symbol, 
                    drug_name=drug_name
                )
                gene_phenotypes_snomed.append({
                    "text": phenotype,
                    "snomed": snomed_mapping
                })
        
        output = {
            "gene_symbol": gene_symbol,
            "protein_id": phase1_data.get("protein_id"),
            "diplotype_info": selected_diplotype,
            "metabolizer_phenotype": phenotype_info,  # Add metabolizer phenotype
            "gene_level_phenotypes": gene_phenotypes,
            "gene_phenotypes_snomed": gene_phenotypes_snomed,
            "total_variants": len(enriched_variants),
            "variants": enriched_variants,
            "timestamp": phase1_data.get("timestamp")
        }
        
        # Save output
        output_file = self.output_dir / f"{gene_symbol}_clinical.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2)
        
        print(f"\nPhase 2 Complete!")
        print(f"   Enriched variants saved: {output_file}")
        print(f"   Total variants processed: {len(enriched_variants)}")
        
        return output


if __name__ == "__main__":
    # Test the module
    from utils.config import Config
    
    config = Config()
    validator = ClinicalValidator(
        ncbi_email=config.ncbi_email,
        ncbi_api_key=config.ncbi_api_key,
        bioportal_api_key=config.bioportal_api_key
    )
    
    result = validator.run_pipeline("CYP2D6")
    print(f"\n   Variants enriched: {result['total_variants']}")

