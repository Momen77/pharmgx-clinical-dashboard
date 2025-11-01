"""
Database Loading Module for Pharmacogenomics Knowledge Base
Modular structure for easier maintenance and testing

Structure:
- connection.py: Database connection management
- reference_data.py: SNOMED, genes, drugs, variants, PharmGKB annotations
- patient_core.py: Patients and demographics tables
- patient_clinical.py: Conditions, medications, organ function, lifestyle
- patient_variants.py: Patient variants and pharmacogenomics profiles
- linking_tables.py: Medication-variant links, conflicts, ethnicity adjustments
- literature.py: Publications and linking tables
- summaries.py: Clinical and processing summaries
- utils.py: Helper functions
"""

from .main_loader import DatabaseLoader

__all__ = ['DatabaseLoader']

