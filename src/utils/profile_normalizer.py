"""
Profile normalization utility: converts a dashboard-entered patient profile into the
canonical JSON-LD structure used by the pipeline (foaf/schema/contexts), preserving
provided fields and filling required structure so it matches generated profiles.
"""
from __future__ import annotations

from typing import Dict, Any, Optional
from datetime import datetime
import uuid

# Canonical @context used by pipeline-generated profiles
_CANONICAL_CONTEXT = {
    "foaf": "http://xmlns.com/foaf/0.1/",
    "schema": "http://schema.org/",
    "pgx": "http://pgx-kg.org/",
    "sdisco": "http://ugent.be/sdisco/",
    "snomed": "http://snomed.info/id/",
    "drugbank": "https://go.drugbank.com/drugs/",
    "ugent": "http://ugent.be/person/",
    "dbsnp": "https://identifiers.org/dbsnp/",
    "ncbigene": "https://identifiers.org/ncbigene/",
    "clinpgx": "https://www.clinpgx.org/haplotype/",
    "gn": "http://www.geonames.org/ontology#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "xsd": "http://www.w3.org/2001/XMLSchema#"
}


def _safe_id_from_profile(profile: Dict[str, Any]) -> str:
    # Prefer dashboard MRN if available; otherwise a deterministic UUID
    mrn = (
        profile.get("demographics", {}).get("mrn")
        or profile.get("mrn")
        or profile.get("identifier")
    )
    if mrn:
        return str(mrn)
    return f"AUTO_{str(uuid.uuid4())[:8]}"


def normalize_dashboard_profile_to_jsonld(dashboard_profile: Dict[str, Any]) -> Dict[str, Any]:
    """Return a JSON-LD patient profile with the exact structure the pipeline emits.

    - Preserves all dashboard-provided clinical info inside clinical_information
    - Adds @context, @id, @type, identifier, dateCreated, name, description
    - Sets dashboard_source: true for traceability
    - Leaves pharmacogenomics_profile and variants empty for the pipeline to fill
    """
    if not isinstance(dashboard_profile, dict):
        dashboard_profile = {}

    patient_id = _safe_id_from_profile(dashboard_profile)

    # Build canonical envelope
    jsonld: Dict[str, Any] = {
        "@context": {**_CANONICAL_CONTEXT},
        "@id": f"http://ugent.be/person/{patient_id}",
        "@type": ["foaf:Person", "schema:Person", "schema:Patient"],
        "identifier": patient_id,
        "patient_id": patient_id,
        "name": "Comprehensive Pharmacogenomics Patient Profile",
        "description": "Dashboard-provided clinical profile (normalized to canonical schema)",
        "dateCreated": datetime.now().isoformat(),
        # Strict location for clinical info as used downstream
        "clinical_information": {},
        # Initialized; pipeline fills these later
        "pharmacogenomics_profile": {
            "genes_analyzed": [],
            "total_variants": 0,
            "variants_by_gene": {},
            "affected_drugs": [],
            "associated_diseases": [],
            "clinical_summary": {},
            "literature_summary": {}
        },
        "variants": [],
        "dashboard_source": True,
        "dataSource": "Dashboard → PGx pipeline"
    }

    # Map common dashboard fields into clinical_information using schema/foaf
    ci: Dict[str, Any] = {}
    demo = dashboard_profile.get("demographics", {}) or {}
    if demo:
        first = demo.get("first_name") or demo.get("givenName") or demo.get("schema:givenName")
        last = demo.get("last_name") or demo.get("familyName") or demo.get("schema:familyName")
        birth_date = demo.get("birthDate") or demo.get("schema:birthDate")
        gender = demo.get("gender") or demo.get("schema:gender")
        weight = demo.get("weight") or demo.get("schema:weight")
        height = demo.get("height") or demo.get("schema:height")
        age = demo.get("age")

        ci_demo: Dict[str, Any] = {
            "@id": "http://ugent.be/person/demographics",
            "foaf:firstName": first or "",
            "foaf:familyName": last or "",
            "schema:givenName": first or "",
            "schema:familyName": last or "",
        }
        if birth_date:
            ci_demo["schema:birthDate"] = birth_date
        if gender:
            ci_demo["schema:gender"] = gender
        if isinstance(weight, (int, float)):
            ci_demo["schema:weight"] = {
                "@type": "schema:QuantitativeValue",
                "schema:value": float(weight),
                "schema:unitCode": "kg",
                "schema:unitText": "kilograms"
            }
        if isinstance(height, (int, float)):
            ci_demo["schema:height"] = {
                "@type": "schema:QuantitativeValue",
                "schema:value": float(height),
                "schema:unitCode": "cm",
                "schema:unitText": "centimeters"
            }
        if isinstance(age, (int, float)):
            ci_demo["age"] = int(age)
        if demo.get("mrn"):
            ci_demo["mrn"] = demo["mrn"]
        ci["demographics"] = ci_demo

    # Bring over current conditions/medications/labs if present
    # Check both at root level (for backward compatibility) AND in clinical_information
    source_ci = dashboard_profile.get("clinical_information", {})

    if dashboard_profile.get("current_conditions"):
        ci["current_conditions"] = dashboard_profile["current_conditions"]
    elif source_ci.get("current_conditions"):
        ci["current_conditions"] = source_ci["current_conditions"]

    if dashboard_profile.get("current_medications"):
        ci["current_medications"] = dashboard_profile["current_medications"]
    elif source_ci.get("current_medications"):
        ci["current_medications"] = source_ci["current_medications"]

    if dashboard_profile.get("organ_function"):
        ci["organ_function"] = dashboard_profile["organ_function"]
    elif source_ci.get("organ_function"):
        ci["organ_function"] = source_ci["organ_function"]

    if dashboard_profile.get("lifestyle_factors"):
        ci["lifestyle_factors"] = dashboard_profile["lifestyle_factors"]
    elif source_ci.get("lifestyle_factors"):
        ci["lifestyle_factors"] = source_ci["lifestyle_factors"]

    # Also copy any manual_enrichment block into clinical_information
    if dashboard_profile.get("manual_enrichment"):
        ci["manual_enrichment"] = dashboard_profile["manual_enrichment"]

    jsonld["clinical_information"] = ci
    return jsonld
