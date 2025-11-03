## src/

Core application code.

- `main.py`: Orchestrates the multi‑gene PGx pipeline (`PGxPipeline`).
- `dashboard/`: Streamlit UI, navigation, and visualization components.
- `phase1_discovery` … `phase5_export`: Pipeline phases.
- `utils/`: Shared helpers (APIs, database loader, event bus, profile generator).

Entry points
- Dashboard: imported via `app.py` at repo root → `src/dashboard/app.py`
- Pipeline class: `from src.main import PGxPipeline`

Notes
- Configuration is read from `config.yaml` at the project root.
- API events are emitted via an event bus/queue for Streamlit-safe updates.

