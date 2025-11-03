## src/phase2_clinical/

Clinical validation and annotation.

- `clinical_validator.py`: Integrates ClinVar, PharmGKB, and ontology mappings.
- Clients: `clinvar_client.py`, `pharmgkb_client.py`, `bioportal_client.py`.

Consumes Phase 1 outputs and enriches variants with clinical significance.

