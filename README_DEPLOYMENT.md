# PGx Clinical Dashboard - Deployment Guide

## Streamlit Cloud Deployment

### Prerequisites
- Upload this repository to GitHub
- Connect to Streamlit Cloud

### Configuration
- **Main file**: `src/dashboard/app.py`
- **Environment file**: `environment.yml` (conda)
- **Python version**: 3.11

### Directory Structure
```
pharmgx-clinical-dashboard/
├── .streamlit/
│   ├── config.toml
│   └── credentials.toml
├── environment.yml
├── requirements.txt
├── config.yaml
└── src/
    ├── main.py
    └── dashboard/
        ├── app.py          # Main entry point
        ├── patient_creator.py
        ├── gene_panel_selector.py
        ├── alert_classifier.py
        ├── report_generator.py
        ├── pdf_exporter.py
        └── utils/
            ├── styling.py
            └── mock_patient.py
```

### Running Locally

1. Activate environment:
```bash
conda activate pgx-kg
```

2. Run the dashboard:
```bash
streamlit run src/dashboard/app.py
```

### Dependencies
All required packages are listed in `environment.yml` including:
- streamlit>=1.28.0
- reportlab>=4.0.0
- Pillow>=10.0.0
- plotly>=5.17.0
- qrcode>=7.4.0

