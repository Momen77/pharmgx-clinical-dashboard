"""
Identifier Mapper
Maps drug names to RxNorm, gene symbols to HGNC, diseases to SNOMED CT
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from typing import Optional, Dict
from utils.api_client import APIClient


class IdentifierMapper:
    """Maps identifiers to standard vocabularies"""
    
    def __init__(self):
        """Initialize identifier mapper"""
        self.rxnorm_client = APIClient("https://rxnav.nlm.nih.gov/REST", rate_limit=10)
        self.hgnc_client = APIClient("https://rest.genenames.org", rate_limit=10)
    
    def drug_to_rxnorm(self, drug_name: str) -> Optional[Dict]:
        """
        Map drug name to RxNorm CUI
        
        Args:
            drug_name: Drug name
            
        Returns:
            Dictionary with RxNorm CUI and name, or None
        """
        endpoint = f"rxcui.json?name={drug_name}"
        
        data = self.rxnorm_client.get(endpoint)
        
        if not data or "idGroup" not in data:
            return None
        
        cui_list = data["idGroup"].get("rxnormId", [])
        if not cui_list:
            return None
        
        cui = cui_list[0]
        
        return {
            "rxnorm_cui": cui,
            "drug_name": drug_name,
            "uri": f"https://identifiers.org/rxnorm:{cui}"
        }
    
    def gene_to_hgnc(self, gene_symbol: str) -> Optional[Dict]:
        """
        Map gene symbol to HGNC ID
        
        Args:
            gene_symbol: Gene symbol
            
        Returns:
            Dictionary with HGNC ID and info, or None
        """
        endpoint = f"fetch/symbol/{gene_symbol}"
        headers = {"Accept": "application/json"}
        
        data = self.hgnc_client.get(endpoint, headers=headers)
        
        if not data or "response" not in data:
            return None
        
        if data["response"].get("numFound", 0) == 0:
            return None
        
        doc = data["response"]["docs"][0]
        
        return {
            "hgnc_id": doc.get("hgnc_id"),
            "gene_symbol": gene_symbol,
            "gene_name": doc.get("name"),
            "ncbi_gene_id": doc.get("entrez_id"),
            "uri": f"https://identifiers.org/hgnc:{doc.get('hgnc_id')}"
        }
    
    def enrich_with_identifiers(self, data: Dict) -> Dict:
        """
        Enrich data with standardized identifiers
        
        Args:
            data: Data dictionary with drugs and genes
            
        Returns:
            Enriched data with identifier mappings
        """
        # Map drugs to RxNorm
        if "variants" in data:
            for variant in data["variants"]:
                if "pharmgkb" in variant and "drugs" in variant["pharmgkb"]:
                    for drug in variant["pharmgkb"]["drugs"]:
                        rxnorm = self.drug_to_rxnorm(drug["name"])
                        if rxnorm:
                            drug["rxnorm"] = rxnorm
        
        # Map gene to HGNC
        if "gene_symbol" in data:
            hgnc = self.gene_to_hgnc(data["gene_symbol"])
            if hgnc:
                data["hgnc"] = hgnc
        
        return data

