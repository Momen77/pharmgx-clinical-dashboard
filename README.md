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

### Core Functionality

1. **Home Dashboard**
   - Overview metrics (patients tested, genes analyzed, drug interactions)
   - Navigation to all workflow steps

2. **Patient Profile Creation**
   - Comprehensive demographics form (age, weight, height, gender, etc.)
   - Photo upload support (including AI-generated patient photos)
   - Auto-generation mode for virtual patients
   - Dynamic clinical data generation with age and lifestyle factors

3. **Gene Panel Selection**
   - Pre-defined PGx gene panels (Core Metabolizers, Chemotherapy, Transporters, etc.)
   - Custom gene selection
   - Panel-based drug interaction insights

4. **Interactive Test Workflow**
   - Real-time progress tracking with animated workflow stages
   - Multi-threaded pipeline execution
   - Simulation of laboratory workflows (DNA extraction, sequencing, variant calling)
   - Progress visualization with detailed sub-steps

5. **Clinical Report Generation**
   - Detailed analysis results with color-coded alerts (based on CPIC guidelines)
   - Interactive D3.js knowledge graph visualization
   - Click-to-explore node details in the graph
   - Summary metrics and statistics

6. **Data Export**
   - Download PDF reports
   - Export raw data (JSON-LD, CSV, RDF)
   - Multiple output format support

## Data Sources and APIs

The dashboard integrates with 9+ external databases and APIs:

### Primary Data Sources
- **UniProt**: Gene and protein information
- **EMBL-EBI Proteins API**: Genetic variants discovery
- **ClinVar**: Clinical significance of genetic variants

### Pharmacogenomics Databases
- **PharmGKB**: Drug-gene interactions and CPIC pharmacogenomic guidelines
- **ChEMBL**: Drug-indication relationships (primary drug API)
- **RxNorm/RxNav**: Drug identifier standardization
- **OpenFDA**: FDA drug labels and safety information

### Clinical & Ontology Databases
- **BioPortal**: SNOMED CT terminology mapping
- **Europe PMC**: Literature evidence and PubMed citations

### Additional Features
- Built-in caching system for API responses
- Rate limiting to respect API constraints
- Robust error handling and fallback logic

## Workflow

The dashboard guides users through a complete pharmacogenomics testing workflow:

1. **Create Patient Profile** (manual form or auto-generate)
2. **Select Genes** to test from available panels
3. **Run Test** with real-time progress tracking
4. **View Results** with interactive knowledge graph
5. **Export Data** in multiple formats

### Pipeline Phases

Behind the scenes, the test execution runs a 5-phase pipeline:

- **Phase 1: Variant Discovery** - Finds clinically significant variants from EMBL-EBI Proteins API
- **Phase 2: Clinical Validation** - Enriches with ClinVar and PharmGKB annotations
- **Phase 3: Drug & Disease Context** - Links to drug databases and literature
- **Phase 4: RDF Knowledge Graph Assembly** - Builds semantic web knowledge graphs
- **Phase 5: Export & Visualization** - Creates multiple output formats

## Technical Implementation

Built with:
- **Python 3.11** with Anaconda
- **Streamlit** for the web dashboard
- **RDFlib** for knowledge graph generation
- **D3.js** for interactive visualizations
- **Threading** for background pipeline execution
- **Caching** for API response optimization

All code is modular and follows a clean architecture with separate modules for each component.

## Requirements

- Python 3.11+
- See `requirements.txt` for all dependencies
