"""
OpenFDA Client
Queries OpenFDA for drug labels and adverse events
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from typing import Dict, List, Optional
from utils.api_client import APIClient


class OpenFDAClient:
    """Client for querying OpenFDA API"""
    
    def __init__(self):
        """Initialize OpenFDA client"""
        self.base_url = "https://api.fda.gov"
        self.client = APIClient(self.base_url, rate_limit=10)
    
    def search_drug_label(self, drug_name: str) -> List[Dict]:
        """
        Search for drug labels with pharmacogenomic information
        
        Args:
            drug_name: Drug name
            
        Returns:
            List of drug label dictionaries
        """
        endpoint = "drug/label.json"
        
        # Try multiple search strategies in order of preference
        search_strategies = [
            # Strategy 1: Look for genetic/genomic terms (more common than "pharmacogenomics")
            f'openfda.generic_name:"{drug_name}" AND (genetic OR genomic OR genotype OR allele OR polymorphism)',
            # Strategy 2: Look for CYP enzyme mentions (common in PGx labels)
            f'openfda.generic_name:"{drug_name}" AND (CYP2D6 OR CYP2C19 OR CYP3A4 OR CYP2C9 OR cytochrome)',
            # Strategy 3: Look for metabolizer terms
            f'openfda.generic_name:"{drug_name}" AND (metabolizer OR metabolism)',
            # Strategy 4: Generic drug search
            f'openfda.generic_name:"{drug_name}"',
            # Strategy 5: Try brand name search if generic fails
            f'openfda.brand_name:"{drug_name}"'
        ]
        
        for i, search_query in enumerate(search_strategies):
            params = {
                "search": search_query,
                "limit": 5
            }
            
            data = self.client.get(endpoint, params=params, use_cache=True)
            
            if data and "results" in data and data["results"]:
                # Found results, check if they contain pharmacogenomic content
                results = data["results"]
                pgx_results = self._filter_pharmacogenomic_content(results, drug_name)
                
                if pgx_results or i >= 3:  # Accept any results from strategy 4+ (generic searches)
                    return pgx_results if pgx_results else results
        
        return []
    
    def _filter_pharmacogenomic_content(self, results: List[Dict], drug_name: str) -> List[Dict]:
        """
        Filter drug labels for pharmacogenomic content
        
        Args:
            results: List of drug label results
            drug_name: Drug name for context
            
        Returns:
            List of results containing pharmacogenomic information
        """
        pgx_keywords = [
            'genetic', 'genomic', 'genotype', 'allele', 'polymorphism',
            'CYP2D6', 'CYP2C19', 'CYP3A4', 'CYP2C9', 'cytochrome',
            'metabolizer', 'poor metabolizer', 'extensive metabolizer',
            'pharmacogenomic', 'pharmacogenetic', 'biomarker',
            'genetic testing', 'genotyping'
        ]
        
        pgx_results = []
        
        for result in results:
            # Check various fields for pharmacogenomic content
            text_fields = []
            
            # Add relevant text fields
            if 'warnings' in result:
                text_fields.extend(result['warnings'])
            if 'boxed_warning' in result:
                text_fields.extend(result['boxed_warning'])
            if 'dosage_and_administration' in result:
                text_fields.extend(result['dosage_and_administration'])
            if 'contraindications' in result:
                text_fields.extend(result['contraindications'])
            if 'precautions' in result:
                text_fields.extend(result['precautions'])
            if 'adverse_reactions' in result:
                text_fields.extend(result['adverse_reactions'])
            
            # Check if any text contains pharmacogenomic keywords
            has_pgx_content = False
            for text in text_fields:
                if isinstance(text, str):
                    text_lower = text.lower()
                    if any(keyword.lower() in text_lower for keyword in pgx_keywords):
                        has_pgx_content = True
                        break
            
            if has_pgx_content:
                pgx_results.append(result)
        
        return pgx_results
    
    def extract_pgx_info(self, drug_name: str) -> Optional[Dict]:
        """
        Extract pharmacogenomic information from drug labels
        
        Args:
            drug_name: Drug name
            
        Returns:
            Dictionary with PGx info or None
        """
        labels = self.search_drug_label(drug_name)
        
        if not labels:
            return None
        
        # Process first label
        label = labels[0]
        
        pgx_info = {
            "drug_name": drug_name,
            "brand_names": label.get("openfda", {}).get("brand_name", []),
            "generic_names": label.get("openfda", {}).get("generic_name", []),
            "warnings": self._extract_field(label, "warnings"),
            "boxed_warning": self._extract_field(label, "boxed_warning"),
            "adverse_reactions": self._extract_field(label, "adverse_reactions"),
            "dosage_and_administration": self._extract_field(label, "dosage_and_administration"),
            "clinical_pharmacology": self._extract_field(label, "clinical_pharmacology")
        }
        
        return pgx_info
    
    def _extract_field(self, label: Dict, field_name: str) -> Optional[str]:
        """Extract field from label, handling list or string"""
        value = label.get(field_name)
        
        if not value:
            return None
        
        if isinstance(value, list):
            return " ".join(value)
        
        return str(value)
    
    def enrich_drugs_with_fda_data(self, variants: List[Dict]) -> List[Dict]:
        """
        Enrich drug information with FDA label data
        
        Args:
            variants: List of variants with drug info
            
        Returns:
            Enriched variants
        """
        processed_drugs = set()
        
        for variant in variants:
            if "pharmgkb" not in variant or "drugs" not in variant["pharmgkb"]:
                continue
            
            for drug in variant["pharmgkb"]["drugs"]:
                drug_name = drug["name"]
                
                # Skip if already processed
                if drug_name in processed_drugs:
                    continue
                
                processed_drugs.add(drug_name)
                
                # Get FDA data
                print(f"   Querying OpenFDA for {drug_name}...")
                fda_info = self.extract_pgx_info(drug_name)
                
                if fda_info:
                    drug["fda_label"] = fda_info
                    print(f"     ✓ Found FDA label data")
                else:
                    print(f"     - No FDA label found (common for older/specialty drugs)")
        
        return variants

