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

#### Option 1: Using pip (recommended for Streamlit Cloud)
```bash
pip install -r requirements.txt
streamlit run app.py
```

#### Option 2: Using conda (for local development)
```bash
conda env create -f environment.yml
conda activate pgx-clinical-dashboard
streamlit run app.py
```

### Configuration

#### Local Development
Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and add your API keys.

#### Streamlit Cloud
Add your API keys in Streamlit Cloud secrets (Settings → Secrets):

```toml
[api]
ncbi_email = "your-email@example.com"
ncbi_api_key = "your-ncbi-key"
bioportal_api_key = "your-bioportal-key"
GOOGLE_API_KEY = "your-google-key"  # Optional: for AI photo generation
```

## Features

- 🏠 Home dashboard with metrics
- 👤 Patient profile creation
- 🧬 Interactive gene panel selection
- 🔬 Pharmacogenetic test execution
- 📊 Clinical report generation
- 💾 Data export (JSON-LD, PDF)

## Requirements

- Python 3.11+
- See `requirements.txt` for all dependencies
