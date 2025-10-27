"""
PharmGKB Client
Queries PharmGKB for pharmacogenomic annotations and drug-gene interactions
"""
import sys
import re
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from typing import Dict, Optional, List
from utils.api_client import APIClient
from utils.evidence_levels import EvidenceLevelInterpreter


class PharmGKBClient:
    """Client for querying PharmGKB API"""
    
    def __init__(self):
        """Initialize PharmGKB client"""
        self.base_url = "https://api.pharmgkb.org/v1/data"
        # Use 1.5 requests per second to be conservative with PharmGKB rate limits
        self.client = APIClient(self.base_url, rate_limit=1.5)
        self.evidence_interpreter = EvidenceLevelInterpreter()
    
    def get_gene_annotations(self, gene_symbol: str) -> List[Dict]:
        """
        Get clinical annotations for a gene
        
        Args:
            gene_symbol: Gene symbol (e.g., CYP2D6)
            
        Returns:
            List of clinical annotations
        """
        endpoint = "clinicalAnnotation"
        params = {
            "location.genes.symbol": gene_symbol
        }
        
        data = self.client.get(endpoint, params=params)
        
        if data and "data" in data:
            return data["data"]
        
        return []
    
    def get_variant_annotations(self, rsid: str) -> List[Dict]:
        """
        Get variant information (not clinical annotations, which are gene-based)
        
        Args:
            rsid: rsID (e.g., rs1065852)
            
        Returns:
            List containing variant information
        """
        # Get basic variant info from PharmGKB
        variant_endpoint = "variant"
        variant_params = {"name": rsid}
        
        variant_data = self.client.get(variant_endpoint, params=variant_params)
        
        if variant_data and "data" in variant_data:
            return variant_data["data"]
        
        return []
    
    def get_cpic_guidelines(self, gene_symbol: str) -> List[Dict]:
        """
        Get CPIC guidelines for a gene
        
        Args:
            gene_symbol: Gene symbol
            
        Returns:
            List of CPIC guideline annotations
        """
        annotations = self.get_gene_annotations(gene_symbol)
        
        # Filter for CPIC guidelines
        cpic_guidelines = [
            ann for ann in annotations
            if "CPIC" in ann.get("source", "").upper() or
               "CPIC" in ann.get("drugName", "").upper()
        ]
        
        return cpic_guidelines
    
    def get_haplotypes(self, gene_symbol: str) -> List[Dict]:
        """
        Get haplotype information for a gene
        
        Args:
            gene_symbol: Gene symbol
            
        Returns:
            List of haplotypes
        """
        endpoint = "haplotype"
        params = {
            "gene.symbol": gene_symbol
        }
        
        data = self.client.get(endpoint, params=params)
        
        if data and "data" in data:
            return data["data"]
        
        return []
    
    def determine_metabolizer_phenotype(self, gene_symbol: str, variants: List[Dict]) -> Optional[Dict]:
        """
        Determine metabolizer phenotype from diplotype/genotype
        
        Args:
            gene_symbol: Gene symbol (e.g., CYP2C19, CYP2D6)
            variants: List of variant dictionaries (diplotype = 2 variants)
            
        Returns:
            Dictionary with phenotype information: {
                "phenotype": "Normal Metabolizer" | "Poor Metabolizer" | "Intermediate Metabolizer" | "Ultrarapid Metabolizer",
                "diplotype": "*1/*1",
                "functionality": "Normal/Normal",
                "source": "PharmGKB/CPIC"
            }
        """
        if not variants or len(variants) == 0:
            return {
                "phenotype": "Not determined",
                "diplotype": "Unknown/Unknown",
                "functionality": "Unknown/Unknown",
                "source": "No variants found"
            }
        
        # Get PharmGKB haplotypes to map variants to star alleles
        haplotypes = self.get_haplotypes(gene_symbol)
        
        # Try to extract star allele names from PharmGKB data or variant annotations
        star_alleles = []
        for variant in variants[:2]:  # Only use first 2 for diplotype
            # Check PharmGKB data for star allele assignment
            pharmgkb_data = variant.get("pharmgkb", {})
            annotations = pharmgkb_data.get("annotations", [])
            
            star_allele = None
            # Look for star allele mentions in phenotypes or drug recommendations
            for ann in annotations:
                phenotype_text = ""
                for allele_pheno in ann.get("allelePhenotypes", []):
                    phenotype_text += " " + allele_pheno.get("phenotype", "")
                
                # Search for star allele pattern (e.g., CYP2C19*17, *2, *1/*2)
                star_pattern = rf'{gene_symbol}\*(\d+[A-Z]?)|\*(\d+[A-Z]?)'
                matches = re.findall(star_pattern, phenotype_text, re.IGNORECASE)
                if matches:
                    # Extract star allele number
                    for match in matches:
                        star_num = match[0] or match[1]
                        if star_num:
                            star_allele = f"*{star_num}"
                            break
                
                if star_allele:
                    break
            
            if not star_allele:
                # Try to match based on variant rsID to known star alleles
                rsid = None
                for xref in variant.get("xrefs", []):
                    if xref.get("name") == "dbSNP":
                        rsid = xref.get("id")
                        break
                
                # Map common variants to star alleles (simplified - should use PharmGKB API)
                star_allele = self._map_variant_to_star_allele(gene_symbol, rsid, variant)
            
            star_alleles.append(star_allele or "*1")  # Default to *1 (wild-type)
        
        # If only one variant, assume homozygous
        if len(star_alleles) == 1:
            star_alleles.append(star_alleles[0])
        
        diplotype = f"{star_alleles[0]}/{star_alleles[1]}"
        
        # Determine functionality and phenotype based on star alleles
        functionality = self._get_allele_functionality(gene_symbol, star_alleles[0], star_alleles[1])
        phenotype = self._determine_phenotype_from_functionality(functionality)
        
        return {
            "phenotype": phenotype,
            "diplotype": diplotype,
            "functionality": functionality,
            "star_alleles": star_alleles,
            "source": "PharmGKB/CPIC"
        }
    
    def _map_variant_to_star_allele(self, gene_symbol: str, rsid: str, variant: Dict) -> Optional[str]:
        """
        Map a variant rsID to a star allele (simplified - should query PharmGKB API)
        This is a basic implementation - ideally should use PharmGKB variant-to-haplotype mapping
        """
        # Common rsID to star allele mappings (simplified - would need comprehensive database)
        # This is a placeholder - full implementation should query PharmGKB
        known_mappings = {
            "CYP2C19": {
                "rs4244285": "*2",  # CYP2C19*2
                "rs4986893": "*3",   # CYP2C19*3
                "rs12248560": "*17", # CYP2C19*17
            },
            "CYP2D6": {
                "rs1065852": "*10",  # CYP2D6*10
                "rs3892097": "*4",   # CYP2D6*4
                "rs1135840": "*2",   # CYP2D6*2
            }
        }
        
        if gene_symbol in known_mappings and rsid in known_mappings[gene_symbol]:
            return known_mappings[gene_symbol][rsid]
        
        return None
    
    def _get_allele_functionality(self, gene_symbol: str, allele1: str, allele2: str) -> str:
        """
        Get functionality description for a diplotype
        
        Args:
            gene_symbol: Gene symbol
            allele1: First star allele (e.g., "*1", "*2")
            allele2: Second star allele (e.g., "*1", "*17")
            
        Returns:
            Functionality string like "Normal/Decreased" or "Normal/Normal"
        """
        # Map star alleles to functionality (CPIC/PharmGKB standard)
        # This is simplified - full implementation would query PharmGKB API
        functionality_map = {
            "CYP2C19": {
                "*1": "Normal",
                "*2": "Decreased",
                "*3": "Decreased",
                "*17": "Increased",
            },
            "CYP2D6": {
                "*1": "Normal",
                "*2": "Normal",
                "*4": "Decreased",
                "*10": "Decreased",
            }
        }
        
        func_map = functionality_map.get(gene_symbol, {})
        func1 = func_map.get(allele1, "Unknown")
        func2 = func_map.get(allele2, "Unknown")
        
        return f"{func1}/{func2}"
    
    def _determine_phenotype_from_functionality(self, functionality: str) -> str:
        """
        Determine metabolizer phenotype from functionality
        
        Args:
            functionality: String like "Normal/Normal" or "Normal/Decreased"
            
        Returns:
            Phenotype string like "Normal Metabolizer" or "Intermediate Metabolizer"
        """
        func_parts = functionality.split("/")
        if len(func_parts) != 2:
            return "Not determined"
        
        func1, func2 = func_parts
        
        # Both alleles have same functionality
        if func1 == func2:
            if func1 == "Normal":
                return "Normal Metabolizer"
            elif func1 == "Decreased":
                return "Poor Metabolizer"
            elif func1 == "Increased":
                return "Ultrarapid Metabolizer"
        
        # Mixed functionality
        functions = [func1, func2]
        if "Increased" in functions:
            return "Ultrarapid Metabolizer"
        elif "Decreased" in functions or "No function" in functions:
            if "Normal" in functions:
                return "Intermediate Metabolizer"
            else:
                return "Poor Metabolizer"
        elif "Normal" in functions:
            return "Normal Metabolizer"
        
        return "Unknown Metabolizer"
    
    def extract_drugs_from_annotations(self, annotations: List[Dict]) -> List[Dict]:
        """
        Extract drug information from annotations
        
        Args:
            annotations: List of PharmGKB annotations
            
        Returns:
            List of drug dictionaries with recommendations
        """
        drugs = []
        seen_drugs = set()
        
        for ann in annotations:
            # Extract drugs from relatedChemicals field
            related_chemicals = ann.get("relatedChemicals", [])
            
            for chemical in related_chemicals:
                drug_name = chemical.get("name")
                if not drug_name or drug_name in seen_drugs:
                    continue
                
                seen_drugs.add(drug_name)
                
                # Extract recommendation from allele phenotypes
                recommendation = ""
                allele_phenotypes = ann.get("allelePhenotypes", [])
                if allele_phenotypes:
                    # Use the first phenotype as the recommendation
                    recommendation = allele_phenotypes[0].get("phenotype", "")
                
                # Get evidence level and interpret it
                evidence_level_obj = ann.get("levelOfEvidence", {})
                evidence_level = evidence_level_obj.get("term", "") if isinstance(evidence_level_obj, dict) else str(evidence_level_obj)
                
                # Interpret the evidence level
                evidence_interpretation = {}
                if evidence_level:
                    evidence_interpretation = self.evidence_interpreter.interpret_pharmgkb_level(evidence_level)
                
                drug_info = {
                    "name": drug_name,
                    "pharmgkb_id": chemical.get("id", ""),
                    "recommendation": recommendation,
                    "evidence_level": evidence_level,
                    "evidence_interpretation": evidence_interpretation,
                    "annotation_type": ann.get("types", []),
                    "source": "PharmGKB",
                    "annotation_name": ann.get("name", ""),
                    "score": ann.get("score", "")
                }
                
                drugs.append(drug_info)
        
        return drugs
    
    def extract_phenotypes_from_annotations(self, annotations: List[Dict]) -> List[str]:
        """
        Extract phenotype descriptions from annotations
        
        Args:
            annotations: List of PharmGKB annotations
            
        Returns:
            List of phenotype descriptions
        """
        phenotypes = set()
        
        for ann in annotations:
            # Check allelePhenotypes array (main source of phenotype data)
            allele_phenotypes = ann.get("allelePhenotypes", [])
            for allele_pheno in allele_phenotypes:
                phenotype_text = allele_pheno.get("phenotype", "")
                if phenotype_text:
                    # Extract key metabolizer phenotypes and drug response info
                    if any(word in phenotype_text.lower() for word in 
                          ["metabolizer", "metaboliser", "function", "clearance", "response", "efficacy", "toxicity"]):
                        # Shorten very long phenotype descriptions
                        if len(phenotype_text) > 200:
                            # Extract the key part (usually first sentence)
                            sentences = phenotype_text.split('. ')
                            if sentences:
                                phenotype_text = sentences[0] + '.'
                        phenotypes.add(phenotype_text)
            
            # Also check top-level phenotype fields (backup)
            for field in ["phenotype", "phenotypeCategory"]:
                if field in ann and ann[field]:
                    text = ann[field]
                    if any(word in text.lower() for word in ["metabolizer", "metaboliser", "function"]):
                        phenotypes.add(text)
        
        return list(phenotypes)
    
    def enrich_variant(self, variant: Dict, gene_symbol: str) -> Dict:
        """
        Enrich variant with PharmGKB data
        
        Args:
            variant: Variant dictionary
            gene_symbol: Gene symbol
            
        Returns:
            Enriched variant dictionary
        """
        # Get rsID
        rsid = None
        for xref in variant.get("xrefs", []):
            if xref.get("name") == "dbSNP":
                rsid = xref.get("id")
                break
        
        # Get annotations
        if rsid:
            variant_annotations = self.get_variant_annotations(rsid)
        else:
            variant_annotations = []
        
        # Also get gene-level annotations
        gene_annotations = self.get_gene_annotations(gene_symbol)
        
        all_annotations = variant_annotations + gene_annotations
        
        # Extract information
        drugs = self.extract_drugs_from_annotations(all_annotations)
        phenotypes = self.extract_phenotypes_from_annotations(all_annotations)
        
        # Add to variant
        variant["pharmgkb"] = {
            "annotations": all_annotations[:5],  # Limit to top 5
            "drugs": drugs,
            "phenotypes": phenotypes
        }
        
        return variant

