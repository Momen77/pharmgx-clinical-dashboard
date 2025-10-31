"""
Dynamic Clinical Data Generator
Queries SNOMED CT and drug APIs dynamically to generate patient conditions and medications
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import random
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from utils.api_client import APIClient


class DynamicClinicalGenerator:
    """Dynamically generates conditions and medications from APIs"""
    
    def __init__(self, bioportal_api_key: str = None):
        """
        Initialize dynamic clinical generator
        
        Args:
            bioportal_api_key: BioPortal API key for SNOMED CT queries
        """
        self.bioportal_api_key = bioportal_api_key
        self.bioportal_base = "https://data.bioontology.org"
        PharmGKBClient = __import__('phase2_clinical.pharmgkb_client', fromlist=['PharmGKBClient']).PharmGKBClient
        ChEMBLClient = __import__('phase3_context.chembl_client', fromlist=['ChEMBLClient']).ChEMBLClient
        
        self.bioportal_client = APIClient(self.bioportal_base, rate_limit=10)
        self.rxnorm_client = APIClient("https://rxnav.nlm.nih.gov/REST", rate_limit=10)
        self.clinical_tables_client = APIClient("https://clinicaltables.nlm.nih.gov/api", rate_limit=10)
        self.chembl_client = ChEMBLClient()
        self.pharmgkb_client = PharmGKBClient()
        
        if bioportal_api_key:
            self.bioportal_headers = {"Authorization": f"apikey token={bioportal_api_key}"}
        else:
            self.bioportal_headers = {}
    
    def get_conditions_by_age_lifestyle(self, age: int, lifestyle_factors: List[Dict]) -> List[Dict]:
        """
        Dynamically query SNOMED CT for conditions based on age and lifestyle

        Args:
            age: Patient age
            lifestyle_factors: List of lifestyle factors (smoking, alcohol, etc.)

        Returns:
            List of condition dictionaries with SNOMED CT codes
        """
        conditions = []

        # Define age-based condition search terms
        age_queries = self._get_age_based_queries(age)

        # Define lifestyle-based condition queries
        lifestyle_queries = self._get_lifestyle_queries(lifestyle_factors)

        # Combine and query SNOMED CT
        all_queries = age_queries + lifestyle_queries

        # Try ALL queries (not probabilistic) to maximize API data retrieval
        print(f"  🔍 Attempting to query {len(all_queries)} potential conditions from APIs...")
        for query_term, probability in all_queries:
            # Increased probability threshold to get more conditions from APIs
            if random.random() < min(probability * 2.5, 0.95):  # Boost probabilities, cap at 95%
                condition = self._search_snomed_condition(query_term)
                if condition:
                    conditions.append(condition)
                    print(f"    ✅ Found via API: {condition.get('rdfs:label')}")

        # Add random common conditions with boosted probabilities
        common_conditions = self._get_common_conditions_by_age(age)
        for condition_query, prob in common_conditions:
            if random.random() < min(prob * 2.0, 0.90):  # Boost common condition probabilities
                condition = self._search_snomed_condition(condition_query)
                if condition:
                    conditions.append(condition)
                    print(f"    ✅ Found via API: {condition.get('rdfs:label')}")

        # Remove duplicates
        seen_codes = set()
        unique_conditions = []
        for cond in conditions:
            code = cond.get("snomed:code")
            if code and code not in seen_codes:
                seen_codes.add(code)
                unique_conditions.append(cond)

        print(f"  📊 Total conditions from APIs: {len(unique_conditions)}")

        # FALLBACK: If insufficient conditions (< 2), use static data as LAST RESORT
        if len(unique_conditions) < 2:
            print(f"  ⚠️  Only {len(unique_conditions)} conditions from APIs - using static fallback for comprehensive data")
            unique_conditions = self._get_static_conditions_by_age(age, lifestyle_factors)

        return unique_conditions[:5]  # Limit to 5 conditions max
    
    def _get_age_based_queries(self, age: int) -> List[tuple]:
        """Get condition search queries based on age"""
        queries = []
        
        if age >= 60:
            queries.extend([
                ("heart disease", 0.20),
                ("diabetes type 2", 0.18),
                ("hypertension", 0.30),
                ("osteoporosis", 0.12),
                ("osteoarthritis", 0.15)
            ])
        elif age >= 40:
            queries.extend([
                ("diabetes type 2", 0.15),
                ("hypertension", 0.25),
                ("asthma", 0.10),
                ("depression", 0.12),
                ("GERD", 0.15)
            ])
        else:
            queries.extend([
                ("asthma", 0.12),
                ("allergy", 0.10),
                ("anxiety", 0.10),
                ("depression", 0.10)
            ])
        
        return queries
    
    def _get_lifestyle_queries(self, lifestyle_factors: List[Dict]) -> List[tuple]:
        """Get condition queries based on lifestyle factors"""
        queries = []
        
        for factor in lifestyle_factors:
            factor_type = factor.get("factor_type", "")
            status = factor.get("status", "")
            
            if factor_type == "smoking" and status == "current":
                queries.extend([
                    ("COPD", 0.25),
                    ("lung disease", 0.15),
                    ("cardiovascular disease", 0.20)
                ])
            elif factor_type == "alcohol" and status in ["regular", "heavy"]:
                queries.extend([
                    ("liver disease", 0.10),
                    ("hypertension", 0.15)
                ])
        
        return queries
    
    def _get_common_conditions_by_age(self, age: int) -> List[tuple]:
        """Get common conditions with age-adjusted probabilities"""
        # Base probabilities for common conditions
        base_conditions = [
            ("hypertension", 0.25),
            ("dyslipidemia", 0.20),
            ("diabetes", 0.15),
            ("asthma", 0.12),
            ("depression", 0.12),
            ("GERD", 0.15),
            ("osteoarthritis", 0.12),
            ("hypothyroidism", 0.10)
        ]
        
        # Adjust probabilities based on age
        adjusted = []
        for term, base_prob in base_conditions:
            if "diabetes" in term or "hypertension" in term:
                # More common in older ages
                prob = base_prob * (1 + (age - 40) / 100) if age > 40 else base_prob * 0.5
            elif "asthma" in term or "allergy" in term:
                # More common in younger ages
                prob = base_prob * (1.5 if age < 40 else 0.7)
            else:
                prob = base_prob
            
            adjusted.append((term, min(prob, 0.5)))  # Cap at 50%
        
        return adjusted
    
    def _search_snomed_condition(self, search_term: str) -> Optional[Dict]:
        """
        Search SNOMED CT for a condition
        
        Args:
            search_term: Search term (e.g., "diabetes type 2")
            
        Returns:
            Condition dictionary with SNOMED CT code, or None
        """
        if not self.bioportal_api_key:
            # Fallback: Use Clinical Tables API (free, no key needed)
            return self._search_clinical_tables(search_term)
        
        # Use BioPortal API
        endpoint = "search"
        params = {
            "q": search_term,
            "ontologies": "SNOMEDCT",
            "require_exact_match": "false",
            "page_size": 5
        }
        
        data = self.bioportal_client.get(endpoint, params=params, headers=self.bioportal_headers)
        
        if not data or "collection" not in data:
            return None
        
        results = data["collection"]
        if not results:
            return None
        
        # Find best match (prefer disorders/diseases)
        best_match = None
        for result in results:
            pref_label = result.get("prefLabel", "").lower()
            if any(term in pref_label for term in ["disorder", "disease", "condition"]):
                best_match = result
                break
        
        if not best_match:
            best_match = results[0]
        
        # Extract SNOMED code
        snomed_uri = best_match.get("@id", "")
        snomed_code = snomed_uri.split("/")[-1] if snomed_uri else None
        
        if not snomed_code:
            return None
        
        return {
            "@id": f"http://snomed.info/id/{snomed_code}",
            "@type": "sdisco:Condition",
            "snomed:code": snomed_code,
            "rdfs:label": best_match.get("prefLabel", search_term),
            "skos:prefLabel": best_match.get("prefLabel", search_term),
            "skos:definition": best_match.get("definition", [""])[0] if best_match.get("definition") else "",
            "search_term": search_term
        }
    
    def _search_clinical_tables(self, search_term: str) -> Optional[Dict]:
        """
        Fallback: Search Clinical Tables API (free, no API key needed)
        
        Args:
            search_term: Search term
            
        Returns:
            Condition dictionary, or None
        """
        endpoint = "conditions/v3/search"
        params = {
            "terms": search_term,
            "maxList": 5
        }
        
        data = self.clinical_tables_client.get(endpoint, params=params)
        
        if not data or len(data) < 2:
            return None
        
        # Clinical Tables returns: [0, count, [ids], [labels]]
        labels = data[3] if len(data) > 3 else []
        ids = data[2] if len(data) > 2 else []
        
        if not labels or not ids:
            return None
        
        # Use first result
        snomed_code = ids[0]
        label = labels[0]
        
        return {
            "@id": f"http://snomed.info/id/{snomed_code}",
            "@type": "sdisco:Condition",
            "snomed:code": snomed_code,
            "rdfs:label": label,
            "skos:prefLabel": label,
            "skos:definition": "",
            "search_term": search_term
        }
    
    def get_drugs_for_condition(self, snomed_code: str, condition_label: str) -> List[Dict]:
        """
        Dynamically query drug APIs for medications treating a condition
        
        Args:
            snomed_code: SNOMED CT code for the condition
            condition_label: Human-readable condition name
            
        Returns:
            List of medication dictionaries
        """
        medications = []
        
        # Strategy 1: Use known condition-drug mappings FIRST (most reliable)
        # This ensures we always have evidence-based medications for common conditions
        print(f"    🔍 Getting evidence-based drugs for: {condition_label}")
        known_drugs = self._get_known_drugs_for_condition(snomed_code, condition_label)
        medications.extend(known_drugs)
        
        # Strategy 2: Query ChEMBL for drugs by indication (supplementary)
        print(f"    🔍 Searching ChEMBL for drugs treating: {condition_label}")
        chembl_drugs = self._search_chembl_by_indication(condition_label, snomed_code)
        medications.extend(chembl_drugs)
        
        # Strategy 3: Query RxNorm for drugs (fallback)
        print(f"    🔍 Searching RxNorm for drugs treating: {condition_label}")
        rxnorm_drugs = self._search_rxnorm_by_indication(condition_label)
        medications.extend(rxnorm_drugs)
        
        # Remove duplicates
        seen_ids = set()
        unique_meds = []
        for med in medications:
            drugbank_id = med.get("drugbank:id", "")
            rxnorm_cui = med.get("rxnorm", {}).get("rxnorm_cui") if isinstance(med.get("rxnorm"), dict) else None
            med_id = drugbank_id or f"rxnorm_{rxnorm_cui}" or med.get("schema:name", "")
            
            if med_id and med_id not in seen_ids:
                seen_ids.add(med_id)
                unique_meds.append(med)
        
        # Select medications based on condition complexity
        # Some conditions may need 1 drug, others may need 2-3 (e.g., combination therapy)
        num_drugs_needed = self._determine_drug_count_needed(condition_label, snomed_code)
        
        if len(unique_meds) >= num_drugs_needed:
            # Priority: Evidence-based > ChEMBL > RxNorm (evidence-based is most reliable)
            source_priority = ["evidence_based", "chembl", "rxnorm"]
            
            selected = []
            for source in source_priority:
                source_meds = [m for m in unique_meds if m.get("source") == source and m not in selected]
                if source_meds and len(selected) < num_drugs_needed:
                    needed = num_drugs_needed - len(selected)
                    selected.extend(random.sample(source_meds, min(needed, len(source_meds))))
            
            # Fill remaining slots from any source
            if len(selected) < num_drugs_needed:
                remaining = [m for m in unique_meds if m not in selected]
                if remaining:
                    needed = num_drugs_needed - len(selected)
                    selected.extend(random.sample(remaining, min(needed, len(remaining))))
            
            return selected[:num_drugs_needed]

        # FALLBACK: If no medications found (all APIs failed), use static mapping
        if not unique_meds:
            print(f"    ⚠️  No drugs found via APIs, using static fallback for: {condition_label}")
            static_meds = self._get_static_medications_for_conditions([{
                "snomed:code": snomed_code,
                "rdfs:label": condition_label
            }])
            return static_meds

        return unique_meds
    
    def _determine_drug_count_needed(self, condition_label: str, snomed_code: str) -> int:
        """
        Determine how many drugs are typically needed for a condition
        Some conditions require combination therapy (2-3 drugs)
        """
        condition_lower = condition_label.lower()
        
        # Conditions that typically need multiple drugs (combination therapy)
        multi_drug_conditions = {
            "diabetes": 2,  # Metformin + Insulin or Metformin + other
            "hypertension": 2,  # Often requires ACE inhibitor + diuretic or combo
            "depression": 1,  # Usually monotherapy
            "anxiety": 1,  # Usually monotherapy
            "asthma": 2,  # Controller + rescue inhaler
            "copd": 2,  # Multiple bronchodilators
            "gerd": 1,  # Usually PPI alone
            "osteoarthritis": 1,  # Usually one NSAID
            "hypothyroidism": 1  # Usually levothyroxine alone
        }
        
        for key, count in multi_drug_conditions.items():
            if key in condition_lower:
                return count
        
        # Default: 1-2 drugs (some variability)
        return random.choice([1, 2])
    
    def _search_chembl_by_indication(self, condition_label: str, snomed_code: str) -> List[Dict]:
        """
        Search ChEMBL for drugs by indication
        
        Args:
            condition_label: Condition name
            snomed_code: SNOMED CT code
            
        Returns:
            List of medication dictionaries
        """
        medications = []
        
        try:
            # ChEMBL API endpoint for drug indications
            endpoint = "drug_indication.json"
            
            # Search by indication name - use more specific terms based on condition
            search_term = self._get_better_search_term(condition_label)
            params = {
                "indication_name__icontains": search_term,
                "limit": 20  # Get more results to filter better
            }
            
            data = self.chembl_client.client.get(endpoint, params=params)
            
            if data and "drug_indications" in data:
                # Collect all indications with metadata for ranking
                indication_candidates = []
                seen_chembl_ids = set()
                
                for indication in data["drug_indications"][:20]:  # Get more for better selection
                    molecule_chembl_id = indication.get("molecule_chembl_id")
                    
                    if not molecule_chembl_id or molecule_chembl_id in seen_chembl_ids:
                        continue
                    
                    seen_chembl_ids.add(molecule_chembl_id)
                    
                    # Get molecule details
                    molecule_data = self._get_chembl_molecule(molecule_chembl_id)
                    if not molecule_data:
                        continue
                    
                    molecule_name = molecule_data.get("pref_name") or ""
                    if not molecule_name and molecule_data.get("molecule_synonyms"):
                        molecule_name = molecule_data["molecule_synonyms"][0].get("molecule_synonym", "")
                    
                    if not molecule_name:
                        continue
                    
                    # Calculate relevance score
                    max_phase = indication.get("max_phase_for_ind", "0")
                    try:
                        phase_float = float(max_phase) if max_phase else 0.0
                    except:
                        phase_float = 0.0
                    
                    # Rank by: Phase 4 (approved) > Phase 3 > Phase 2 > Phase 1
                    # Also check if drug has approved status
                    max_phase_overall = molecule_data.get("max_phase", 0)
                    try:
                        overall_phase = float(max_phase_overall) if max_phase_overall else 0.0
                    except:
                        overall_phase = 0.0
                    
                    # Higher score = more relevant
                    # Phase 4 drugs get highest priority, then phase 3, etc.
                    relevance_score = phase_float * 10 + overall_phase
                    
                    # Check if it's an FDA-approved drug (first_approval exists)
                    first_approval = molecule_data.get("first_approval", "")
                    if first_approval:
                        relevance_score += 100  # Big boost for approved drugs
                    
                    # Check for "withdrawn" status - penalize
                    withdrawn_flag = molecule_data.get("withdrawn_flag", False)
                    if withdrawn_flag:
                        relevance_score -= 50
                    
                    indication_candidates.append({
                        "indication": indication,
                        "molecule_data": molecule_data,
                        "molecule_name": molecule_name,
                        "molecule_chembl_id": molecule_chembl_id,
                        "relevance_score": relevance_score,
                        "max_phase": phase_float
                    })
                
                # Sort by relevance score (highest first)
                indication_candidates.sort(key=lambda x: x["relevance_score"], reverse=True)
                
                # Process top 5 most relevant drugs
                for candidate in indication_candidates[:5]:
                    indication = candidate["indication"]
                    molecule_data = candidate["molecule_data"]
                    molecule_name = candidate["molecule_name"]
                    molecule_chembl_id = candidate["molecule_chembl_id"]
                    
                    # Try to get RxNorm for standardization
                    rxnorm_info = self._get_rxnorm_for_drug(molecule_name)
                    
                    # Get protocol information from ChEMBL
                    protocol_info = self._get_chembl_protocol(molecule_chembl_id, indication)
                    
                    medication = {
                        "@id": f"https://www.ebi.ac.uk/chembl/compound_report_card/{molecule_chembl_id}",
                        "@type": "sdisco:Medication",
                        "chembl_id": molecule_chembl_id,
                        "schema:name": molecule_name,
                        "rdfs:label": molecule_name,
                        "schema:dosageForm": "tablet",
                        "schema:doseValue": self._estimate_dose(molecule_name),
                        "schema:doseUnit": "mg",
                        "schema:frequency": "Once daily",
                        "source": "chembl",
                        "indication_name": indication.get("indication_name", condition_label),
                        "max_phase_for_ind": indication.get("max_phase_for_ind", ""),
                        "max_phase_overall": molecule_data.get("max_phase", ""),
                        "first_approval": molecule_data.get("first_approval", ""),
                        "relevance_score": candidate["relevance_score"],
                        "protocol": protocol_info
                    }
                    
                    if rxnorm_info:
                        medication["rxnorm"] = rxnorm_info
                    
                    # Add SNOMED CT code for medication (substance)
                    snomed_code = self._get_snomed_code_for_drug(molecule_name)
                    if snomed_code:
                        medication["snomed:code"] = snomed_code
                        medication["snomed:uri"] = f"http://snomed.info/id/{snomed_code}"
                    
                    medications.append(medication)
        
        except Exception as e:
            print(f"      ⚠️ ChEMBL search failed: {e}")
        
        return medications
    
    def _get_chembl_molecule(self, chembl_id: str) -> Optional[Dict]:
        """Get ChEMBL molecule details"""
        try:
            endpoint = f"molecule/{chembl_id}.json"
            data = self.chembl_client.client.get(endpoint)
            return data if data else None
        except:
            return None
    
    def _get_chembl_protocol(self, chembl_id: str, indication: Dict) -> Dict:
        """
        Get treatment protocol information from ChEMBL indication data
        
        Args:
            chembl_id: ChEMBL molecule ID
            indication: ChEMBL indication record
            
        Returns:
            Protocol dictionary with treatment guidelines
        """
        protocol = {
            "treatment_line": "",
            "clinical_phase": indication.get("max_phase_for_ind", ""),
            "guideline": "",
            "combination_therapy": False
        }
        
        # Determine treatment line based on phase
        max_phase = indication.get("max_phase_for_ind", "")
        if max_phase == "4":
            protocol["treatment_line"] = "FDA-approved - First-line or standard treatment"
            protocol["guideline"] = "Approved by FDA for this indication"
        elif max_phase == "3":
            protocol["treatment_line"] = "Phase 3 - Investigational"
            protocol["guideline"] = "Currently in Phase 3 clinical trials"
        elif max_phase == "2":
            protocol["treatment_line"] = "Phase 2 - Experimental"
            protocol["guideline"] = "Currently in Phase 2 clinical trials"
        else:
            protocol["treatment_line"] = "Standard treatment option"
            protocol["guideline"] = "Used clinically for this indication"
        
        # Add indication-specific protocols
        indication_name = indication.get("indication_name", "").lower()
        
        if "depression" in indication_name or "depressive" in indication_name:
            protocol["guideline"] = "SSRI first-line treatment for major depressive disorder according to clinical guidelines"
            protocol["treatment_line"] = "First-line (SSRI therapy)"
        elif "anxiety" in indication_name:
            protocol["guideline"] = "SSRI or benzodiazepine for anxiety disorders - SSRIs preferred for long-term management"
            protocol["treatment_line"] = "First-line (SSRI) or Second-line (Benzodiazepine)"
        elif "diabetes" in indication_name:
            protocol["guideline"] = "Metformin is first-line for type 2 diabetes. Add insulin if glycemic control inadequate."
            protocol["treatment_line"] = "First-line (Metformin) or Second-line (Insulin)"
            protocol["combination_therapy"] = True
        elif "hypertension" in indication_name:
            protocol["guideline"] = "ACE inhibitor or ARB first-line. May combine with diuretic or calcium channel blocker."
            protocol["treatment_line"] = "First-line (ACE/ARB) - May require combination therapy"
            protocol["combination_therapy"] = True
        elif "asthma" in indication_name:
            protocol["guideline"] = "Inhaled corticosteroid (controller) + Short-acting beta-agonist (rescue)"
            protocol["treatment_line"] = "Controller + Rescue inhaler"
            protocol["combination_therapy"] = True
        
        return protocol
    
    def _search_rxnorm_by_indication(self, condition: str) -> List[Dict]:
        """
        Search RxNorm for drugs - uses condition-to-drug-class mapping
        
        Args:
            condition: Condition name
            
        Returns:
            List of medication dictionaries
        """
        medications = []
        
        try:
            # Map conditions to common drug classes
            condition_lower = condition.lower()
            drug_classes = []
            
            if "depress" in condition_lower:
                drug_classes = ["sertraline", "escitalopram", "citalopram", "fluoxetine"]
            elif "anxiety" in condition_lower:
                drug_classes = ["alprazolam", "sertraline", "buspirone", "lorazepam"]
            elif "diabetes" in condition_lower:
                drug_classes = ["metformin", "insulin", "glipizide", "pioglitazone"]
            elif "hypertension" in condition_lower or "blood pressure" in condition_lower:
                drug_classes = ["lisinopril", "amlodipine", "losartan", "hydrochlorothiazide"]
            elif "asthma" in condition_lower:
                drug_classes = ["albuterol", "fluticasone", "montelukast", "salmeterol"]
            elif "gerd" in condition_lower or "reflux" in condition_lower:
                drug_classes = ["omeprazole", "pantoprazole", "lansoprazole", "esomeprazole"]
            elif "osteoarthritis" in condition_lower or "arthritis" in condition_lower:
                drug_classes = ["celecoxib", "ibuprofen", "naproxen", "diclofenac"]
            elif "hypothyroidism" in condition_lower:
                drug_classes = ["levothyroxine", "liothyronine"]
            elif "copd" in condition_lower:
                drug_classes = ["albuterol", "tiotropium", "salmeterol", "fluticasone"]
            
            # Search RxNorm for each drug
            for drug_name in drug_classes[:3]:  # Limit to 3 searches
                rxnorm_info = self._get_rxnorm_for_drug(drug_name)
                if rxnorm_info:
                    # Get SNOMED CT code for RxNorm drug
                    snomed_code = self._get_snomed_code_for_drug(drug_name)
                    
                    medication = {
                        "@id": f"https://identifiers.org/rxnorm:{rxnorm_info['rxnorm_cui']}",
                        "@type": "sdisco:Medication",
                        "schema:name": drug_name,
                        "rdfs:label": drug_name,
                        "rxnorm": rxnorm_info,
                        "schema:dosageForm": "tablet",
                        "schema:doseValue": self._estimate_dose(drug_name),
                        "schema:doseUnit": "mg",
                        "schema:frequency": "Once daily",
                        "source": "rxnorm",
                        "treats_condition": condition
                    }
                    
                    # Add SNOMED CT code if found
                    if snomed_code:
                        medication["snomed:code"] = snomed_code
                        medication["snomed:uri"] = f"http://snomed.info/id/{snomed_code}"
                    
                    medications.append(medication)
        
        except Exception as e:
            print(f"      ⚠️ RxNorm search failed: {e}")
        
        return medications
    
    def _estimate_dose(self, drug_name: str) -> int:
        """Estimate typical dose based on drug name"""
        drug_lower = drug_name.lower()
        
        # Common dose patterns
        if "sertraline" in drug_lower:
            return random.choice([50, 100, 200])
        elif "escitalopram" in drug_lower or "citalopram" in drug_lower:
            return random.choice([10, 20, 40])
        elif "alprazolam" in drug_lower:
            return random.choice([0.25, 0.5, 1])
        elif "metformin" in drug_lower:
            return random.choice([500, 850, 1000])
        elif "lisinopril" in drug_lower:
            return random.choice([5, 10, 20])
        elif "atorvastatin" in drug_lower:
            return random.choice([10, 20, 40, 80])
        else:
            return random.choice([10, 20, 50, 100])  # Generic default
    
    def _get_known_drugs_for_condition(self, snomed_code: str, condition_label: str) -> List[Dict]:
        """
        Get known drugs for condition with RxNorm lookup for standardization
        Uses evidence-based drug-condition mappings
        """
        # Comprehensive drug-condition mapping with RxNorm/DrugBank IDs
        # Comprehensive drug-condition mapping - used as fallback when API search fails
        # Maps SNOMED codes to evidence-based medications
        condition_drug_map = {
            # Support multiple SNOMED codes for same condition type
            "44054006": [  # Diabetes type 2
                {"drugbank_id": "DB00619", "name": "Metformin", "doses": [500, 850, 1000], "unit": "mg", "frequency": "Twice daily"},
                {"drugbank_id": "DB00030", "name": "Insulin glargine", "doses": [10, 20, 30], "unit": "units", "frequency": "Once daily"}
            ],
            "73211009": [  # Diabetes mellitus (general)
                {"drugbank_id": "DB00619", "name": "Metformin", "doses": [500, 850, 1000], "unit": "mg", "frequency": "Twice daily"}
            ],
            "254837009": [  # Hypertension
                {"drugbank_id": "DB01175", "name": "Lisinopril", "doses": [5, 10, 20], "unit": "mg", "frequency": "Once daily"},
                {"drugbank_id": "DB00472", "name": "Amlodipine", "doses": [5, 10], "unit": "mg", "frequency": "Once daily"}
            ],
            "38341003": [  # Hypertensive disorder
                {"drugbank_id": "DB01175", "name": "Lisinopril", "doses": [5, 10, 20], "unit": "mg", "frequency": "Once daily"}
            ],
            "372244006": [  # Asthma
                {"drugbank_id": "DB14761", "name": "Albuterol", "doses": [90, 180], "unit": "mcg", "frequency": "As needed"},
                {"drugbank_id": "DB01264", "name": "Fluticasone", "doses": [110, 220], "unit": "mcg", "frequency": "Twice daily"}
            ],
            "363418016": [  # Depression
                {"drugbank_id": "DB00264", "name": "Sertraline", "doses": [50, 100, 200], "unit": "mg", "frequency": "Once daily"},
                {"drugbank_id": "DB00261", "name": "Escitalopram", "doses": [10, 20], "unit": "mg", "frequency": "Once daily"}
            ],
            "35489007": [  # Depressive disorder
                {"drugbank_id": "DB00264", "name": "Sertraline", "doses": [50, 100, 200], "unit": "mg", "frequency": "Once daily"},
                {"drugbank_id": "DB00261", "name": "Escitalopram", "doses": [10, 20], "unit": "mg", "frequency": "Once daily"}
            ],
            "363478007": [  # Anxiety disorder
                {"drugbank_id": "DB00856", "name": "Alprazolam", "doses": [0.25, 0.5, 1], "unit": "mg", "frequency": "Three times daily"},
                {"drugbank_id": "DB00264", "name": "Sertraline", "doses": [50, 100], "unit": "mg", "frequency": "Once daily"}
            ],
            "197480006": [  # Anxiety disorder (alternative code)
                {"drugbank_id": "DB00856", "name": "Alprazolam", "doses": [0.25, 0.5, 1], "unit": "mg", "frequency": "Three times daily"},
                {"drugbank_id": "DB00264", "name": "Sertraline", "doses": [50, 100], "unit": "mg", "frequency": "Once daily"}
            ],
            "266430006": [  # GERD
                {"drugbank_id": "DB00738", "name": "Omeprazole", "doses": [20, 40], "unit": "mg", "frequency": "Once daily"}
            ],
            "161891005": [  # Osteoarthritis
                {"drugbank_id": "DB01229", "name": "Celecoxib", "doses": [100, 200], "unit": "mg", "frequency": "Twice daily"}
            ],
            "4855003": [  # Hypothyroidism
                {"drugbank_id": "DB00651", "name": "Levothyroxine", "doses": [25, 50, 75, 100], "unit": "mcg", "frequency": "Once daily"}
            ],
            "26889001": [  # COPD
                {"drugbank_id": "DB14761", "name": "Albuterol", "doses": [90, 180], "unit": "mcg", "frequency": "As needed"},
                {"drugbank_id": "DB01264", "name": "Fluticasone", "doses": [110, 220], "unit": "mcg", "frequency": "Twice daily"}
            ],
            "10692761000119107": [  # Asthma-COPD overlap
                {"drugbank_id": "DB14761", "name": "Albuterol", "doses": [90, 180], "unit": "mcg", "frequency": "As needed"},
                {"drugbank_id": "DB01264", "name": "Fluticasone", "doses": [110, 220], "unit": "mcg", "frequency": "Twice daily"}
            ],
            "370992007": [  # Dyslipidemia
                {"drugbank_id": "DB00641", "name": "Atorvastatin", "doses": [10, 20, 40, 80], "unit": "mg", "frequency": "Once daily"},
                {"drugbank_id": "DB01076", "name": "Simvastatin", "doses": [10, 20, 40], "unit": "mg", "frequency": "Once daily"}
            ],
            "10742861000119102": [  # Dyslipidemia (alternative code)
                {"drugbank_id": "DB00641", "name": "Atorvastatin", "doses": [10, 20, 40, 80], "unit": "mg", "frequency": "Once daily"},
                {"drugbank_id": "DB01076", "name": "Simvastatin", "doses": [10, 20, 40], "unit": "mg", "frequency": "Once daily"}
            ]
        }
        
        # Try to find drugs by SNOMED code first
        drug_infos = []
        if snomed_code in condition_drug_map:
            drug_infos = condition_drug_map[snomed_code]
        else:
            # Try by condition label keywords (improved matching)
            condition_lower = condition_label.lower()
            
            # Map keywords to SNOMED codes with drugs
            keyword_mappings = {
                "anxiety": "197480006",
                "depress": "35489007",
                "asthma": "372244006",
                "copd": "26889001",
                "pulmonary": "26889001",
                "chronic obstructive": "26889001",
                "dyslipidemia": "370992007",
                "lipid": "370992007",
                "hyperlipidemia": "370992007",
                "hypertension": "38341003",
                "diabetes": "44054006",
                "gerd": "266430006",
                "reflux": "266430006",
                "arthritis": "161891005",
                "osteoarthritis": "161891005",
                "hypothyroidism": "4855003"
            }
            
            for keyword, code in keyword_mappings.items():
                if keyword in condition_lower and code in condition_drug_map:
                    drug_infos = condition_drug_map[code]
                    break
        
        if not drug_infos:
            return []  # No fallback drugs found
        current_date = datetime.now()
        
        medications = []
        for drug_info in drug_infos:
            # Select random dose
            dose_value = random.choice(drug_info["doses"])
            
            # Generate start date
            days_ago = random.randint(30, 730)
            start_date = (current_date - timedelta(days=days_ago)).strftime("%Y-%m-%d")
            
            # Try to get RxNorm CUI for the drug
            rxnorm_info = self._get_rxnorm_for_drug(drug_info["name"])
            
            medication = {
                "@id": f"https://go.drugbank.com/drugs/{drug_info['drugbank_id']}",
                "@type": "sdisco:Medication",
                "drugbank:id": drug_info["drugbank_id"],
                "rdfs:label": drug_info["name"],
                "schema:name": drug_info["name"],
                "schema:dosageForm": "tablet" if drug_info["unit"] in ["mg", "mcg"] else "injection" if drug_info["unit"] == "units" else "inhaler",
                "schema:doseValue": dose_value,
                "schema:doseUnit": drug_info["unit"],
                "schema:frequency": drug_info["frequency"],
                "start_date": start_date,
                "purpose": condition_label,
                "source": "evidence_based",
                "treats_condition": {
                    "snomed:code": snomed_code,
                    "rdfs:label": condition_label
                }
            }
            
            if rxnorm_info:
                medication["rxnorm"] = rxnorm_info
            
            # Add SNOMED CT code for evidence-based drug
            snomed_code = self._get_snomed_code_for_drug(drug_info["name"])
            if snomed_code:
                medication["snomed:code"] = snomed_code
                medication["snomed:uri"] = f"http://snomed.info/id/{snomed_code}"
            
            medications.append(medication)
        
        return medications
    
    def _get_rxnorm_for_drug(self, drug_name: str) -> Optional[Dict]:
        """Get RxNorm CUI for a drug"""
        endpoint = f"rxcui.json?name={drug_name}"
        data = self.rxnorm_client.get(endpoint)
        
        if not data or "idGroup" not in data:
            return None
        
        cui_list = data["idGroup"].get("rxnormId", [])
        if not cui_list:
            return None
        
        return {
            "rxnorm_cui": cui_list[0],
            "uri": f"https://identifiers.org/rxnorm:{cui_list[0]}"
        }
    
    def _get_snomed_code_for_drug(self, drug_name: str) -> Optional[str]:
        """
        Get SNOMED CT code for a drug/substance
        
        Args:
            drug_name: Drug name
            
        Returns:
            SNOMED CT code or None
        """
        if not self.bioportal_api_key:
            return None
        
        try:
            # Search SNOMED CT for substance with multiple strategies
            url = f"{self.bioportal_base}/search"
            base_params = {
                "ontologies": "SNOMEDCT",
                "apikey": self.bioportal_api_key,
                "pagesize": 5
            }

            def extract_first_code(resp: Dict) -> Optional[str]:
                if resp and resp.get("collection"):
                    # Prefer substance or product concepts if available
                    for item in resp["collection"]:
                        types = (item.get("@type") or []) if isinstance(item.get("@type"), list) else [item.get("@type")]
                        if any(t and "Substance" in t for t in types) or any(t and "Product" in t for t in types):
                            uri = item.get("@id", "")
                            return uri.split("/")[-1] if uri else None
                    # Fallback: first result
                    uri = resp["collection"][0].get("@id", "")
                    return uri.split("/")[-1] if uri else None
                return None

            # Strategy A: explicit substance qualifier
            params = {**base_params, "q": f"{drug_name} (substance)"}
            response = self.bioportal_client.get(url, params=params, headers=self.bioportal_headers)
            code = extract_first_code(response)
            if code:
                return code

            # Strategy B: plain drug name
            params = {**base_params, "q": drug_name}
            response = self.bioportal_client.get(url, params=params, headers=self.bioportal_headers)
            code = extract_first_code(response)
            if code:
                return code

            # Strategy C: common synonyms (lowercase variants)
            synonyms = {drug_name}
            lower = drug_name.lower()
            if lower.endswith("e"):  # e.g., omeprazole
                synonyms.add(lower)
            if "-" in lower:
                synonyms.add(lower.replace("-", " "))
            for term in synonyms:
                params = {**base_params, "q": term}
                response = self.bioportal_client.get(url, params=params, headers=self.bioportal_headers)
                code = extract_first_code(response)
                if code:
                    return code

            # Strategy D: RxNorm-assisted search – standardize name via RxNorm
            rxnorm = self._get_rxnorm_for_drug(drug_name)
            rx_name_candidates: List[str] = []
            if rxnorm and rxnorm.get("rxnorm_cui"):
                # Get standardized RxNorm name (if available)
                try:
                    cui = rxnorm["rxnorm_cui"]
                    # Use RxNorm display name endpoint
                    rx_resp = self.rxnorm_client.get(f"rxcui/{cui}/property.json?propName=RxNorm%20Name")
                    rx_name = None
                    if rx_resp and rx_resp.get("propConceptGroup"):
                        groups = rx_resp["propConceptGroup"].get("propConcept") or []
                        if groups and isinstance(groups, list):
                            rx_name = groups[0].get("propValue")
                    if rx_name:
                        rx_name_candidates.append(rx_name)
                except Exception:
                    pass
            for term in rx_name_candidates:
                params = {**base_params, "q": term}
                response = self.bioportal_client.get(url, params=params, headers=self.bioportal_headers)
                code = extract_first_code(response)
                if code:
                    return code
                params = {**base_params, "q": f"{term} (substance)"}
                response = self.bioportal_client.get(url, params=params, headers=self.bioportal_headers)
                code = extract_first_code(response)
                if code:
                    return code

        except Exception:
            # Silent fail - SNOMED CT is optional
            pass
        
        return None
    
    def _get_better_search_term(self, condition_label: str) -> str:
        """
        Get better search term for ChEMBL based on condition type
        Maps conditions to more specific search terms
        """
        condition_lower = condition_label.lower()
        
        # Map common conditions to better search terms
        search_term_mapping = {
            "asthma": "asthma",
            "copd": "chronic obstructive pulmonary disease",
            "pulmonary": "pulmonary disease",
            "dyslipidemia": "hyperlipidemia",
            "lipid": "hyperlipidemia",
            "diabetes": "diabetes",
            "hypertension": "hypertension",
            "depression": "depression",
            "anxiety": "anxiety",
            "arthritis": "arthritis",
            "pain": "pain",
            "infection": "infection",
            "heart": "heart disease",
            "cardiac": "heart disease"
        }
        
        # Check for keywords in condition
        for keyword, search_term in search_term_mapping.items():
            if keyword in condition_lower:
                return search_term
        
        # Default: use first significant word (not articles/prepositions)
        words = condition_label.split()
        significant_words = [w for w in words if len(w) > 3 and w.lower() not in ["the", "for", "with", "and", "or"]]
        
        if significant_words:
            return significant_words[0].lower()

        return condition_label.split()[0] if condition_label else ""

    def _get_static_conditions_by_age(self, age: int, lifestyle_factors: List[Dict]) -> List[Dict]:
        """
        Static fallback: Generate realistic conditions based on age and lifestyle
        Used when API calls fail to ensure profiles always have some clinical data
        """
        # Common conditions with SNOMED codes (real codes for common conditions)
        static_conditions = {
            "hypertension": {
                "@id": "http://snomed.info/id/38341003",
                "@type": "sdisco:Condition",
                "snomed:code": "38341003",
                "rdfs:label": "Essential hypertension",
                "skos:prefLabel": "Essential hypertension",
                "search_term": "hypertension"
            },
            "diabetes_type2": {
                "@id": "http://snomed.info/id/44054006",
                "@type": "sdisco:Condition",
                "snomed:code": "44054006",
                "rdfs:label": "Diabetes mellitus type 2",
                "skos:prefLabel": "Diabetes mellitus type 2",
                "search_term": "diabetes type 2"
            },
            "hyperlipidemia": {
                "@id": "http://snomed.info/id/55822004",
                "@type": "sdisco:Condition",
                "snomed:code": "55822004",
                "rdfs:label": "Hyperlipidemia",
                "skos:prefLabel": "Hyperlipidemia",
                "search_term": "high cholesterol"
            },
            "osteoarthritis": {
                "@id": "http://snomed.info/id/396275006",
                "@type": "sdisco:Condition",
                "snomed:code": "396275006",
                "rdfs:label": "Osteoarthritis",
                "skos:prefLabel": "Osteoarthritis",
                "search_term": "osteoarthritis"
            },
            "gerd": {
                "@id": "http://snomed.info/id/235595009",
                "@type": "sdisco:Condition",
                "snomed:code": "235595009",
                "rdfs:label": "Gastroesophageal reflux disease",
                "skos:prefLabel": "GERD",
                "search_term": "GERD"
            },
            "asthma": {
                "@id": "http://snomed.info/id/195967001",
                "@type": "sdisco:Condition",
                "snomed:code": "195967001",
                "rdfs:label": "Asthma",
                "skos:prefLabel": "Asthma",
                "search_term": "asthma"
            },
            "depression": {
                "@id": "http://snomed.info/id/35489007",
                "@type": "sdisco:Condition",
                "snomed:code": "35489007",
                "rdfs:label": "Depressive disorder",
                "skos:prefLabel": "Depression",
                "search_term": "depression"
            },
            "anxiety": {
                "@id": "http://snomed.info/id/48694002",
                "@type": "sdisco:Condition",
                "snomed:code": "48694002",
                "rdfs:label": "Anxiety disorder",
                "skos:prefLabel": "Anxiety",
                "search_term": "anxiety"
            },
            "copd": {
                "@id": "http://snomed.info/id/13645005",
                "@type": "sdisco:Condition",
                "snomed:code": "13645005",
                "rdfs:label": "Chronic obstructive pulmonary disease",
                "skos:prefLabel": "COPD",
                "search_term": "COPD"
            },
            "allergic_rhinitis": {
                "@id": "http://snomed.info/id/61582004",
                "@type": "sdisco:Condition",
                "snomed:code": "61582004",
                "rdfs:label": "Allergic rhinitis",
                "skos:prefLabel": "Allergic rhinitis",
                "search_term": "allergies"
            }
        }

        conditions = []

        # Age-based selection with MUCH HIGHER probabilities for comprehensive profiles
        if age >= 60:
            # Older adults - typically have 3-4 chronic conditions
            if random.random() < 0.85:  # 85% chance
                conditions.append(static_conditions["hypertension"])
            if random.random() < 0.70:  # 70% chance
                conditions.append(static_conditions["hyperlipidemia"])
            if random.random() < 0.60:  # 60% chance
                conditions.append(static_conditions["diabetes_type2"])
            if random.random() < 0.50:  # 50% chance
                conditions.append(static_conditions["osteoarthritis"])
            if random.random() < 0.40:  # 40% chance
                conditions.append(static_conditions["gerd"])
        elif age >= 40:
            # Middle-aged - typically have 2-3 conditions
            if random.random() < 0.70:  # 70% chance
                conditions.append(static_conditions["hypertension"])
            if random.random() < 0.65:  # 65% chance
                conditions.append(static_conditions["hyperlipidemia"])
            if random.random() < 0.45:  # 45% chance
                conditions.append(static_conditions["diabetes_type2"])
            if random.random() < 0.50:  # 50% chance
                conditions.append(static_conditions["gerd"])
            if random.random() < 0.35:  # 35% chance
                conditions.append(static_conditions["depression"])
        else:
            # Younger adults - typically have 2-3 conditions
            if random.random() < 0.50:  # 50% chance
                conditions.append(static_conditions["asthma"])
            if random.random() < 0.45:  # 45% chance
                conditions.append(static_conditions["anxiety"])
            if random.random() < 0.55:  # 55% chance
                conditions.append(static_conditions["allergic_rhinitis"])
            if random.random() < 0.40:  # 40% chance
                conditions.append(static_conditions["depression"])

        # Lifestyle-based additions
        is_smoker = any(f.get('factor_type') == 'smoking' and f.get('status') == 'current'
                       for f in lifestyle_factors if isinstance(f, dict))
        if is_smoker and random.random() < 0.60:  # 60% for smokers
            conditions.append(static_conditions["copd"])

        # GUARANTEE at least 3 conditions for comprehensive profiles
        if len(conditions) < 3:
            # Add common conditions until we have at least 3
            pool_keys = ["hyperlipidemia", "gerd", "allergic_rhinitis", "hypertension", "anxiety"]
            random.shuffle(pool_keys)
            for cond_key in pool_keys:
                if static_conditions[cond_key] not in conditions:
                    conditions.append(static_conditions[cond_key])
                    if len(conditions) >= 3:
                        break

        print(f"    📋 Static fallback generated {len(conditions)} conditions")
        return conditions[:5]  # Limit to 5 max

    def _get_static_medications_for_conditions(self, conditions: List[Dict]) -> List[Dict]:
        """
        Static fallback: Generate medications based on conditions
        Used when API calls fail to ensure profiles always have medication data
        Now includes MULTIPLE medications per condition for realistic combination therapy
        """
        # Comprehensive medication map with MULTIPLE drugs per condition (real DrugBank IDs)
        medication_map = {
            "38341003": [  # Hypertension - typically needs 2-3 drugs
                {
                    "@id": "http://go.drugbank.com/drugs/DB00945",
                    "@type": "sdisco:Drug",
                    "drugbank:id": "DB00945",
                    "rdfs:label": "Aspirin",
                    "indication": "Cardiovascular protection",
                    "source": "evidence_based"
                },
                {
                    "@id": "http://go.drugbank.com/drugs/DB00492",
                    "@type": "sdisco:Drug",
                    "drugbank:id": "DB00492",
                    "rdfs:label": "Fosinopril",
                    "indication": "Hypertension (ACE inhibitor)",
                    "source": "evidence_based"
                },
                {
                    "@id": "http://go.drugbank.com/drugs/DB00999",
                    "@type": "sdisco:Drug",
                    "drugbank:id": "DB00999",
                    "rdfs:label": "Hydrochlorothiazide",
                    "indication": "Hypertension (diuretic)",
                    "source": "evidence_based"
                }
            ],
            "44054006": [  # Diabetes type 2 - often needs 2 drugs
                {
                    "@id": "http://go.drugbank.com/drugs/DB00331",
                    "@type": "sdisco:Drug",
                    "drugbank:id": "DB00331",
                    "rdfs:label": "Metformin",
                    "indication": "Type 2 diabetes mellitus (first-line)",
                    "source": "evidence_based"
                },
                {
                    "@id": "http://go.drugbank.com/drugs/DB00046",
                    "@type": "sdisco:Drug",
                    "drugbank:id": "DB00046",
                    "rdfs:label": "Insulin lispro",
                    "indication": "Type 2 diabetes mellitus (supplemental)",
                    "source": "evidence_based"
                }
            ],
            "55822004": [  # Hyperlipidemia
                {
                    "@id": "http://go.drugbank.com/drugs/DB01076",
                    "@type": "sdisco:Drug",
                    "drugbank:id": "DB01076",
                    "rdfs:label": "Atorvastatin",
                    "indication": "Hyperlipidemia (statin)",
                    "source": "evidence_based"
                },
                {
                    "@id": "http://go.drugbank.com/drugs/DB00973",
                    "@type": "sdisco:Drug",
                    "drugbank:id": "DB00973",
                    "rdfs:label": "Ezetimibe",
                    "indication": "Hyperlipidemia (cholesterol absorption inhibitor)",
                    "source": "evidence_based"
                }
            ],
            "396275006": [  # Osteoarthritis - may need 2 drugs
                {
                    "@id": "http://go.drugbank.com/drugs/DB00328",
                    "@type": "sdisco:Drug",
                    "drugbank:id": "DB00328",
                    "rdfs:label": "Indomethacin",
                    "indication": "Pain and inflammation (NSAID)",
                    "source": "evidence_based"
                },
                {
                    "@id": "http://go.drugbank.com/drugs/DB00316",
                    "@type": "sdisco:Drug",
                    "drugbank:id": "DB00316",
                    "rdfs:label": "Acetaminophen",
                    "indication": "Pain relief",
                    "source": "evidence_based"
                }
            ],
            "235595009": [  # GERD
                {
                    "@id": "http://go.drugbank.com/drugs/DB00338",
                    "@type": "sdisco:Drug",
                    "drugbank:id": "DB00338",
                    "rdfs:label": "Omeprazole",
                    "indication": "Gastroesophageal reflux disease (PPI)",
                    "source": "evidence_based"
                }
            ],
            "195967001": [  # Asthma - typically needs 2 drugs (controller + rescue)
                {
                    "@id": "http://go.drugbank.com/drugs/DB01001",
                    "@type": "sdisco:Drug",
                    "drugbank:id": "DB01001",
                    "rdfs:label": "Salbutamol",
                    "indication": "Asthma (rescue inhaler)",
                    "source": "evidence_based"
                },
                {
                    "@id": "http://go.drugbank.com/drugs/DB00588",
                    "@type": "sdisco:Drug",
                    "drugbank:id": "DB00588",
                    "rdfs:label": "Fluticasone",
                    "indication": "Asthma (controller inhaler)",
                    "source": "evidence_based"
                }
            ],
            "35489007": [  # Depression
                {
                    "@id": "http://go.drugbank.com/drugs/DB00472",
                    "@type": "sdisco:Drug",
                    "drugbank:id": "DB00472",
                    "rdfs:label": "Fluoxetine",
                    "indication": "Depression (SSRI)",
                    "source": "evidence_based"
                }
            ],
            "48694002": [  # Anxiety
                {
                    "@id": "http://go.drugbank.com/drugs/DB00404",
                    "@type": "sdisco:Drug",
                    "drugbank:id": "DB00404",
                    "rdfs:label": "Alprazolam",
                    "indication": "Anxiety disorder (benzodiazepine)",
                    "source": "evidence_based"
                }
            ],
            "13645005": [  # COPD - typically needs 2-3 drugs
                {
                    "@id": "http://go.drugbank.com/drugs/DB00697",
                    "@type": "sdisco:Drug",
                    "drugbank:id": "DB00697",
                    "rdfs:label": "Tiotropium",
                    "indication": "COPD (long-acting bronchodilator)",
                    "source": "evidence_based"
                },
                {
                    "@id": "http://go.drugbank.com/drugs/DB01001",
                    "@type": "sdisco:Drug",
                    "drugbank:id": "DB01001",
                    "rdfs:label": "Salbutamol",
                    "indication": "COPD (rescue bronchodilator)",
                    "source": "evidence_based"
                }
            ],
            "61582004": [  # Allergic rhinitis
                {
                    "@id": "http://go.drugbank.com/drugs/DB00341",
                    "@type": "sdisco:Drug",
                    "drugbank:id": "DB00341",
                    "rdfs:label": "Cetirizine",
                    "indication": "Allergic rhinitis (antihistamine)",
                    "source": "evidence_based"
                }
            ]
        }

        medications = []
        seen_drugbank_ids = set()

        # Get ALL medications for each condition (not just first one)
        for condition in conditions:
            snomed_code = condition.get("snomed:code")
            if snomed_code in medication_map:
                for med in medication_map[snomed_code]:
                    drugbank_id = med.get("drugbank:id")
                    if drugbank_id not in seen_drugbank_ids:
                        medications.append(med)
                        seen_drugbank_ids.add(drugbank_id)
                        print(f"      💊 Added medication: {med.get('rdfs:label')}")

        print(f"    📋 Static fallback generated {len(medications)} medications for {len(conditions)} conditions")
        return medications[:10]  # Increased limit to 10 medications

