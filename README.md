# UGent Pharmacogenomics Clinical Dashboard

Clinical pharmacogenomics dashboard for interactive PGx testing and reporting. Integrates variant discovery, clinical validation, and drug interaction analysis with a Streamlit-based interface for healthcare providers.

## Deployment on Streamlit Cloud

This app uses `requirements.txt` for dependency management to avoid conda TOS issues.

### Quick Deploy

1. Push this repository to GitHub
2. Go to https://share.streamlit.io
3. Connect your repository
4. Deploy!

### Local Development

```bash
pip install -r requirements.txt
streamlit run app.py
```

### Configuration

Add your API keys in Streamlit Cloud secrets (Settings → Secrets):

```toml
[api]
ncbi_email = "your-email@example.com"
ncbi_api_key = "your-ncbi-key"
bioportal_api_key = "your-bioportal-key"
```

## Features

- 🏠 Home dashboard with metrics
- 👤 Patient profile creation
- 🧬 Interactive gene panel selection
- 🔬 Pharmacogenetic test execution
- 📊 Clinical report generation
- 💾 Data export (JSON-LD, PDF)

## Documentation

- `DEPLOYMENT_SUCCESS.md` - Deployment status and guide
- `DEPLOYMENT_CHECKLIST.md` - Troubleshooting checklist
- `DEPLOYMENT_FIXES.md` - What was fixed
- `README_DEPLOYMENT.md` - Detailed deployment guide

## Requirements

- Python 3.11+
- See `requirements.txt` for all dependencies
