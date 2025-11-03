## src/phase1_discovery/

Variant discovery for selected genes.

- `variant_discoverer.py`: Queries external sources (e.g., EMBL‑EBI Proteins) and prepares per‑gene variant sets with metadata.

Called by `PGxPipeline.run(...)` / `run_multi_gene(...)` in `src/main.py`.

