"""
ChEMBL Client
Queries ChEMBL for drug bioactivity, target interactions, and mechanism of action data
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from typing import Dict, List, Optional
from utils.api_client import APIClient


class ChEMBLClient:
    """Client for querying ChEMBL Web Services API"""
    
    def __init__(self):
        """Initialize ChEMBL client"""
        self.base_url = "https://www.ebi.ac.uk/chembl/api/data"
        # ChEMBL allows up to 20 requests per second
        self.client = APIClient(self.base_url, rate_limit=15)
    
    def search_compound_by_name(self, drug_name: str) -> Optional[Dict]:
        """
        Search for a compound by name in ChEMBL
        
        Args:
            drug_name: Drug name to search for
            
        Returns:
            ChEMBL compound data or None
        """
        endpoint = "molecule.json"
        params = {
            "molecule_synonyms__molecule_synonym__iexact": drug_name,
            "limit": 5
        }
        
        data = self.client.get(endpoint, params=params)
        
        if data and "molecules" in data and data["molecules"]:
            # Return the first match
            return data["molecules"][0]
        
        # Try alternative search with contains
        params = {
            "molecule_synonyms__molecule_synonym__icontains": drug_name,
            "limit": 5
        }
        
        data = self.client.get(endpoint, params=params)
        
        if data and "molecules" in data and data["molecules"]:
            return data["molecules"][0]
        
        return None
    
    def get_compound_bioactivities(self, chembl_id: str, target_gene: str = None) -> List[Dict]:
        """
        Get bioactivity data for a compound
        
        Args:
            chembl_id: ChEMBL compound ID
            target_gene: Optional gene symbol to filter targets (e.g., CYP2C19)
            
        Returns:
            List of bioactivity records
        """
        endpoint = "activity.json"
        params = {
            "molecule_chembl_id": chembl_id,
            "limit": 50
        }
        
        # Add target filter if specified
        if target_gene:
            params["target_organism"] = "Homo sapiens"
            # Try to filter by gene name in target
            params["target_pref_name__icontains"] = target_gene
        
        data = self.client.get(endpoint, params=params)
        
        if data and "activities" in data:
            return data["activities"]
        
        return []
    
    def get_compound_targets(self, chembl_id: str) -> List[Dict]:
        """
        Get target information for a compound
        
        Args:
            chembl_id: ChEMBL compound ID
            
        Returns:
            List of target dictionaries
        """
        # Get bioactivities first to find targets
        bioactivities = self.get_compound_bioactivities(chembl_id)
        
        targets = {}
        for activity in bioactivities:
            target_chembl_id = activity.get("target_chembl_id")
            if target_chembl_id and target_chembl_id not in targets:
                target_info = self.get_target_details(target_chembl_id)
                if target_info:
                    targets[target_chembl_id] = target_info
        
        return list(targets.values())
    
    def get_target_details(self, target_chembl_id: str) -> Optional[Dict]:
        """
        Get detailed information about a target
        
        Args:
            target_chembl_id: ChEMBL target ID
            
        Returns:
            Target details or None
        """
        endpoint = f"target/{target_chembl_id}.json"
        
        data = self.client.get(endpoint)
        
        if data:
            return data
        
        return None
    
    def get_pharmacogenomic_bioactivities(self, chembl_id: str) -> Dict:
        """
        Get pharmacogenomics-relevant bioactivity data
        
        Args:
            chembl_id: ChEMBL compound ID
            
        Returns:
            Dictionary with PGx-relevant bioactivity data
        """
        # Focus on CYP enzymes and other PGx-relevant targets
        pgx_targets = [
            "CYP2C19", "CYP2D6", "CYP3A4", "CYP2C9", "CYP1A2",
            "DPYD", "TPMT", "UGT1A1", "SLCO1B1", "ABCB1"
        ]
        
        pgx_data = {
            "chembl_id": chembl_id,
            "pgx_bioactivities": [],
            "mechanism_of_action": [],
            "target_interactions": []
        }
        
        # Get all bioactivities
        all_bioactivities = self.get_compound_bioactivities(chembl_id)
        
        for activity in all_bioactivities:
            target_name = activity.get("target_pref_name", "")
            
            # Check if this is a PGx-relevant target
            is_pgx_target = any(pgx_gene in target_name.upper() for pgx_gene in pgx_targets)
            
            if is_pgx_target:
                # Get target details including ChEMBL target ID
                target_chembl_id = activity.get("target_chembl_id")
                target_details = None
                if target_chembl_id:
                    target_details = self.get_target_details(target_chembl_id)
                
                bioactivity_record = {
                    "target_chembl_id": target_chembl_id,
                    "target_name": target_name,
                    "target_type": activity.get("target_type"),
                    "target_organism": activity.get("target_organism"),
                    "target_pref_name": activity.get("target_pref_name"),
                    "assay_type": activity.get("assay_type"),
                    "bioactivity_type": activity.get("standard_type"),
                    "value": activity.get("standard_value"),
                    "units": activity.get("standard_units"),
                    "relation": activity.get("standard_relation"),
                    "assay_description": activity.get("assay_description", "")[:200],
                    "target_gene_symbol": target_details.get("target_components", [{}])[0].get("target_component_synonym", "") if target_details and target_details.get("target_components") else None
                }
                
                pgx_data["pgx_bioactivities"].append(bioactivity_record)
        
        # Get mechanism of action
        pgx_data["mechanism_of_action"] = self.get_mechanism_of_action(chembl_id)
        
        return pgx_data
    
    def get_mechanism_of_action(self, chembl_id: str) -> List[Dict]:
        """
        Get mechanism of action data for a compound
        
        Args:
            chembl_id: ChEMBL compound ID
            
        Returns:
            List of mechanism of action records
        """
        endpoint = "mechanism.json"
        params = {
            "molecule_chembl_id": chembl_id,
            "limit": 20
        }
        
        data = self.client.get(endpoint, params=params)
        
        if data and "mechanisms" in data:
            mechanisms = []
            for mech in data["mechanisms"]:
                mechanism_record = {
                    "mechanism_of_action": mech.get("mechanism_of_action"),
                    "target_chembl_id": mech.get("target_chembl_id"),
                    "target_name": mech.get("target_pref_name"),
                    "action_type": mech.get("action_type"),
                    "mechanism_comment": mech.get("mechanism_comment")
                }
                mechanisms.append(mechanism_record)
            return mechanisms
        
        return []
    
    def enrich_drug_with_chembl_data(self, drug_name: str, gene_symbol: str = None) -> Optional[Dict]:
        """
        Enrich a drug with comprehensive ChEMBL data
        
        Args:
            drug_name: Drug name
            gene_symbol: Optional gene symbol for focused search
            
        Returns:
            Dictionary with ChEMBL enrichment data
        """
        # Search for the compound
        compound = self.search_compound_by_name(drug_name)
        
        if not compound:
            return None
        
        chembl_id = compound.get("molecule_chembl_id")
        if not chembl_id:
            return None
        
        # Get comprehensive data including ADMET properties
        molecule_props = compound.get("molecule_properties") or {}
        enrichment_data = {
            "drug_name": drug_name,
            "chembl_id": chembl_id,
            "compound_info": {
                "pref_name": compound.get("pref_name"),
                "molecule_type": compound.get("molecule_type"),
                "max_phase": compound.get("max_phase"),
                "therapeutic_flag": compound.get("therapeutic_flag"),
                "molecular_weight": molecule_props.get("mw_freebase") if isinstance(molecule_props, dict) else None,
                "alogp": molecule_props.get("alogp") if isinstance(molecule_props, dict) else None,
                "hbd": molecule_props.get("hbd") if isinstance(molecule_props, dict) else None,  # Hydrogen bond donors (ADMET)
                "hba": molecule_props.get("hba") if isinstance(molecule_props, dict) else None,  # Hydrogen bond acceptors (ADMET)
                "psa": molecule_props.get("psa") if isinstance(molecule_props, dict) else None,  # Polar surface area (ADMET)
                "rtb": molecule_props.get("rtb") if isinstance(molecule_props, dict) else None,  # Rotatable bonds (ADMET)
                "num_ro5_violations": molecule_props.get("num_ro5_violations") if isinstance(molecule_props, dict) else None,  # Lipinski's Rule of Five violations
                "structure_type": compound.get("structure_type")
            },
            "pgx_bioactivities": [],
            "mechanism_of_action": [],
            "target_interactions": []
        }
        
        # Get pharmacogenomic bioactivities
        pgx_data = self.get_pharmacogenomic_bioactivities(chembl_id)
        enrichment_data.update(pgx_data)
        
        # Get target interactions
        targets = self.get_compound_targets(chembl_id)
        enrichment_data["target_interactions"] = targets[:10]  # Limit to top 10
        
        return enrichment_data
    
    def enrich_drugs_with_chembl_data(self, variants: List[Dict]) -> List[Dict]:
        """
        Enrich all drugs in variants with ChEMBL data
        
        Args:
            variants: List of variant dictionaries with drug information
            
        Returns:
            Enriched variants with ChEMBL data
        """
        print("   Enriching drugs with ChEMBL bioactivity data...")
        
        for variant in variants:
            if "pharmgkb" in variant and "drugs" in variant["pharmgkb"]:
                chembl_enriched_drugs = []
                
                for drug in variant["pharmgkb"]["drugs"]:
                    drug_name = drug.get("name", "")
                    if drug_name:
                        print(f"     Querying ChEMBL for {drug_name}...")
                        
                        # Get gene symbol from variant context if available
                        gene_symbol = None
                        if "gene_symbol" in variant:
                            gene_symbol = variant["gene_symbol"]
                        
                        chembl_data = self.enrich_drug_with_chembl_data(drug_name, gene_symbol)
                        
                        if chembl_data:
                            drug["chembl_data"] = chembl_data
                            print(f"       [OK] Found ChEMBL data: {chembl_data['chembl_id']}")
                        else:
                            print(f"       [SKIP] No ChEMBL data found for {drug_name}")
                        
                        chembl_enriched_drugs.append(drug)
                
                variant["pharmgkb"]["drugs"] = chembl_enriched_drugs
        
        return variants


if __name__ == "__main__":
    # Test the ChEMBL client
    client = ChEMBLClient()
    
    # Test with a known PGx drug
    test_drugs = ["clopidogrel", "warfarin", "omeprazole"]
    
    for drug in test_drugs:
        print(f"\nTesting {drug}:")
        result = client.enrich_drug_with_chembl_data(drug, "CYP2C19")
        if result:
            print(f"  ChEMBL ID: {result['chembl_id']}")
            print(f"  PGx bioactivities: {len(result['pgx_bioactivities'])}")
            print(f"  Mechanisms: {len(result['mechanism_of_action'])}")
        else:
            print(f"  No data found")
