"""
Variant-Phenotype-Drug Linker with Conflict Detection
Links patient medications, conditions, and variants using SNOMED CT codes
Detects conflicts between patient medications and variant-affected drugs
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime
from utils.api_client import APIClient


class VariantPhenotypeLinker:
    """
    Links variants to phenotypes, drugs, and patient conditions
    Detects conflicts using SNOMED CT standardized codes
    """
    
    def __init__(self, bioportal_api_key: str = None):
        """
        Initialize linker
        
        Args:
            bioportal_api_key: BioPortal API key for SNOMED CT queries
        """
        self.bioportal_api_key = bioportal_api_key
        self.bioportal_base = "https://data.bioontology.org"
        
        if bioportal_api_key:
            self.bioportal_headers = {"Authorization": f"apikey token={bioportal_api_key}"}
        else:
            self.bioportal_headers = {}
        
        self.bioportal_client = APIClient(self.bioportal_base, rate_limit=10)
        self.rxnorm_client = APIClient("https://rxnav.nlm.nih.gov/REST", rate_limit=10)
        self.clinical_tables_client = APIClient("https://clinicaltables.nlm.nih.gov/api", rate_limit=10)
        
        # Cache for SNOMED CT mappings
        self._snomed_cache = {}
        self._drug_snomed_cache = {}
    
    def link_patient_profile_to_variants(
        self, 
        patient_profile: Dict,
        variants: List[Dict]
    ) -> Dict:
        """
        Main method: Link patient profile to variants and detect conflicts
        
        Args:
            patient_profile: Patient profile with conditions and medications
            variants: List of variants with PharmGKB data
            
        Returns:
            Enhanced profile with links and conflicts
        """
        print("\n" + "="*70)
        print("LINKING PATIENT PROFILE TO VARIANTS")
        print("="*70)
        
        # Extract patient data
        patient_conditions = patient_profile.get("clinical_information", {}).get("current_conditions", [])
        patient_medications = patient_profile.get("clinical_information", {}).get("current_medications", [])
        
        # Extract variant data
        variant_drugs = self._extract_variant_drugs(variants)
        variant_phenotypes = self._extract_variant_phenotypes(variants)
        variant_diseases = self._extract_variant_diseases(variants)
        
        # Map everything to SNOMED CT
        print("\n📋 Mapping patient conditions to SNOMED CT...")
        patient_condition_codes = self._map_conditions_to_snomed(patient_conditions)
        
        print(f"💊 Mapping {len(patient_medications)} patient medications to SNOMED CT...")
        patient_medication_codes = self._map_medications_to_snomed(patient_medications)
        
        print(f"🧬 Mapping {len(variant_drugs)} variant-affected drugs to SNOMED CT...")
        variant_drug_codes = self._map_drugs_to_snomed(variant_drugs)
        
        print(f"🏥 Mapping {len(variant_diseases)} variant-related diseases to SNOMED CT...")
        variant_disease_codes = self._map_diseases_to_snomed(variant_diseases)
        
        # Detect conflicts
        print("\n⚠️  Detecting conflicts...")
        conflicts = self._detect_conflicts(
            patient_medications=patient_medications,
            patient_medication_codes=patient_medication_codes,
            variant_drugs=variant_drugs,
            variant_drug_codes=variant_drug_codes,
            variants=variants
        )
        
        # Create links
        print("\n🔗 Creating links...")
        links = self._create_links(
            patient_conditions=patient_conditions,
            patient_condition_codes=patient_condition_codes,
            patient_medications=patient_medications,
            patient_medication_codes=patient_medication_codes,
            variant_drugs=variant_drugs,
            variant_drug_codes=variant_drug_codes,
            variant_diseases=variant_diseases,
            variant_disease_codes=variant_disease_codes,
            variants=variants,
            variant_phenotypes=variant_phenotypes
        )
        
        # Build summary
        summary = self._build_summary(
            conflicts=conflicts,
            links=links,
            patient_conditions=patient_conditions,
            patient_medications=patient_medications,
            variants=variants
        )
        
        return {
            "links": links,
            "conflicts": conflicts,
            "summary": summary,
            "snomed_mappings": {
                "patient_conditions": patient_condition_codes,
                "patient_medications": patient_medication_codes,
                "variant_drugs": variant_drug_codes,
                "variant_diseases": variant_disease_codes
            }
        }
    
    def _extract_variant_drugs(self, variants: List[Dict]) -> List[Dict]:
        """Extract all drugs affected by variants"""
        drugs = []
        drug_variants_map = {}
        
        for variant in variants:
            gene = variant.get("gene")
            variant_id = variant.get("variant_id") or variant.get("rsid")
            
            if "pharmgkb" in variant and "drugs" in variant["pharmgkb"]:
                for drug in variant["pharmgkb"]["drugs"]:
                    drug_name = drug.get("name")
                    if drug_name:
                        drug_key = drug_name.lower()
                        if drug_key not in drug_variants_map:
                            drug_variants_map[drug_key] = {
                                "name": drug_name,
                                "variants": [],
                                "recommendations": [],
                                "evidence_levels": []
                            }
                        
                        drug_variants_map[drug_key]["variants"].append({
                            "gene": gene,
                            "variant_id": variant_id,
                            "rsid": variant.get("rsid")
                        })
                        
                        if drug.get("recommendation"):
                            drug_variants_map[drug_key]["recommendations"].append({
                                "gene": gene,
                                "variant_id": variant_id,
                                "recommendation": drug.get("recommendation")
                            })
                        
                        if drug.get("evidence_level"):
                            drug_variants_map[drug_key]["evidence_levels"].append(drug.get("evidence_level"))
        
        return list(drug_variants_map.values())
    
    def _extract_variant_phenotypes(self, variants: List[Dict]) -> List[Dict]:
        """Extract phenotypes from variants"""
        phenotypes = []
        
        for variant in variants:
            gene = variant.get("gene")
            variant_id = variant.get("variant_id") or variant.get("rsid")
            
            # From PharmGKB
            if "pharmgkb" in variant:
                if "phenotypes" in variant["pharmgkb"]:
                    for phenotype_text in variant["pharmgkb"]["phenotypes"]:
                        phenotypes.append({
                            "text": phenotype_text,
                            "gene": gene,
                            "variant_id": variant_id,
                            "source": "PharmGKB"
                        })
                
                # From annotations
                if "annotations" in variant["pharmgkb"]:
                    for annotation in variant["pharmgkb"]["annotations"]:
                        if "allelePhenotypes" in annotation:
                            for allele_pheno in annotation["allelePhenotypes"]:
                                if "phenotype" in allele_pheno:
                                    phenotypes.append({
                                        "text": allele_pheno["phenotype"],
                                        "gene": gene,
                                        "variant_id": variant_id,
                                        "allele": allele_pheno.get("allele"),
                                        "source": "PharmGKB Annotation"
                                    })
            
            # From ClinVar
            if "clinvar" in variant and "phenotypes" in variant["clinvar"]:
                for phenotype_text in variant["clinvar"]["phenotypes"]:
                    phenotypes.append({
                        "text": phenotype_text,
                        "gene": gene,
                        "variant_id": variant_id,
                        "source": "ClinVar"
                    })
        
        return phenotypes
    
    def _extract_variant_diseases(self, variants: List[Dict]) -> List[Dict]:
        """Extract diseases associated with variants"""
        diseases = []
        seen = set()
        
        for variant in variants:
            gene = variant.get("gene")
            variant_id = variant.get("variant_id") or variant.get("rsid")
            
            # From disease associations
            if "disease_associations" in variant:
                for disease in variant["disease_associations"]:
                    disease_text = disease.get("name") or disease if isinstance(disease, str) else str(disease)
                    disease_key = f"{gene}:{disease_text}"
                    if disease_key not in seen:
                        seen.add(disease_key)
                        diseases.append({
                            "name": disease_text,
                            "gene": gene,
                            "variant_id": variant_id,
                            "source": disease.get("source", "Unknown")
                        })
            
            # From PharmGKB annotations
            if "pharmgkb" in variant and "annotations" in variant["pharmgkb"]:
                for annotation in variant["pharmgkb"]["annotations"]:
                    if "relatedDiseases" in annotation:
                        for disease_obj in annotation["relatedDiseases"]:
                            disease_name = disease_obj.get("name", "")
                            disease_key = f"{gene}:{disease_name}"
                            if disease_name and disease_key not in seen:
                                seen.add(disease_key)
                                diseases.append({
                                    "name": disease_name,
                                    "gene": gene,
                                    "variant_id": variant_id,
                                    "source": "PharmGKB"
                                })
        
        return diseases
    
    def _map_conditions_to_snomed(self, conditions: List[Dict]) -> Dict[str, Dict]:
        """Map patient conditions to SNOMED CT codes"""
        mappings = {}
        
        for condition in conditions:
            snomed_code = condition.get("snomed:code")
            condition_label = condition.get("rdfs:label") or condition.get("skos:prefLabel", "")
            
            if snomed_code:
                mappings[snomed_code] = {
                    "code": snomed_code,
                    "label": condition_label,
                    "condition": condition
                }
            else:
                # Try to search for SNOMED code
                label = condition_label or condition.get("search_term", "")
                if label:
                    snomed_result = self._search_snomed(label)
                    if snomed_result:
                        mappings[snomed_result["code"]] = {
                            "code": snomed_result["code"],
                            "label": snomed_result["label"],
                            "condition": condition
                        }
        
        return mappings
    
    def _map_medications_to_snomed(self, medications: List[Dict]) -> Dict[str, Dict]:
        """Map patient medications to SNOMED CT substance codes"""
        mappings = {}
        
        for med in medications:
            drug_name = (
                med.get("name")
                or med.get("drug_name")
                or med.get("rdfs:label")
                or med.get("schema:name")
                or ""
            )
            if not drug_name:
                continue
            
            # Check cache first
            cache_key = drug_name.lower()
            if cache_key in self._drug_snomed_cache:
                snomed_data = self._drug_snomed_cache[cache_key]
            else:
                snomed_data = self._search_drug_snomed(drug_name)
                if snomed_data:
                    self._drug_snomed_cache[cache_key] = snomed_data
            
            if snomed_data:
                mappings[drug_name] = {
                    "code": snomed_data["code"],
                    "label": snomed_data["label"],
                    "medication": med
                }
        
        return mappings
    
    def _map_drugs_to_snomed(self, drugs: List[Dict]) -> Dict[str, Dict]:
        """Map variant-affected drugs to SNOMED CT codes"""
        mappings = {}
        
        for drug_info in drugs:
            drug_name = drug_info.get("name")
            if not drug_name:
                continue
            
            # Check cache
            cache_key = drug_name.lower()
            if cache_key in self._drug_snomed_cache:
                snomed_data = self._drug_snomed_cache[cache_key]
            else:
                snomed_data = self._search_drug_snomed(drug_name)
                if snomed_data:
                    self._drug_snomed_cache[cache_key] = snomed_data
            
            if snomed_data:
                mappings[drug_name] = {
                    "code": snomed_data["code"],
                    "label": snomed_data["label"],
                    "drug_info": drug_info
                }
        
        return mappings
    
    def _map_diseases_to_snomed(self, diseases: List[Dict]) -> Dict[str, Dict]:
        """Map variant-related diseases to SNOMED CT codes"""
        mappings = {}
        
        for disease in diseases:
            disease_name = disease.get("name", "")
            if not disease_name:
                continue
            
            # Try to find SNOMED code
            snomed_result = self._search_snomed(disease_name)
            if snomed_result:
                disease_key = disease_name.lower()
                if disease_key not in mappings:
                    mappings[disease_key] = {
                        "code": snomed_result["code"],
                        "label": snomed_result["label"],
                        "disease": disease
                    }
        
        return mappings
    
    def _search_snomed(self, term: str) -> Optional[Dict]:
        """Search SNOMED CT for a term"""
        if not self.bioportal_api_key:
            return None
        
        cache_key = term.lower()
        if cache_key in self._snomed_cache:
            return self._snomed_cache[cache_key]
        
        try:
            url = f"{self.bioportal_base}/search"
            params = {
                "q": term,
                "ontologies": "SNOMEDCT",
                "apikey": self.bioportal_api_key,
                "pagesize": 1
            }
            
            response = self.bioportal_client.get(url, params=params, headers=self.bioportal_headers)
            
            if response and response.get("collection"):
                result = response["collection"][0]
                snomed_data = {
                    "code": result.get("@id", "").split("/")[-1],
                    "label": result.get("prefLabel", term)
                }
                self._snomed_cache[cache_key] = snomed_data
                return snomed_data
        except Exception as e:
            print(f"      Warning: Could not search SNOMED for '{term}': {e}")
        
        return None
    
    def _search_drug_snomed(self, drug_name: str) -> Optional[Dict]:
        """Search SNOMED CT for a drug/substance"""
        # Try substance search
        substance_result = self._search_snomed(f"{drug_name} (substance)")
        if substance_result:
            return substance_result
        
        # Try generic search
        return self._search_snomed(drug_name)
    
    def _detect_conflicts(
        self,
        patient_medications: List[Dict],
        patient_medication_codes: Dict[str, Dict],
        variant_drugs: List[Dict],
        variant_drug_codes: Dict[str, Dict],
        variants: List[Dict]
    ) -> List[Dict]:
        """Detect conflicts between patient medications and variant-affected drugs"""
        conflicts = []
        
        # Normalize drug names for comparison
        def _med_display_name(m: Dict) -> str:
            return (
                m.get("name")
                or m.get("drug_name")
                or m.get("rdfs:label")
                or m.get("schema:name")
                or ""
            )
        patient_drug_names = {_med_display_name(med).lower(): med for med in patient_medications}
        variant_drug_names = {drug.get("name", "").lower(): drug for drug in variant_drugs}
        
        # Check exact name matches
        for patient_drug_lower, patient_med in patient_drug_names.items():
            if patient_drug_lower in variant_drug_names:
                variant_drug = variant_drug_names[patient_drug_lower]
                conflict = self._analyze_drug_conflict(
                    patient_med=patient_med,
                    variant_drug=variant_drug,
                    variants=variants
                )
                if conflict:
                    conflicts.append(conflict)
        
        # Check SNOMED CT code matches (more accurate)
        patient_snomed_codes = {
            mapping["code"]: (name, mapping["medication"])
            for name, mapping in patient_medication_codes.items()
            if "code" in mapping
        }
        
        variant_snomed_codes = {
            mapping["code"]: (name, mapping["drug_info"])
            for name, mapping in variant_drug_codes.items()
            if "code" in mapping
        }
        
        # Find matching SNOMED codes
        matching_codes = set(patient_snomed_codes.keys()) & set(variant_snomed_codes.keys())
        
        for snomed_code in matching_codes:
            patient_name, patient_med = patient_snomed_codes[snomed_code]
            variant_name, variant_drug = variant_snomed_codes[snomed_code]
            
            # Skip if already found by name match
            if patient_name.lower() in variant_drug_names:
                continue
            
            conflict = self._analyze_drug_conflict(
                patient_med=patient_med,
                variant_drug=variant_drug,
                variants=variants
            )
            if conflict:
                conflict["match_method"] = "SNOMED_CT_CODE"
                conflict["snomed_code"] = snomed_code
                conflicts.append(conflict)
        
        return conflicts
    
    def _analyze_drug_conflict(
        self,
        patient_med: Dict,
        variant_drug: Dict,
        variants: List[Dict]
    ) -> Optional[Dict]:
        """Analyze if there's a conflict between patient medication and variant-affected drug"""
        drug_name = variant_drug.get("name", "")
        
        # Find variants affecting this drug
        affecting_variants = []
        for variant in variants:
            if "pharmgkb" in variant and "drugs" in variant["pharmgkb"]:
                for drug in variant["pharmgkb"]["drugs"]:
                    if drug.get("name", "").lower() == drug_name.lower():
                        affecting_variants.append({
                            "gene": variant.get("gene"),
                            "variant_id": variant.get("variant_id") or variant.get("rsid"),
                            "rsid": variant.get("rsid"),
                            "recommendation": drug.get("recommendation", ""),
                            "evidence_level": drug.get("evidence_level", ""),
                            "clinical_significance": variant.get("clinical_significance")
                        })
        
        if not affecting_variants:
            return None
        
        # Determine conflict severity
        severity = "INFO"
        conflict_keywords = [
            "contraindicated", "avoid", "do not use", "not recommended",
            "risk", "toxicity", "adverse", "reduced efficacy", "ineffective"
        ]
        
        all_recommendations = " ".join([
            v.get("recommendation", "").lower() for v in affecting_variants
        ])
        
        if any(keyword in all_recommendations for keyword in conflict_keywords):
            severity = "WARNING"
            if any(kw in all_recommendations for kw in ["contraindicated", "avoid", "do not use"]):
                severity = "CRITICAL"
        
        return {
            "drug_name": drug_name,
            "patient_medication": patient_med,
            "severity": severity,
            "affecting_variants": affecting_variants,
            "match_method": "EXACT_NAME",
            "recommendation": affecting_variants[0].get("recommendation", ""),
            "timestamp": datetime.now().isoformat()
        }
    
    def _create_links(
        self,
        patient_conditions: List[Dict],
        patient_condition_codes: Dict[str, Dict],
        patient_medications: List[Dict],
        patient_medication_codes: Dict[str, Dict],
        variant_drugs: List[Dict],
        variant_drug_codes: Dict[str, Dict],
        variant_diseases: List[Dict],
        variant_disease_codes: Dict[str, Dict],
        variants: List[Dict],
        variant_phenotypes: List[Dict]
    ) -> Dict:
        """Create comprehensive links between patient profile and variants"""
        links = {
            "medication_to_variant": [],
            "condition_to_disease": [],
            "variant_to_phenotype": [],
            "drug_to_variant": []
        }
        
        # Link medications to variants
        def _med_display_name2(m: Dict) -> str:
            return (
                m.get("name")
                or m.get("drug_name")
                or m.get("rdfs:label")
                or m.get("schema:name")
                or ""
            )
        patient_med_names = {_med_display_name2(med).lower(): med for med in patient_medications}

        # Helper to extract DrugBank id from a medication dict
        def _drugbank_id(med: Dict) -> Optional[str]:
            return med.get("drugbank:id") or med.get("drugbank_id")

        # Optional gene->metabolizer map if present on profile
        def _get_gene_metabolizer(gene_symbol: str) -> Tuple[Optional[str], Optional[str]]:
            # Try known locations in the profile for phenotype/diplotype
            phenotype = None
            diplotype = None
            try:
                # Some profiles may carry a per-gene block
                per_gene = {}
                if isinstance(variants, list):
                    # If any variant objects embed metabolizer info per gene (rare)
                    for v in variants:
                        if v.get("gene") == gene_symbol:
                            mp = v.get("metabolizer_phenotype") or {}
                            if isinstance(mp, dict):
                                phenotype = phenotype or mp.get("phenotype")
                                diplotype = diplotype or mp.get("diplotype")
                # Fallback: none
            except Exception:
                pass
            return phenotype, diplotype

        # Exact NAME match links
        for variant_drug in variant_drugs:
            drug_name = variant_drug.get("name", "").lower()
            if drug_name in patient_med_names:
                patient_med = patient_med_names[drug_name]
                for variant_ref in variant_drug.get("variants", []):
                    gene_symbol = variant_ref.get("gene")
                    phenotype_label, diplotype_label = _get_gene_metabolizer(gene_symbol or "")
                    links["medication_to_variant"].append({
                        "medication": _med_display_name2(patient_med),
                        "drugbank_id": _drugbank_id(patient_med),
                        "gene": gene_symbol,
                        "diplotype": diplotype_label,
                        "phenotype": phenotype_label,
                        "interaction_type": variant_drug.get("interaction_type"),
                        "clinical_significance": (variant_drug.get("evidence_levels") or [None])[0],
                        "recommendation": (variant_drug.get("recommendations") or [{}])[0].get("recommendation"),
                        "variant": variant_ref,
                        "drug_name": variant_drug.get("name"),
                        "link_type": "PATIENT_MEDICATION_AFFECTED_BY_VARIANT",
                        "match_method": "EXACT_NAME"
                    })

        # SNOMED CT CODE match links (more robust)
        patient_snomed_codes = {
            mapping.get("code"): mapping.get("medication")
            for mapping in patient_medication_codes.values()
            if isinstance(mapping, dict) and mapping.get("code") and mapping.get("medication")
        }
        variant_snomed_codes = {
            mapping.get("code"): mapping.get("drug_info")
            for mapping in variant_drug_codes.values()
            if isinstance(mapping, dict) and mapping.get("code") and mapping.get("drug_info")
        }

        matching_codes = set(patient_snomed_codes.keys()) & set(variant_snomed_codes.keys())
        for snomed_code in matching_codes:
            patient_med = patient_snomed_codes[snomed_code]
            variant_drug = variant_snomed_codes[snomed_code]
            for variant_ref in variant_drug.get("variants", []):
                gene_symbol = variant_ref.get("gene")
                phenotype_label, diplotype_label = _get_gene_metabolizer(gene_symbol or "")
                links["medication_to_variant"].append({
                    "medication": _med_display_name2(patient_med),
                    "drugbank_id": _drugbank_id(patient_med),
                    "gene": gene_symbol,
                    "diplotype": diplotype_label,
                    "phenotype": phenotype_label,
                    "interaction_type": variant_drug.get("interaction_type"),
                    "clinical_significance": (variant_drug.get("evidence_levels") or [None])[0],
                    "recommendation": (variant_drug.get("recommendations") or [{}])[0].get("recommendation"),
                    "variant": variant_ref,
                    "drug_name": variant_drug.get("name"),
                    "snomed_code": snomed_code,
                    "link_type": "PATIENT_MEDICATION_AFFECTED_BY_VARIANT",
                    "match_method": "SNOMED_CT_CODE"
                })
        
        # Link conditions to variant-related diseases (using SNOMED CT)
        patient_condition_snomed = {
            mapping["code"]: mapping["condition"]
            for mapping in patient_condition_codes.values()
            if "code" in mapping
        }
        
        variant_disease_snomed = {
            mapping["code"]: mapping["disease"]
            for mapping in variant_disease_codes.values()
            if "code" in mapping
        }
        
        matching_disease_codes = set(patient_condition_snomed.keys()) & set(variant_disease_snomed.keys())
        for snomed_code in matching_disease_codes:
            links["condition_to_disease"].append({
                "patient_condition": patient_condition_snomed[snomed_code],
                "variant_disease": variant_disease_snomed[snomed_code],
                "snomed_code": snomed_code,
                "link_type": "CONDITION_MATCHES_VARIANT_DISEASE"
            })
        
        # Link variants to phenotypes
        for phenotype in variant_phenotypes:
            links["variant_to_phenotype"].append({
                "variant_id": phenotype.get("variant_id"),
                "gene": phenotype.get("gene"),
                "phenotype_text": phenotype.get("text"),
                "source": phenotype.get("source"),
                "link_type": "VARIANT_ASSOCIATED_WITH_PHENOTYPE"
            })
        
        # Link drugs to variants (drug-centric), include SNOMED and evidence context if available
        for variant_drug in variant_drugs:
            snomed_entry = variant_drug_codes.get(variant_drug.get("name")) or {}
            snomed_code = snomed_entry.get("code") if isinstance(snomed_entry, dict) else None
            for variant_ref in variant_drug.get("variants", []):
                links["drug_to_variant"].append({
                    "drug_name": variant_drug.get("name"),
                    "snomed_code": snomed_code,
                    "variant": variant_ref,
                    "interaction_type": variant_drug.get("interaction_type"),
                    "recommendations": variant_drug.get("recommendations", []),
                    "evidence_levels": variant_drug.get("evidence_levels", []),
                    "link_type": "DRUG_AFFECTED_BY_VARIANT"
                })
        
        return links
    
    def _build_summary(
        self,
        conflicts: List[Dict],
        links: Dict,
        patient_conditions: List[Dict],
        patient_medications: List[Dict],
        variants: List[Dict]
    ) -> Dict:
        """Build summary of links and conflicts"""
        critical_conflicts = [c for c in conflicts if c.get("severity") == "CRITICAL"]
        warning_conflicts = [c for c in conflicts if c.get("severity") == "WARNING"]
        
        return {
            "total_links": {
                "medication_to_variant": len(links.get("medication_to_variant", [])),
                "condition_to_disease": len(links.get("condition_to_disease", [])),
                "variant_to_phenotype": len(links.get("variant_to_phenotype", [])),
                "drug_to_variant": len(links.get("drug_to_variant", []))
            },
            "conflicts": {
                "total": len(conflicts),
                "critical": len(critical_conflicts),
                "warnings": len(warning_conflicts),
                "info": len(conflicts) - len(critical_conflicts) - len(warning_conflicts)
            },
            "patient_summary": {
                "conditions": len(patient_conditions),
                "medications": len(patient_medications)
            },
            "variant_summary": {
                "total_variants": len(variants),
                "variants_with_drug_data": len([v for v in variants if "pharmgkb" in v and "drugs" in v.get("pharmgkb", {})])
            },
            "analysis_timestamp": datetime.now().isoformat()
        }

