"""
Medication Enricher: Ensures all medications have SNOMED codes for substances and conditions
"""
from typing import Dict, List, Optional


class MedicationEnricher:
    """Enriches medications with SNOMED codes"""
    
    def __init__(self, dynamic_clinical_generator):
        """
        Initialize medication enricher
        
        Args:
            dynamic_clinical_generator: DynamicClinicalGenerator instance for SNOMED lookups
        """
        self.dynamic_clinical = dynamic_clinical_generator
    
    def enrich_medications(self, medications: List[Dict]) -> List[Dict]:
        """
        Enrich all medications with SNOMED codes
        
        Args:
            medications: List of medication dictionaries
            
        Returns:
            List of enriched medication dictionaries
        """
        enriched = []
        for medication in medications:
            enriched_med = self.enrich_single_medication(medication.copy())
            enriched.append(enriched_med)
        return enriched
    
    def enrich_single_medication(self, medication: Dict) -> Dict:
        """
        Enrich a single medication with SNOMED codes
        
        Args:
            medication: Medication dictionary
            
        Returns:
            Enriched medication dictionary
        """
        drug_name = medication.get("schema:name") or medication.get("rdfs:label") or ""
        
        # 1. Ensure drug substance has SNOMED code - try multiple strategies
        if not medication.get("snomed:code"):
            drug_snomed_code = self.dynamic_clinical._get_snomed_code_for_drug(drug_name)
            if not drug_snomed_code and drug_name:
                # Try lowercase variant
                drug_snomed_code = self.dynamic_clinical._get_snomed_code_for_drug(drug_name.lower())
            if not drug_snomed_code and drug_name:
                # Try capitalized variant
                drug_snomed_code = self.dynamic_clinical._get_snomed_code_for_drug(drug_name.title())
            if drug_snomed_code:
                medication["snomed:code"] = drug_snomed_code
                medication["snomed:uri"] = f"http://snomed.info/id/{drug_snomed_code}"
                print(f"    ✅ Found SNOMED code for drug: {drug_name} -> {drug_snomed_code}")
            else:
                print(f"    ⚠️  Could not find SNOMED code for drug: {drug_name}")
        
        # 2. Ensure treats_condition has valid SNOMED code (never null)
        treats_condition = medication.get("treats_condition")
        if treats_condition:
            # Fix null SNOMED codes
            condition_code = treats_condition.get("snomed:code")
            if not condition_code or str(condition_code) == "None" or str(condition_code).strip() == "":
                # Try to find SNOMED code for condition
                condition_label = treats_condition.get("rdfs:label") or medication.get("purpose") or medication.get("indication_name", "")
                if condition_label:
                    condition_result = self.dynamic_clinical._search_snomed_condition(condition_label)
                    if condition_result and condition_result.get("snomed:code"):
                        treats_condition["snomed:code"] = condition_result["snomed:code"]
                        treats_condition["@id"] = f"http://snomed.info/id/{condition_result['snomed:code']}"
                    else:
                        # Remove treats_condition if we can't find a code
                        del medication["treats_condition"]
        elif medication.get("purpose") or medication.get("indication_name"):
            # Add treats_condition if missing but we have purpose/indication
            condition_label = medication.get("purpose") or medication.get("indication_name", "")
            if condition_label:
                condition_result = self.dynamic_clinical._search_snomed_condition(condition_label)
                if condition_result and condition_result.get("snomed:code"):
                    medication["treats_condition"] = {
                        "snomed:code": condition_result["snomed:code"],
                        "rdfs:label": condition_label,
                        "@id": f"http://snomed.info/id/{condition_result['snomed:code']}"
                    }
                    print(f"    ✅ Added treats_condition for {drug_name}: {condition_label} -> {condition_result['snomed:code']}")
                else:
                    print(f"    ⚠️  Could not find SNOMED code for condition: {condition_label} (for drug {drug_name})")
        
        return medication

