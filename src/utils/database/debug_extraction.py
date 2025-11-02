"""
Debug utilities for data extraction - Logs what data is found vs missing
"""

import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def log_variant_structure(variant: Dict, variant_index: int = 0):
    """Log the actual structure of a variant for debugging"""
    logger.info(f"🔍 VARIANT #{variant_index} STRUCTURE:")
    logger.info(f"   Keys: {list(variant.keys())}")
    
    # Check for key fields
    logger.info(f"   gene: {variant.get('gene')}")
    logger.info(f"   variant_id: {variant.get('variant_id')}")
    logger.info(f"   rsid: {variant.get('rsid')}")
    logger.info(f"   clinical_significance: {variant.get('clinical_significance')}")
    
    # Check raw_data
    if variant.get("raw_data"):
        raw_variant = variant["raw_data"]
        logger.info(f"   ✅ HAS raw_data with keys: {list(raw_variant.keys())[:10]}...")
        logger.info(f"   raw_data.gene: {raw_variant.get('gene')}")
        logger.info(f"   raw_data.xrefs: {len(raw_variant.get('xrefs', []))} xrefs")
        logger.info(f"   raw_data.genomicLocation: {raw_variant.get('genomicLocation') is not None}")
        logger.info(f"   raw_data.pharmgkb: {raw_variant.get('pharmgkb') is not None}")
        if raw_variant.get("pharmgkb"):
            pharmgkb = raw_variant["pharmgkb"]
            logger.info(f"      pharmgkb.keys: {list(pharmgkb.keys()) if isinstance(pharmgkb, dict) else 'Not a dict'}")
            logger.info(f"      pharmgkb.annotations: {len(pharmgkb.get('annotations', []))}")
            logger.info(f"      pharmgkb.drugs: {len(pharmgkb.get('drugs', []))}")
    else:
        logger.warning(f"   ❌ NO raw_data field!")
    
    # Check other fields
    logger.info(f"   drugs: {len(variant.get('drugs', []))}")
    logger.info(f"   pharmgkb: {variant.get('pharmgkb') is not None}")
    logger.info(f"   clinvar: {variant.get('clinvar') is not None}")
    logger.info(f"   population_frequencies: {variant.get('population_frequencies') is not None}")
    logger.info(f"   predictions: {variant.get('predictions') is not None}")


def log_profile_structure(profile: Dict):
    """Log the structure of the profile for debugging"""
    logger.info("🔍 PROFILE STRUCTURE:")
    logger.info(f"   Keys: {list(profile.keys())}")
    
    variants = profile.get("variants", [])
    logger.info(f"   variants count: {len(variants)}")
    
    variant_linking = profile.get("variant_linking", {})
    logger.info(f"   variant_linking exists: {variant_linking is not None}")
    if variant_linking:
        logger.info(f"   variant_linking.keys: {list(variant_linking.keys())}")
        logger.info(f"   variant_linking.conflicts: {len(variant_linking.get('conflicts', []))}")
        logger.info(f"   variant_linking.links: {variant_linking.get('links') is not None}")
    
    ethnicity_adjustments = profile.get("ethnicity_medication_adjustments", [])
    logger.info(f"   ethnicity_medication_adjustments: {len(ethnicity_adjustments)}")
    
    literature_summary = profile.get("literature_summary", {})
    logger.info(f"   literature_summary exists: {literature_summary is not None}")
    if literature_summary:
        logger.info(f"   literature_summary.keys: {list(literature_summary.keys())}")


def log_extraction_result(table_name: str, expected_count: int, actual_count: int, sample_data: Any = None):
    """Log extraction results"""
    if actual_count == 0 and expected_count > 0:
        logger.warning(f"⚠️ {table_name}: Expected {expected_count} but got 0 records")
    elif actual_count < expected_count:
        logger.info(f"ℹ️ {table_name}: Got {actual_count}/{expected_count} records")
    else:
        logger.info(f"✅ {table_name}: Got {actual_count} records")
    
    if sample_data and actual_count > 0:
        logger.debug(f"   Sample data keys: {list(sample_data.keys()) if isinstance(sample_data, dict) else 'Not a dict'}")


def log_field_extraction(field_name: str, found: bool, value: Any, source: str = "direct"):
    """Log whether a field was found and where"""
    if found:
        logger.debug(f"   ✅ {field_name}: Found in {source} = {str(value)[:100]}")
    else:
        logger.debug(f"   ❌ {field_name}: NOT FOUND in {source}")

