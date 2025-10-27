"""
ClinVar Client
Queries ClinVar for variant clinical significance and pathogenicity
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from typing import Dict, Optional, List
from utils.api_client import APIClient
from utils.evidence_levels import EvidenceLevelInterpreter


class ClinVarClient:
    """Client for querying ClinVar via NCBI E-utilities"""
    
    def __init__(self, email: str, api_key: Optional[str] = None):
        """
        Initialize ClinVar client
        
        Args:
            email: Your email (required by NCBI)
            api_key: Optional NCBI API key for higher rate limits
        """
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        self.email = email
        self.api_key = api_key
        rate_limit = 10 if api_key else 3
        self.client = APIClient(self.base_url, rate_limit=rate_limit)
        self.evidence_interpreter = EvidenceLevelInterpreter()
    
    def search_variant_by_rsid(self, rsid: str) -> Optional[str]:
        """
        Search for a variant by rsID and get ClinVar ID
        
        Args:
            rsid: dbSNP rsID (e.g., rs1065852)
            
        Returns:
            ClinVar ID or None
        """
        endpoint = "esearch.fcgi"
        params = {
            "db": "clinvar",
            "term": rsid,
            "retmode": "json",
            "email": self.email
        }
        
        if self.api_key:
            params["api_key"] = self.api_key
        
        data = self.client.get(endpoint, params=params)
        
        if data and "esearchresult" in data:
            id_list = data["esearchresult"].get("idlist", [])
            if id_list:
                return id_list[0]
        
        return None
    
    def get_variant_details(self, clinvar_id: str) -> Optional[Dict]:
        """
        Get detailed ClinVar record
        
        Args:
            clinvar_id: ClinVar ID
            
        Returns:
            Dictionary with variant details or None
        """
        endpoint = "esummary.fcgi"
        params = {
            "db": "clinvar",
            "id": clinvar_id,
            "retmode": "json",
            "email": self.email
        }
        
        if self.api_key:
            params["api_key"] = self.api_key
        
        data = self.client.get(endpoint, params=params)
        
        if not data or "result" not in data:
            return None
        
        result = data["result"].get(clinvar_id, {})
        
        # Extract key information
        clin_sig = result.get("clinical_significance", {})
        star_rating = self._calculate_star_rating(clin_sig.get("review_status", ""))
        
        # Interpret star rating
        evidence_interpretation = {}
        if star_rating is not None:
            evidence_interpretation = self.evidence_interpreter.interpret_clinvar_stars(star_rating)
        
        return {
            "clinvar_id": clinvar_id,
            "clinical_significance": clin_sig.get("description"),
            "review_status": clin_sig.get("review_status"),
            "last_evaluated": clin_sig.get("last_evaluated"),
            "variation_type": result.get("obj_type"),
            "germline_classification": result.get("germline_classification", {}).get("description"),
            "phenotypes": self._extract_phenotypes(result),
            "star_rating": star_rating,
            "evidence_interpretation": evidence_interpretation
        }
    
    def _extract_phenotypes(self, result: Dict) -> List[str]:
        """Extract phenotype/disease names from ClinVar result"""
        phenotypes = []
        
        # Try multiple fields where phenotypes might be stored
        if "trait_set" in result:
            for trait in result["trait_set"]:
                if "trait_name" in trait:
                    phenotypes.append(trait["trait_name"])
        
        if "phenotype_list" in result:
            phenotypes.extend(result["phenotype_list"])
        
        return list(set(phenotypes))  # Remove duplicates
    
    def _calculate_star_rating(self, review_status: str) -> int:
        """
        Calculate star rating from review status
        
        ClinVar star rating system:
        0 stars: no assertion provided
        1 star: no assertion criteria provided
        2 stars: criteria provided, single submitter
        3 stars: criteria provided, multiple submitters, no conflicts
        4 stars: practice guideline, reviewed by expert panel
        """
        review_status_lower = review_status.lower()
        
        if "practice guideline" in review_status_lower or "expert panel" in review_status_lower:
            return 4
        elif "multiple submitters" in review_status_lower and "no conflict" in review_status_lower:
            return 3
        elif "criteria provided" in review_status_lower and "single submitter" in review_status_lower:
            return 2
        elif "criteria provided" in review_status_lower:
            return 2
        elif "no assertion" not in review_status_lower:
            return 1
        else:
            return 0
    
    def enrich_variant(self, variant: Dict) -> Dict:
        """
        Enrich variant with ClinVar data
        
        Args:
            variant: Variant dictionary with rsID
            
        Returns:
            Enriched variant dictionary
        """
        # Extract rsID from variant
        rsid = None
        for xref in variant.get("xrefs", []):
            if xref.get("name") == "dbSNP":
                rsid = xref.get("id")
                break
        
        if not rsid:
            return variant
        
        # Search ClinVar
        clinvar_id = self.search_variant_by_rsid(rsid)
        if not clinvar_id:
            return variant
        
        # Get details
        details = self.get_variant_details(clinvar_id)
        if not details:
            return variant
        
        # Add to variant
        variant["clinvar"] = details
        
        return variant

