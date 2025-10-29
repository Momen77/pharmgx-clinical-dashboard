from typing import Dict, List, Optional


# Minimal, literature-informed scaffolding for ethnicity-aware medication adjustments.
# This module provides NON-BINDING suggestions to surface population context.
# It should not be used as sole clinical guidance.


def suggest_ethnicity_adjustments(
    variants: List[Dict], patient_ethnicity: Optional[str]
) -> List[Dict]:
    """
    Produce ethnicity-aware medication adjustment hints based on common PGx patterns.

    Returns a list of dict entries with keys:
      - drug (str)
      - gene (str)
      - rationale (str)
      - adjustment (str)  # e.g., "consider alternative", "monitor closely", "↑ dose", "↓ dose"
      - strength (str)    # "suggestion" | "consider" | "info"

    Safety: Conservative statements; no hard doses here. For numeric dosing, integrate guideline engines.
    """
    if not patient_ethnicity:
        return []

    # Normalize ethnicity label to canonical buckets
    eth = patient_ethnicity

    # Collect quick gene/rs snapshot
    gene_to_rs = {}
    for v in variants:
        g = v.get("gene")
        rsid = v.get("rsid") or v.get("variant_id")
        if g and rsid:
            gene_to_rs.setdefault(g, set()).add(str(rsid))

    suggestions: List[Dict] = []

    # CYP2C19 ↔ Clopidogrel (Asian populations)
    # If patient is Asian and CYP2C19 variants present, flag alternative consideration
    if eth == "Asian" and ("CYP2C19" in gene_to_rs or _has_variant_of_gene(variants, "CYP2C19")):
        suggestions.append({
            "drug": "Clopidogrel",
            "gene": "CYP2C19",
            "adjustment": "consider alternative",
            "strength": "consider",
            "rationale": "CYP2C19 loss-of-function alleles are common in Asian populations; reduced activation of clopidogrel may occur."
        })

    # CYP3A5 ↔ Tacrolimus (African populations)
    if eth == "African" and ("CYP3A5" in gene_to_rs or _has_variant_of_gene(variants, "CYP3A5")):
        suggestions.append({
            "drug": "Tacrolimus",
            "gene": "CYP3A5",
            "adjustment": "↑ dose / monitor",
            "strength": "consider",
            "rationale": "High CYP3A5 expression is frequent in African populations; tacrolimus clearance may be higher. Monitor trough levels and adjust."
        })

    # CYP2D6 ↔ Codeine/Tramadol (variable in African/Asian; UM risk; conservative: monitor)
    if (eth in ("African", "Asian")) and ("CYP2D6" in gene_to_rs or _has_variant_of_gene(variants, "CYP2D6")):
        suggestions.append({
            "drug": "Codeine/Tramadol",
            "gene": "CYP2D6",
            "adjustment": "monitor closely",
            "strength": "suggestion",
            "rationale": "CYP2D6 activity distribution varies by population; risk of altered morphine exposure. Monitor efficacy and adverse events."
        })

    # Warfarin (population differences exist; keep conservative)
    if eth in ("Asian", "African"):
        suggestions.append({
            "drug": "Warfarin",
            "gene": "VKORC1/CYP2C9",
            "adjustment": "monitor closely",
            "strength": "suggestion",
            "rationale": "Warfarin sensitivity varies by ancestry; consider closer INR monitoring and genotype-guided dosing when available."
        })

    # Nil return if nothing matched
    return suggestions


def _has_variant_of_gene(variants: List[Dict], gene: str) -> bool:
    for v in variants:
        if v.get("gene") == gene:
            return True
    return False


