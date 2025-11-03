## src/utils/database/

Optional patient-profile persistence.

- `connection.py`: Connection factory (e.g., Postgres via psycopg / Cloud SQL connector).
- `main_loader.py` + helpers: Load comprehensive patient profile and related tables.
- `linking_tables.py`, `patient_*`, `reference_data.py`: Schema-aligned loaders.

Enable/disable via `database.enabled` in `config.yaml`. Non‑blocking mode continues the pipeline if loading fails.

