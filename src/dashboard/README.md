## src/dashboard/

Streamlit UI for the PGx Dashboard.

- `app.py`: Main multi-page app (Home, Create Patient, Select Genes, Run Test, View Results, Export).
- `gene_panel_selector.py`: Gene panel selection UI/logic.
- `patient_creator.py`: Patient form and auto‑generation.
- `ui_animation.py`: Storyboard progress animation and controls.
- `pdf_exporter.py`, `report_generator.py`: Reporting hooks.
- `components/`: Visualization pieces (e.g., JSON‑LD → D3 hierarchy).
- `utils/`: Styling and small UI utilities.

Run via repository root: `streamlit run app.py` (imports this module).

