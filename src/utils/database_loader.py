"""
Database Loader - Compatibility Wrapper
✅ SCHEMA-ALIGNED with complete_enhanced_schema.sql

This file now imports from the modular database package for easier maintenance.
All functionality has been moved to database/* submodules:

Structure:
- database/connection.py: Database connection management
- database/reference_data.py: SNOMED, genes, drugs, variants, PharmGKB annotations
- database/patient_core.py: Patients and demographics tables
- database/patient_clinical.py: Conditions, medications, organ function, lifestyle
- database/patient_variants.py: Patient variants and pharmacogenomics profiles
- database/linking_tables.py: Medication-variant links, conflicts, ethnicity adjustments
- database/literature.py: Publications and linking tables
- database/summaries.py: Clinical and processing summaries
- database/main_loader.py: Orchestrator that ties everything together
"""

# Import from modular database package
from .database import DatabaseLoader

# Backward compatibility aliases
ComprehensiveDatabaseLoader = DatabaseLoader

__all__ = ['DatabaseLoader', 'ComprehensiveDatabaseLoader']
