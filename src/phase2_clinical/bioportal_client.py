"""
BioPortal Client
Maps terms to SNOMED CT codes via BioPortal API
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from typing import Dict, Optional, List
from utils.api_client import APIClient


class BioPortalClient:
    """Client for querying BioPortal SNOMED CT"""
    
    def __init__(self, api_key: str):
        """
        Initialize BioPortal client
        
        Args:
            api_key: BioPortal API key
        """
        self.base_url = "https://data.bioontology.org"
        self.api_key = api_key
        self.client = APIClient(self.base_url, rate_limit=10)
        self.headers = {"Authorization": f"apikey token={api_key}"}
    
    def search_snomed(self, term: str, ontology: str = "SNOMEDCT") -> Optional[Dict]:
        """
        Search for a term in SNOMED CT
        
        Args:
            term: Search term
            ontology: Ontology to search (default: SNOMEDCT)
            
        Returns:
            Dictionary with SNOMED code and label, or None
        """
        endpoint = "search"
        params = {
            "q": term,
            "ontologies": ontology,
            "require_exact_match": "false",
            "page_size": 10  # Get more results to find better matches
        }
        
        data = self.client.get(endpoint, params=params, headers=self.headers)
        
        if not data or "collection" not in data:
            return None
        
        results = data["collection"]
        if not results:
            return None
        
        # Get best match
        best_match = results[0]
        
        # Extract SNOMED code from URI
        snomed_uri = best_match.get("@id", "")
        snomed_code = snomed_uri.split("/")[-1] if snomed_uri else None
        
        if not snomed_code:
            return None
        
        return {
            "code": snomed_code,
            "label": best_match.get("prefLabel", ""),
            "uri": f"http://snomed.info/id/{snomed_code}",
            "match_type": "exact" if best_match.get("exact_match") else "partial",
            "definition": best_match.get("definition", [])
        }
    
    def search_clinical_finding(self, phenotype_text: str, gene_symbol: str = None, drug_name: str = None) -> Optional[Dict]:
        """
        Search for Clinical Finding in SNOMED CT for pharmacogenomic phenotypes
        Uses proper SNOMED CT post-coordinated expressions when possible
        
        Args:
            phenotype_text: Full phenotype description
            gene_symbol: Gene symbol (e.g., CYP2C19)
            drug_name: Drug name (e.g., clopidogrel)
            
        Returns:
            Dictionary with SNOMED Clinical Finding code/expression and label, or None
        """
        # First, try to build a proper post-coordinated SNOMED CT expression
        post_coordinated = self._build_post_coordinated_expression(phenotype_text, gene_symbol, drug_name)
        if post_coordinated:
            return post_coordinated
        
        # If post-coordination fails, return None rather than using poor search results
        # This ensures we only return high-quality SNOMED CT mappings
        return None
    
    def _build_post_coordinated_expression(self, phenotype_text: str, gene_symbol: str = None, drug_name: str = None) -> Optional[Dict]:
        """
        Build proper SNOMED CT post-coordinated expression for pharmacogenomic findings
        
        Format: FocusConceptID : { AttributeID1 = ValueID1 , AttributeID2 = ValueID2 }
        
        Example:
        406164007 | Ineffective drug therapy (finding) : { 
            246075003 | Causative agent (attribute) = 412352002 | Clopidogrel (substance) , 
            47429007 | Associated with (attribute) = 782299006 | Cytochrome P450 2C19 poor metabolizer genotype (finding) 
        }
        """
        phenotype_lower = phenotype_text.lower()
        
        # Detect the type of clinical finding from phenotype text
        finding_type = None
        finding_concept = None
        
        # More specific detection patterns for pharmacogenomic findings
        # Check for drug-related findings first (most specific)
        if any(term in phenotype_lower for term in ["ineffective", "reduced efficacy", "decreased response", "poor response", "no significant association"]):
            if "drug" in phenotype_lower or drug_name:
                finding_type = "ineffective_therapy"
                finding_concept = "406164007"  # Ineffective drug therapy (finding)
        
        # Check for concentration changes (drug pharmacokinetics)
        if not finding_concept:
            if any(term in phenotype_lower for term in ["increased concentration", "elevated concentration", "higher concentration", "increased levels", "increased risk"]):
                finding_type = "increased_concentration"
                finding_concept = "404919007"  # Increased drug concentration (finding)
            elif any(term in phenotype_lower for term in ["decreased concentration", "reduced concentration", "lower concentration", "reduced levels"]):
                finding_type = "decreased_concentration"
                finding_concept = "404920001"  # Decreased drug concentration (finding)
        
        # Check for clearance/metabolism changes
        if not finding_concept:
            if any(term in phenotype_lower for term in ["decreased clearance", "reduced clearance", "decreased metabolism", "reduced metabolism"]):
                finding_type = "decreased_clearance"
                finding_concept = "733423003"  # Altered drug clearance (finding)
            elif any(term in phenotype_lower for term in ["increased clearance", "increased metabolism"]):
                finding_type = "increased_clearance"
                finding_concept = "733423003"  # Altered drug clearance (finding)
        
        # Check for risk/protective findings
        if not finding_concept:
            if "decreased risk" in phenotype_lower:
                finding_type = "decreased_risk"
                finding_concept = "365858006"  # Finding of risk level (finding)
            elif "increased risk" in phenotype_lower or "risk of" in phenotype_lower:
                finding_type = "increased_risk"
                finding_concept = "365858006"  # Finding of risk level (finding)
        
        # Check for adverse reactions
        if not finding_concept:
            if any(term in phenotype_lower for term in ["adverse reaction", "toxicity", "side effect", "harmful"]):
                finding_type = "adverse_reaction"
                finding_concept = "281647001"  # Adverse reaction (finding)
        
        # Check for enzyme activity findings (generic fallback)
        if not finding_concept:
            if any(term in phenotype_lower for term in ["enzyme activity", "decreased enzyme activity", "increased enzyme activity"]):
                finding_type = "enzyme_activity"
                finding_concept = "713330009"  # Thiopurine S-methyltransferase deficient (finding)
        
        # Only proceed if we have a finding concept AND either drug or gene context
        if not finding_concept:
            return None
        
        # Require at least drug or gene context for meaningful post-coordination
        if not drug_name and not gene_symbol:
            return None
        
        # Search for drug concept if drug name provided
        drug_concept = None
        drug_label = None
        if drug_name:
            # Try to find drug in SNOMED CT (filter for substances, not findings)
            drug_search = self.search_snomed(drug_name)
            if drug_search:
                # Verify it's a substance, not a finding
                snomed_code = drug_search.get("code")
                if snomed_code:
                    # Check if it contains "substance" in the URI or check the concept type
                    concept_label = self._get_concept_label(snomed_code) or ""
                    if "substance" in concept_label.lower() or "product" in concept_label.lower() or "medication" in concept_label.lower():
                        drug_concept = snomed_code
                        drug_label = concept_label
        
        # Search for genotype/phenotype concept if gene symbol provided
        genotype_concept = None
        genotype_label = None
        if gene_symbol:
            # Check for metabolizer status patterns
            if "poor metabolizer" in phenotype_lower or "no function" in phenotype_lower or "impaired" in phenotype_lower:
                genotype_search = self.search_snomed(f"{gene_symbol} poor metabolizer genotype")
                if genotype_search:
                    genotype_concept = genotype_search.get("code")
                    genotype_label = genotype_search.get("label")
            elif "intermediate metabolizer" in phenotype_lower:
                genotype_search = self.search_snomed(f"{gene_symbol} intermediate metabolizer genotype")
                if genotype_search:
                    genotype_concept = genotype_search.get("code")
                    genotype_label = genotype_search.get("label")
            elif "ultra rapid metabolizer" in phenotype_lower or "extensive metabolizer" in phenotype_lower or "rapid metabolizer" in phenotype_lower:
                genotype_search = self.search_snomed(f"{gene_symbol} extensive metabolizer genotype")
                if genotype_search:
                    genotype_concept = genotype_search.get("code")
                    genotype_label = genotype_search.get("label")
            else:
                # Generic genotype finding for the gene
                genotype_search = self.search_snomed(f"{gene_symbol} genotype")
                if genotype_search:
                    genotype_concept = genotype_search.get("code")
                    genotype_label = genotype_search.get("label")
        
        # Build post-coordinated expression - require at least one attribute
        attributes = []
        
        if drug_concept:
            drug_display = drug_label or drug_name
            attributes.append(f"246075003 | Causative agent (attribute) = {drug_concept} | {drug_display} (substance)")
        
        if genotype_concept:
            genotype_display = genotype_label or f"{gene_symbol} genotype"
            attributes.append(f"47429007 | Associated with (attribute) = {genotype_concept} | {genotype_display} (finding)")
        
        # Only return if we have at least one meaningful attribute
        if not attributes:
            return None
        
        expression = f"{finding_concept} : {{ {', '.join(attributes)} }}"
        
        # Get base concept label
        base_label = self._get_concept_label(finding_concept)
        if not base_label:
            # Fallback to readable names based on finding type
            finding_labels = {
                "ineffective_therapy": "Ineffective drug therapy",
                "increased_concentration": "Increased drug concentration",
                "decreased_concentration": "Decreased drug concentration",
                "decreased_clearance": "Altered drug clearance",
                "increased_clearance": "Altered drug clearance",
                "decreased_risk": "Decreased risk finding",
                "increased_risk": "Increased risk finding",
                "adverse_reaction": "Adverse reaction",
                "enzyme_activity": "Enzyme activity finding"
            }
            base_label = finding_labels.get(finding_type, "Clinical finding")
        
        return {
            "code": finding_concept,
            "label": base_label,
            "uri": f"http://snomed.info/id/{finding_concept}",
            "match_type": "post_coordinated",
            "expression": expression,
            "definition": [f"Post-coordinated SNOMED CT expression: {expression}"],
            "search_term": phenotype_text,  # Keep full text for drug extraction
            "phenotype_text": phenotype_text,  # Store full phenotype text
            "attributes": {
                "causative_agent": drug_concept if drug_concept else None,
                "associated_with": genotype_concept if genotype_concept else None,
                "drug_name": drug_name if drug_name else None,  # Include drug name for reference
                "gene_symbol": gene_symbol if gene_symbol else None  # Include gene for reference
            }
        }
    
    def _get_concept_label(self, snomed_code: str) -> Optional[str]:
        """Get the label for a SNOMED CT concept code"""
        try:
            endpoint = f"ontologies/SNOMEDCT/classes/http%3A%2F%2Fsnomed.info%2Fid%2F{snomed_code}"
            data = self.client.get(endpoint, headers=self.headers)
            if data and "prefLabel" in data:
                return data["prefLabel"]
        except:
            pass
        return None
    
    def _extract_key_terms(self, text: str) -> list:
        """Extract key medical terms from phenotype text"""
        # Common pharmacogenomic and medical terms to prioritize
        key_patterns = [
            # Drug response terms
            "increased", "decreased", "reduced", "enhanced", "impaired",
            "metabolism", "clearance", "concentration", "response", "efficacy",
            "toxicity", "adverse", "bleeding", "thrombosis", "reactivity",
            # Medical conditions
            "cardiovascular", "cardiac", "hepatic", "renal", "neurological",
            "psychiatric", "gastrointestinal", "respiratory", "hematologic",
            # Drug names and classes
            "clopidogrel", "warfarin", "methadone", "clobazam", "prasugrel",
            "etravirine", "anticoagulant", "antiplatelet", "opioid"
        ]
        
        text_lower = text.lower()
        found_terms = []
        
        for pattern in key_patterns:
            if pattern in text_lower:
                # Extract context around the key term
                words = text_lower.split()
                for i, word in enumerate(words):
                    if pattern in word:
                        # Get 2-3 words of context
                        start = max(0, i-1)
                        end = min(len(words), i+3)
                        context = " ".join(words[start:end])
                        found_terms.append(context)
                        break
        
        # If no key terms found, extract first meaningful phrase
        if not found_terms:
            words = text.split()[:10]  # First 10 words
            found_terms.append(" ".join(words))
        
        return found_terms[:3]  # Limit to top 3 terms
    
    def _search_with_clinical_finding_filter(self, term: str) -> Optional[Dict]:
        """Search SNOMED CT and prioritize Clinical Findings with better filtering"""
        endpoint = "search"
        params = {
            "q": term,
            "ontologies": "SNOMEDCT",
            "require_exact_match": "false",
            "page_size": 30  # Get more results for better filtering
        }
        
        data = self.client.get(endpoint, params=params, headers=self.headers)
        
        if not data or "collection" not in data:
            return None
        
        results = data["collection"]
        if not results:
            return None
        
        # Filter out substances/drugs and prioritize clinical findings
        clinical_findings = []
        substance_drugs = []
        other_results = []
        
        # Terms that indicate drugs/substances (should be filtered out)
        drug_indicators = ["substance", "product", "medication", "drug", "preparation"]
        
        for result in results:
            label = result.get("prefLabel", "").lower()
            definition = " ".join(result.get("definition", [])).lower() if result.get("definition") else ""
            full_text = (label + " " + definition).lower()
            
            # Filter out drug names and substances
            if any(indicator in full_text for indicator in drug_indicators):
                # But check if it's actually about a finding related to a drug
                if any(term in full_text for term in ["adverse", "reaction", "response", "interaction", "effect"]):
                    # This is a finding about a drug, keep it
                    clinical_findings.append(result)
                else:
                    substance_drugs.append(result)
                continue
            
            # Check if this is a Clinical Finding
            # More specific patterns for pharmacogenomic findings
            if any(term in full_text for term in [
                "finding", "disorder", "disease", "condition", "syndrome", 
                "dysfunction", "abnormality", "impairment", "response to",
                "adverse reaction", "drug response", "metabolic disorder",
                "enzyme activity", "pharmacokinetic", "drug metabolism"
            ]):
                clinical_findings.append(result)
            else:
                other_results.append(result)
        
        # Score and prioritize results
        scored_results = []
        
        for result in clinical_findings:
            label = result.get("prefLabel", "").lower()
            score = 0
            
            # Higher score for pharmacogenomic-relevant terms
            if any(term in label for term in ["drug response", "pharmacokinetic", "metabolism", "enzyme activity"]):
                score += 10
            elif any(term in label for term in ["response", "adverse", "reaction", "finding"]):
                score += 5
            
            # Lower score for too generic terms
            if any(term in label for term in ["disorder of carbohydrate", "general", "unspecified"]):
                score -= 5
            
            scored_results.append((score, result))
        
        # Sort by score (highest first)
        scored_results.sort(key=lambda x: x[0], reverse=True)
        
        # Get best match
        if scored_results:
            best_match = scored_results[0][1]
        elif other_results:
            best_match = other_results[0]
        else:
            return None
        
        # Extract SNOMED code from URI
        snomed_uri = best_match.get("@id", "")
        snomed_code = snomed_uri.split("/")[-1] if snomed_uri else None
        
        if not snomed_code:
            return None
        
        return {
            "code": snomed_code,
            "label": best_match.get("prefLabel", ""),
            "uri": f"http://snomed.info/id/{snomed_code}",
            "match_type": "clinical_finding" if clinical_findings else "general",
            "definition": best_match.get("definition", []),
            "search_term": term
        }
    
    def map_phenotype(self, phenotype_text: str, gene_symbol: str = None, drug_name: str = None) -> Optional[Dict]:
        """
        Map phenotype text to SNOMED CT Clinical Finding
        
        Args:
            phenotype_text: Phenotype description
            gene_symbol: Gene symbol (e.g., CYP2C19)
            drug_name: Drug name (e.g., clopidogrel)
            
        Returns:
            SNOMED CT Clinical Finding mapping or None
        """
        return self.search_clinical_finding(phenotype_text, gene_symbol, drug_name)
    
    def map_disease(self, disease_text: str) -> Optional[Dict]:
        """
        Map disease/phenotype text to SNOMED CT Clinical Finding
        
        Args:
            disease_text: Disease name or phenotype description
            
        Returns:
            SNOMED CT Clinical Finding mapping or None
        """
        return self.search_clinical_finding(disease_text)
    
    def map_adverse_reaction(self, reaction_text: str) -> Optional[Dict]:
        """
        Map adverse reaction to SNOMED CT clinical finding
        
        Args:
            reaction_text: Adverse reaction description
            
        Returns:
            SNOMED CT Clinical Finding mapping or None
        """
        return self.search_clinical_finding(reaction_text)
    
    def map_procedure(self, procedure_text: str) -> Optional[Dict]:
        """
        Map genetic test/procedure to SNOMED CT procedure code
        
        Args:
            procedure_text: Procedure description
            
        Returns:
            SNOMED CT mapping or None
        """
        return self.search_snomed(procedure_text)
    
    def get_snomed_hierarchy(self, snomed_code: str) -> Optional[Dict]:
        """
        Get SNOMED CT concept hierarchy (parents/ancestors)
        
        Args:
            snomed_code: SNOMED CT code
            
        Returns:
            Dictionary with hierarchy information or None
        """
        endpoint = f"ontologies/SNOMEDCT/classes/http%3A%2F%2Fsnomed.info%2Fid%2F{snomed_code}/ancestors"
        
        try:
            data = self.client.get(endpoint, headers=self.headers)
        except Exception as e:
            # Many SNOMED codes don't have ancestors in BioPortal - this is normal
            # Silently handle 404s and other errors
            return None
        
        if not data or "collection" not in data:
            return None
        
        ancestors = data["collection"]
        
        # Filter for disease-related ancestors
        disease_ancestors = []
        for ancestor in ancestors:
            label = ancestor.get("prefLabel", "").lower()
            if any(term in label for term in [
                "disease", "disorder", "syndrome", "condition", 
                "dysfunction", "pathology", "abnormality"
            ]):
                ancestor_code = ancestor.get("@id", "").split("/")[-1]
                if ancestor_code:
                    disease_ancestors.append({
                        "code": ancestor_code,
                        "label": ancestor.get("prefLabel", ""),
                        "uri": f"http://snomed.info/id/{ancestor_code}"
                    })
        
        if not disease_ancestors:
            return None
        
        return {
            "clinical_finding_code": snomed_code,
            "disease_ancestors": disease_ancestors[:5]  # Top 5 most relevant
        }
    
    def extract_disease_entities(self, phenotype_text: str) -> List[str]:
        """
        Extract potential disease names from phenotype text using pattern matching
        
        Args:
            phenotype_text: Full phenotype description
            
        Returns:
            List of potential disease names
        """
        import re
        
        # Common disease patterns in pharmacogenomic text
        disease_patterns = [
            # Direct disease mentions
            r'\b(cardiovascular disease|heart disease|cardiac disease)\b',
            r'\b(diabetes|diabetes mellitus)\b',
            r'\b(hypertension|high blood pressure)\b',
            r'\b(depression|major depression)\b',
            r'\b(anxiety|anxiety disorder)\b',
            r'\b(schizophrenia|psychosis)\b',
            r'\b(epilepsy|seizure disorder)\b',
            r'\b(cancer|carcinoma|tumor|malignancy)\b',
            r'\b(thrombosis|blood clot)\b',
            r'\b(bleeding|hemorrhage)\b',
            r'\b(liver disease|hepatic disease)\b',
            r'\b(kidney disease|renal disease)\b',
            
            # Syndrome patterns
            r'\b(\w+\s+syndrome)\b',
            r'\b(\w+\s+disorder)\b',
            r'\b(\w+\s+disease)\b',
            
            # Condition patterns
            r'\bpatients with ([^,]+(?:disease|disorder|syndrome|condition))\b',
            r'\bin patients with ([^,]+(?:disease|disorder|syndrome))\b'
        ]
        
        diseases = []
        text_lower = phenotype_text.lower()
        
        for pattern in disease_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    diseases.extend([m.strip() for m in match if m.strip()])
                else:
                    diseases.append(match.strip())
        
        # Remove duplicates and filter out very short matches
        unique_diseases = list(set([d for d in diseases if len(d) > 3]))
        return unique_diseases[:3]  # Top 3 most relevant
    
    def extract_pharmgkb_diseases(self, phenotype_text: str) -> List[str]:
        """
        Extract pharmacogenomic-specific diseases from PharmGKB phenotype text
        
        Args:
            phenotype_text: PharmGKB phenotype description
            
        Returns:
            List of extracted disease names
        """
        import re
        
        # Pharmacogenomic-specific disease patterns from PharmGKB data
        pharmgkb_disease_patterns = [
            # Cardiovascular diseases
            r'\b(cardiovascular disease|heart disease|cardiac disease|acute coronary syndrome)\b',
            r'\b(myocardial infarction|heart attack)\b',
            r'\b(atrial fibrillation|arrhythmia)\b',
            r'\b(hypertension|high blood pressure)\b',
            r'\b(stroke|cerebrovascular disease)\b',
            r'\b(thrombosis|blood clot|bleeding events?)\b',
            
            # Cancer types
            r'\b(breast cancer|lung cancer|colon cancer|prostate cancer)\b',
            r'\b(cancer|carcinoma|tumor|malignancy|neoplasm)\b',
            
            # Neurological/Psychiatric
            r'\b(epilepsy|seizure disorder)\b',
            r'\b(depression|major depression|depressive disorder)\b',
            r'\b(anxiety|anxiety disorder|panic disorder)\b',
            r'\b(schizophrenia|psychosis|bipolar disorder)\b',
            r'\b(alzheimer\'?s disease|dementia)\b',
            r'\b(parkinson\'?s disease)\b',
            
            # Metabolic diseases
            r'\b(diabetes|diabetes mellitus|type \d+ diabetes)\b',
            r'\b(obesity|overweight)\b',
            r'\b(metabolic syndrome)\b',
            r'\b(hyperlipidemia|high cholesterol)\b',
            
            # Infectious diseases
            r'\b(HIV|human immunodeficiency virus)\b',
            r'\b(hepatitis [ABC]?)\b',
            r'\b(tuberculosis|TB)\b',
            r'\b(malaria)\b',
            
            # Autoimmune/Inflammatory
            r'\b(rheumatoid arthritis|arthritis)\b',
            r'\b(inflammatory bowel disease|IBD|crohn\'?s disease|ulcerative colitis)\b',
            r'\b(lupus|systemic lupus erythematosus)\b',
            
            # Organ-specific diseases
            r'\b(liver disease|hepatic disease|cirrhosis)\b',
            r'\b(kidney disease|renal disease|chronic kidney disease)\b',
            r'\b(lung disease|pulmonary disease|asthma|COPD)\b',
            
            # Addiction/Substance use
            r'\b(alcoholism|alcohol use disorder|substance abuse)\b',
            r'\b(opioid addiction|drug addiction)\b',
            
            # Context-aware extraction
            r'\bpatients with ([^,]+(?:disease|disorder|syndrome|condition|cancer))\b',
            r'\bin patients with ([^,]+(?:disease|disorder|syndrome|cancer))\b',
            r'\bwho have ([^,]+(?:disease|disorder|syndrome|cancer))\b'
        ]
        
        diseases = []
        text_lower = phenotype_text.lower()
        
        for pattern in pharmgkb_disease_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    diseases.extend([m.strip() for m in match if m.strip() and len(m.strip()) > 3])
                else:
                    if len(match.strip()) > 3:
                        diseases.append(match.strip())
        
        # Remove duplicates and clean up
        unique_diseases = []
        seen = set()
        for disease in diseases:
            disease_clean = disease.lower().strip()
            if disease_clean not in seen and len(disease_clean) > 3:
                seen.add(disease_clean)
                unique_diseases.append(disease)
        
        return unique_diseases[:5]  # Top 5 most relevant
    
    def map_phenotype_to_diseases(self, phenotype_text: str, gene_symbol: str = None, drug_name: str = None) -> Dict:
        """
        Comprehensive mapping: Clinical Finding + PharmGKB Disease extraction + Hierarchy
        Uses proper SNOMED CT post-coordinated expressions when possible
        
        Args:
            phenotype_text: Phenotype description
            gene_symbol: Gene symbol (e.g., CYP2C19)
            drug_name: Drug name (e.g., clopidogrel)
            
        Returns:
            Dictionary with clinical findings and associated diseases
        """
        result = {
            "phenotype_text": phenotype_text,
            "clinical_finding": None,
            "extracted_diseases": [],
            "pharmgkb_diseases": [],
            "snomed_disease_hierarchy": None
        }
        
        # 1. Get Clinical Finding with proper post-coordinated expression
        clinical_finding = self.search_clinical_finding(phenotype_text, gene_symbol, drug_name)
        if clinical_finding:
            result["clinical_finding"] = clinical_finding
            
            # 2. Get disease hierarchy from Clinical Finding (only if not post-coordinated)
            if clinical_finding.get("match_type") != "post_coordinated":
                hierarchy = self.get_snomed_hierarchy(clinical_finding["code"])
                if hierarchy:
                    result["snomed_disease_hierarchy"] = hierarchy
        
        # 3. Extract PharmGKB-specific diseases (prioritized)
        pharmgkb_diseases = self.extract_pharmgkb_diseases(phenotype_text)
        if pharmgkb_diseases:
            # Map each PharmGKB disease to SNOMED
            pharmgkb_mappings = []
            for disease in pharmgkb_diseases:
                disease_mapping = self.search_snomed(disease)
                if disease_mapping:
                    pharmgkb_mappings.append({
                        "extracted_text": disease,
                        "snomed_mapping": disease_mapping,
                        "source": "pharmgkb_phenotype"
                    })
            result["pharmgkb_diseases"] = pharmgkb_mappings
        
        # 4. Extract general disease entities from text (fallback)
        extracted_diseases = self.extract_disease_entities(phenotype_text)
        if extracted_diseases:
            # Map each extracted disease to SNOMED
            disease_mappings = []
            for disease in extracted_diseases:
                # Skip if already found by PharmGKB extraction
                if not any(disease.lower() in pgx["extracted_text"].lower() 
                          for pgx in result["pharmgkb_diseases"]):
                    disease_mapping = self.search_snomed(disease)
                    if disease_mapping:
                        disease_mappings.append({
                            "extracted_text": disease,
                            "snomed_mapping": disease_mapping,
                            "source": "general_extraction"
                        })
            result["extracted_diseases"] = disease_mappings
        
        return result

