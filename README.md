## UGent Pharmacogenomics Clinical Dashboard

Interactive clinical pharmacogenomics dashboard for PGx testing and reporting. The app guides you from patient profile creation to multi-gene analysis, then builds and visualizes a knowledge graph with exportable outputs.

## Quick Start

### Local
```bash
pip install -r requirements.txt
streamlit run app.py
```

### Streamlit Cloud
1. Push to GitHub
2. Open `https://share.streamlit.io`
3. Connect the repository
4. Set Secrets (see Configuration) and deploy

## What You Can Do
- Create a patient profile (manual form or auto-generate)
- Select PGx gene panels or custom genes
- Run analysis with real-time progress storyboard
- View an interactive knowledge graph of results
- Export outputs (JSON-LD, RDF/TTL, HTML report, optional PDF)

## Workflow
1. Create Patient → 2. Select Genes → 3. Run Test → 4. View Results → 5. Export

### Pipeline Phases (behind the scenes)
- Phase 1: Variant Discovery (e.g., EMBL‑EBI Proteins)
- Phase 2: Clinical Validation (ClinVar, PharmGKB)
- Phase 3: Drug & Disease Context (ChEMBL, BioPortal, Europe PMC, OpenFDA)
- Phase 4: RDF Knowledge Graph Assembly (RDFlib)
- Phase 5: Export & Visualization (JSON‑LD, HTML, RDF/TTL)

## Architecture (high level)
- UI: `src/dashboard/app.py` (Streamlit pages and storyboard)
- Pipeline: `src/main.py` (`PGxPipeline` orchestration, multi‑gene support, events)
- Phases: `src/phase1_discovery` … `src/phase5_export`
- Utilities: `src/utils` (APIs, database loader, profile generator, event bus)

For deeper details, see folder READMEs in their respective directories.

## Data Sources (examples)
- ClinVar, PharmGKB, ChEMBL
- NCBI/EMBL‑EBI, RxNorm/RxNav
- BioPortal (SNOMED CT), Europe PMC, OpenFDA

## Configuration
- File: `config.yaml` controls API keys, rate limits, caching, and optional database loading
- Secrets (Streamlit Cloud → Settings → Secrets):
```toml
[api]
ncbi_email = "your-email@example.com"
ncbi_api_key = "your-ncbi-key"
bioportal_api_key = "your-bioportal-key"
GOOGLE_API_KEY = "your-google-key"  # optional for AI photos
```

## Outputs
- App shows generated file paths after a run
- Typical formats: JSON‑LD (comprehensive), RDF/TTL, HTML report, optional PDF
- Export page provides download buttons if files exist on disk

## Troubleshooting (quick)
- Missing API keys → add to `config.yaml` or Cloud Secrets
- Rate limits/timeouts → reduce genes, enable cache, check `rate_limits` in `config.yaml`
- “Visualization file not found” → ensure JSON‑LD is present in outputs and on disk

## Minimal Repo Structure
```
pharmgx-clinical-dashboard/
  app.py               # streamlit entrypoint
  config.yaml          # config and feature toggles
  src/
    dashboard/         # UI and visualization
    phase1_discovery/  # variants
    phase2_clinical/   # clinical validation
    phase3_context/    # drugs & literature
    phase4_rdf/        # graph assembly
    phase5_export/     # exporters
    utils/             # shared helpers, db loader, event bus
```

## License & Acknowledgments
- University assets in `assets/` belong to their respective owners
- External APIs and databases acknowledged above
