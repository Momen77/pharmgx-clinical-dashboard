## src/utils/

Shared utilities for the pipeline and dashboard.

- API helpers: `api_client.py`, external service clients, rate limiting/caching.
- Profile: `dynamic_clinical_generator.py`, `profile_normalizer.py`.
- Pipeline: `pipeline_worker.py`, `background_worker.py`, `event_bus.py`.
- Database: loader and helpers in `utils/database/`.
- Others: `evidence_levels.py`, `dosing_adjustments.py`, etc.

Configuration path resolution falls back to the project root `config.yaml`.

