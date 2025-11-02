"""
Robust data extraction utilities for JSON-LD profile structures.
Handles multiple key name variations, nested structures, and JSON-LD prefixes.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


def extract_field(
    obj: Dict,
    primary_key: str,
    fallback_keys: Optional[List[str]] = None,
    default: Any = None,
    log_missing: bool = False,
    obj_name: str = "object"
) -> Any:
    """
    Extract field with multiple fallback attempts.
    
    Args:
        obj: Dictionary to extract from
        primary_key: Primary key to try first
        fallback_keys: List of alternative keys to try
        default: Default value if all keys fail
        log_missing: Whether to log when field is not found
        obj_name: Name of object for logging purposes
    
    Returns:
        Extracted value or default
    """
    if fallback_keys is None:
        fallback_keys = []
    
    # Try primary key
    value = obj.get(primary_key)
    if value is not None:
        return value
    
    # Try fallback keys
    for key in fallback_keys:
        value = obj.get(key)
        if value is not None:
            return value
    
    # Log if requested
    if log_missing:
        logger.debug(f"Field '{primary_key}' not found in {obj_name} (tried: {primary_key}, {', '.join(fallback_keys)})")
    
    return default


def extract_nested_field(
    obj: Dict,
    path: List[str],
    default: Any = None
) -> Any:
    """
    Extract field from nested structure using path.
    
    Args:
        obj: Dictionary to extract from
        path: List of keys representing path (e.g., ['hasGene', 'gene_symbol'])
        default: Default value if path doesn't exist
    
    Returns:
        Extracted value or default
    """
    current = obj
    for key in path:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current if current is not None else default


def extract_from_jsonb(
    obj: Dict,
    jsonb_field: str,
    field_name: str,
    default: Any = None
) -> Any:
    """
    Extract field from JSONB field (like raw_uniprot_data, raw_pharmgkb_data).
    
    Args:
        obj: Dictionary containing JSONB field
        jsonb_field: Name of JSONB field
        field_name: Field to extract from JSONB
        default: Default value if not found
    
    Returns:
        Extracted value or default
    """
    jsonb_data = obj.get(jsonb_field)
    if not jsonb_data:
        return default
    
    # Parse if string
    if isinstance(jsonb_data, str):
        try:
            jsonb_data = json.loads(jsonb_data)
        except json.JSONDecodeError:
            logger.debug(f"Could not parse JSONB field {jsonb_field}")
            return default
    
    # Extract field
    if isinstance(jsonb_data, dict):
        return jsonb_data.get(field_name, default)
    
    return default


def extract_variant_gene(variant: Dict) -> Optional[str]:
    """Extract gene symbol from variant - PRIORITIZES raw_data where available."""
    # ✅ STEP 1: Check direct key (variant_info has "gene" at top level)
    gene = extract_field(
        variant, "gene",
        fallback_keys=["gene_symbol", "geneSymbol", "hasGene"],
        obj_name="variant"
    )
    
    if gene and isinstance(gene, str):
        return gene
    
    # Handle nested structure
    if isinstance(gene, dict):
        gene = extract_field(
            gene, "gene_symbol",
            fallback_keys=["symbol", "name", "@id"],
            obj_name="gene_object"
        )
        if gene and isinstance(gene, str):
            return gene
    
    # ✅ STEP 2: Check raw_data (where original variant data exists)
    if variant.get("raw_data"):
        raw_variant = variant["raw_data"]
        raw_gene = raw_variant.get("gene")
        if raw_gene and isinstance(raw_gene, str):
            logger.debug(f"Found gene in raw_data: {raw_gene}")
            return raw_gene
    
    # ✅ STEP 3: Extract from JSONB (for patient_variants table)
    if not gene:
        gene = extract_from_jsonb(variant, "raw_uniprot_data", "gene")
        if gene and isinstance(gene, str):
            return gene
    
    return None


def extract_variant_field(
    variant: Dict,
    field_name: str,
    fallback_keys: Optional[List[str]] = None,
    camel_case: Optional[str] = None,
    nested_paths: Optional[List[List[str]]] = None,
    jsonb_fields: Optional[List[str]] = None,
    default: Any = None,
    check_raw_data: bool = True
) -> Any:
    """
    Comprehensive variant field extraction.
    
    Args:
        variant: Variant dictionary (from pipeline, may have "raw_data" key)
        field_name: Primary field name (snake_case)
        fallback_keys: List of alternative keys to try
        camel_case: CamelCase alternative (added to fallback_keys)
        nested_paths: List of nested paths to try
        jsonb_fields: List of JSONB fields to check
        default: Default value
        check_raw_data: If True, also check variant["raw_data"] as final fallback
    """
    if fallback_keys is None:
        fallback_keys = []
    if camel_case:
        fallback_keys.append(camel_case)
    
    # ✅ STEP 1: Try direct extraction from variant_info (pipeline structure)
    value = extract_field(variant, field_name, fallback_keys=fallback_keys, default=None, obj_name="variant")
    if value is not None:
        return value
    
    # ✅ STEP 2: Try nested paths
    if nested_paths:
        for path in nested_paths:
            value = extract_nested_field(variant, path, default=None)
            if value is not None:
                return value
    
    # ✅ STEP 3: Try JSONB fields (for patient_variants table that has raw_uniprot_data)
    if jsonb_fields:
        for jsonb_field in jsonb_fields:
            value = extract_from_jsonb(variant, jsonb_field, field_name, default=None)
            if value is not None:
                return value
            if camel_case:
                value = extract_from_jsonb(variant, jsonb_field, camel_case, default=None)
                if value is not None:
                    return value
    
    # ✅ STEP 4: CRITICAL - Check raw_data (full original variant from phase1/phase2)
    # Pipeline stores full variant in variant["raw_data"] with all UniProt/PharmGKB data
    if check_raw_data and variant.get("raw_data"):
        raw_variant = variant["raw_data"]
        # Recursively try extraction from raw_data (but don't check raw_data again to avoid loop)
        value = extract_variant_field(
            raw_variant, field_name,
            fallback_keys=fallback_keys,
            camel_case=camel_case,
            nested_paths=nested_paths,
            jsonb_fields=None,  # Don't check JSONB in raw_data
            default=None,
            check_raw_data=False  # Prevent infinite recursion
        )
        if value is not None:
            return value
    
    return default


def extract_genomic_locations(variant: Dict) -> List[Dict]:
    """Extract genomic locations - PRIORITIZES raw_data (where it actually exists in pipeline)"""
    # ✅ STEP 1: CRITICAL - Check raw_data FIRST (this is where genomic locations actually exist!)
    if variant.get("raw_data"):
        raw_variant = variant["raw_data"]
        raw_locations = extract_field(
            raw_variant, "genomicLocation",
            fallback_keys=["genomicLocations", "locations"],
            default=None
        )
        if raw_locations:
            logger.debug(f"Found genomic locations in raw_data for variant {variant.get('variant_id')}")
            if isinstance(raw_locations, dict):
                return [raw_locations]
            if isinstance(raw_locations, list):
                return raw_locations
    
    # ✅ STEP 2: Check direct key (fallback)
    locations = extract_field(
        variant, "genomicLocation",
        fallback_keys=["genomicLocations", "genomic_location", "location", "hasLocation"],
        default=None,
        obj_name="variant"
    )
    
    # Handle dict (single location)
    if isinstance(locations, dict):
        return [locations]
    
    # Handle list
    if isinstance(locations, list) and locations:
        return locations
    
    # Try nested
    nested = extract_nested_field(variant, ["hasLocation"])
    if nested:
        return [nested] if isinstance(nested, dict) else nested if isinstance(nested, list) else []
    
    # Try from JSONB (for patient_variants table)
    raw_locations = extract_from_jsonb(variant, "raw_uniprot_data", "genomicLocation")
    if raw_locations:
        return raw_locations if isinstance(raw_locations, list) else [raw_locations]
    
    return []


def extract_uniprot_data(variant: Dict) -> Dict:
    """Extract UniProt-related data - PRIORITIZES raw_data (where it actually exists in pipeline)"""
    # ✅ STEP 1: CRITICAL - Check raw_data FIRST (this is where UniProt data actually exists!)
    if variant.get("raw_data"):
        raw_variant = variant["raw_data"]
        raw_has_data = (
            raw_variant.get("alternativeSequence") or
            raw_variant.get("codon") or
            raw_variant.get("molecularConsequence") or
            raw_variant.get("wildType") or
            raw_variant.get("begin") or
            raw_variant.get("end")
        )
        if raw_has_data:
            logger.debug(f"Found UniProt data in raw_data for variant {variant.get('variant_id')}")
            return {
                "alternativeSequence": raw_variant.get("alternativeSequence"),
                "begin": raw_variant.get("begin") or raw_variant.get("beginPosition"),
                "end": raw_variant.get("end") or raw_variant.get("endPosition"),
                "codon": raw_variant.get("codon"),
                "molecularConsequence": raw_variant.get("molecularConsequence") or raw_variant.get("consequence_type"),
                "wildType": raw_variant.get("wildType") or raw_variant.get("wild_type"),
                "somaticStatus": raw_variant.get("somaticStatus") or raw_variant.get("somatic_status"),
                "sourceType": raw_variant.get("sourceType") or raw_variant.get("source_type")
            }
    
    # ✅ STEP 2: Check direct keys in variant_info (fallback)
    has_uniprot_data = (
        variant.get("alternativeSequence") or
        variant.get("codon") or
        variant.get("molecularConsequence") or
        variant.get("wildType")
    )
    
    if has_uniprot_data:
        return {
            "alternativeSequence": variant.get("alternativeSequence"),
            "begin": variant.get("begin") or variant.get("beginPosition"),
            "end": variant.get("end") or variant.get("endPosition"),
            "codon": variant.get("codon"),
            "molecularConsequence": variant.get("molecularConsequence") or variant.get("consequence_type"),
            "wildType": variant.get("wildType") or variant.get("wild_type"),
            "somaticStatus": variant.get("somaticStatus") or variant.get("somatic_status"),
            "sourceType": variant.get("sourceType") or variant.get("source_type")
        }
    
    # ✅ STEP 3: Try from raw_uniprot_data JSONB (for patient_variants table)
    raw_data = variant.get("raw_uniprot_data")
    if isinstance(raw_data, str):
        try:
            raw_data = json.loads(raw_data)
        except:
            pass
    
    if isinstance(raw_data, dict) and raw_data:
        return raw_data
    
    return {}


def extract_xrefs(variant: Dict) -> List[Dict]:
    """Extract cross-references - PRIORITIZES raw_data (where it actually exists in pipeline)"""
    # ✅ STEP 1: CRITICAL - Check raw_data FIRST (this is where xrefs actually exist!)
    if variant.get("raw_data"):
        raw_variant = variant["raw_data"]
        raw_xrefs = raw_variant.get("xrefs")
        if raw_xrefs:
            logger.debug(f"Found xrefs in raw_data for variant {variant.get('variant_id')}: {len(raw_xrefs) if isinstance(raw_xrefs, list) else 1}")
            if isinstance(raw_xrefs, list) and raw_xrefs:
                return raw_xrefs
            if isinstance(raw_xrefs, dict):
                return [raw_xrefs]
    
    # ✅ STEP 2: Check direct key (fallback)
    xrefs = extract_field(
        variant, "xrefs",
        fallback_keys=["cross_references", "references", "hasReference"],
        default=None,
        obj_name="variant"
    )
    
    if isinstance(xrefs, list) and xrefs:
        return xrefs
    
    if isinstance(xrefs, dict):
        # Convert dict to list
        return [xrefs]
    
    # Try from JSONB (for patient_variants table)
    raw_xrefs = extract_from_jsonb(variant, "raw_uniprot_data", "xrefs")
    if raw_xrefs:
        return raw_xrefs if isinstance(raw_xrefs, list) else [raw_xrefs]
    
    return []


def extract_predictions(variant: Dict) -> List[Dict]:
    """Extract variant predictions with fallbacks."""
    predictions = extract_field(
        variant, "predictions",
        fallback_keys=["prediction_scores", "variant_predictions", "predictions_data"],
        default=[],
        obj_name="variant"
    )
    
    # Handle dict format (tool -> prediction mapping)
    if isinstance(predictions, dict):
        predictions_list = []
        for tool, pred_data in predictions.items():
            if isinstance(pred_data, dict):
                predictions_list.append({
                    "tool": tool,
                    "prediction": pred_data.get("prediction"),
                    "score": pred_data.get("score"),
                    "confidence": pred_data.get("confidence")
                })
            else:
                predictions_list.append({
                    "tool": tool,
                    "prediction": str(pred_data),
                    "score": None,
                    "confidence": None
                })
        return predictions_list
    
    if isinstance(predictions, list):
        return predictions
    
    return []


def extract_clinvar_data(variant: Dict) -> List[Dict]:
    """Extract ClinVar data - PRIORITIZES raw_data (where it actually exists in pipeline)"""
    # ✅ STEP 1: CRITICAL - Check raw_data FIRST (this is where ClinVar data actually exists!)
    if variant.get("raw_data"):
        raw_variant = variant["raw_data"]
        raw_clinvar = raw_variant.get("clinvar")
        if raw_clinvar:
            logger.debug(f"Found ClinVar data in raw_data for variant {variant.get('variant_id')}")
            # Handle list
            if isinstance(raw_clinvar, list):
                return raw_clinvar
            # Handle dict
            if isinstance(raw_clinvar, dict):
                # Check for submissions key
                if raw_clinvar.get("submissions"):
                    subs = raw_clinvar["submissions"]
                    return subs if isinstance(subs, list) else [subs]
                # Single submission as dict
                if raw_clinvar.get("clinvar_id") or raw_clinvar.get("id"):
                    return [raw_clinvar]
    
    # ✅ STEP 2: Check direct key (fallback)
    clinvar = extract_field(
        variant, "clinvar",
        fallback_keys=["clinvar_data", "clinvar_submissions", "clinicalVariants"],
        default=None,
        obj_name="variant"
    )
    
    if not clinvar:
        return []
    
    # Handle list
    if isinstance(clinvar, list):
        return clinvar
    
    # Handle dict
    if isinstance(clinvar, dict):
        # Check for submissions key
        if clinvar.get("submissions"):
            subs = clinvar["submissions"]
            return subs if isinstance(subs, list) else [subs]
        
        # Single submission as dict
        if clinvar.get("clinvar_id") or clinvar.get("id"):
            return [clinvar]
    
    return []


def extract_pharmgkb_data(variant: Dict) -> Dict:
    """Extract PharmGKB data - PRIORITIZES raw_data (where it actually exists in pipeline)"""
    # ✅ STEP 1: CRITICAL - Check raw_data FIRST (this is where PharmGKB data actually exists!)
    # Pipeline stores full variant in variant["raw_data"] with ALL PharmGKB data
    if variant.get("raw_data"):
        raw_variant = variant["raw_data"]
        raw_pharmgkb = raw_variant.get("pharmgkb")
        if isinstance(raw_pharmgkb, dict) and raw_pharmgkb:
            logger.debug(f"Found PharmGKB data in raw_data for variant {variant.get('variant_id')}")
            return raw_pharmgkb
    
    # ✅ STEP 2: Check direct key in variant_info (might exist in some cases)
    pharmgkb = extract_field(
        variant, "pharmgkb",
        fallback_keys=["pharmgkb_data", "annotations", "pharmgkb_annotations"],
        default=None,
        obj_name="variant"
    )
    
    if isinstance(pharmgkb, dict) and pharmgkb:
        return pharmgkb
    
    # ✅ STEP 3: Try from raw_pharmgkb_data JSONB (for patient_variants table)
    raw_pharmgkb = variant.get("raw_pharmgkb_data")
    if isinstance(raw_pharmgkb, str):
        try:
            raw_pharmgkb = json.loads(raw_pharmgkb)
        except:
            pass
    
    if isinstance(raw_pharmgkb, dict) and raw_pharmgkb:
        return raw_pharmgkb
    
    return {}


def extract_ethnicity_adjustments(profile: Dict) -> List[Dict]:
    """Extract ethnicity medication adjustments with fallbacks."""
    adjustments = extract_field(
        profile, "ethnicity_medication_adjustments",
        fallback_keys=[
            "ethnicity_adjustments",
            "ethnicityMedicationAdjustments",
            "variant_linking.ethnicity_adjustments",
            "clinical_information.ethnicity_adjustments"
        ],
        default=[],
        obj_name="profile"
    )
    
    if isinstance(adjustments, list):
        return adjustments
    
    # Try nested locations
    variant_linking = profile.get("variant_linking", {})
    if isinstance(variant_linking, dict):
        nested = variant_linking.get("ethnicity_adjustments")
        if nested:
            return nested if isinstance(nested, list) else [nested]
    
    clinical_info = profile.get("clinical_information", {})
    if isinstance(clinical_info, dict):
        nested = clinical_info.get("ethnicity_adjustments")
        if nested:
            return nested if isinstance(nested, list) else [nested]
    
    return []


def extract_population_frequencies(variant: Dict) -> Dict:
    """Extract population frequencies with fallbacks."""
    freqs = extract_field(
        variant, "population_frequencies",
        fallback_keys=["populationFrequencies", "frequencies", "allele_frequencies"],
        default={},
        obj_name="variant"
    )
    
    if isinstance(freqs, dict):
        return freqs
    
    # Try from variant_linking
    variant_linking = variant.get("variant_linking", {})
    if isinstance(variant_linking, dict):
        nested_freqs = variant_linking.get("population_frequencies")
        if isinstance(nested_freqs, dict):
            return nested_freqs
    
    return {}


def log_extraction_stats(extracted: int, expected: int, table_name: str):
    """Log extraction statistics for debugging."""
    if extracted == 0 and expected > 0:
        logger.warning(f"⚠️ {table_name}: Expected {expected} records but extracted 0")
    elif extracted < expected:
        logger.info(f"ℹ️ {table_name}: Extracted {extracted}/{expected} records")
    else:
        logger.debug(f"✓ {table_name}: Extracted {extracted} records")

