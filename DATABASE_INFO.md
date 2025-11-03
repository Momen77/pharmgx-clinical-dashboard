# Database Documentation

PostgreSQL database for storing patient pharmacogenomics data and clinical recommendations.

## Quick Facts

- **Database**: PostgreSQL 11+ on Google Cloud SQL or local
- **Schema**: `Pharmacogenomics_Clinical_db.sql` (complete DDL, 60+ tables)
- **Connection**: Cloud SQL Connector or direct PostgreSQL
- **Loader**: `src/utils/database/` (Python, 5-phase loading)
- **Optional**: Non-blocking, works without database

## Key Tables

| Category | Tables | Purpose |
|----------|--------|---------|
| **Foundation** | SNOMED concepts | Medical terminology |
| **Reference** | Genes, drugs, variants, PharmGKB | Knowledge base |
| **Patient Core** | Patients, demographics | Basic patient data |
| **Clinical** | Conditions, medications, labs, lifestyle | Clinical data |
| **PGx** | Patient variants, profiles | Genetic variants |
| **Linking** | Medication links, conflicts | Drug interactions |
| **Population** | Frequencies, ethnicity adjustments | Population data |
| **Literature** | Publications, gene/variant links | Evidence |

## Setup

### 1. Create Database
```sql
CREATE DATABASE pgx_database;
CREATE USER pgx_user WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE pgx_database TO pgx_user;
\c pgx_database
CREATE EXTENSION pg_trgm;
```

### 2. Load Schema
```bash
psql -U pgx_user -d pgx_database -f Pharmacogenomics_Clinical_db.sql
```

### 3. Configure

**Local PostgreSQL**:
```toml
# .streamlit/secrets.toml
[db]
DB_HOST = "localhost"
DB_PORT = "5432"
DB_USER = "pgx_user"
DB_PASS = "password"
DB_NAME = "pgx_database"
```

**Google Cloud SQL**:
```toml
# .streamlit/secrets.toml
[db]
INSTANCE_CONNECTION_NAME = "project:region:instance"
DB_USER = "pgx_user"
DB_PASS = "password"
DB_NAME = "pgx_database"
```

```yaml
# config.yaml
database:
  enabled: true
  non_blocking: true
```

## Common Queries

### Patient's Critical Conflicts
```sql
SELECT p.name, cm.drug_name, pc.severity, pc.recommendation
FROM patients p
JOIN pgx_conflicts pc ON p.patient_id = pc.patient_id
JOIN current_medications cm ON pc.medication_id = cm.medication_id
WHERE pc.severity = 'CRITICAL';
```

### Patient's Variants
```sql
SELECT gene_symbol, variant_id, diplotype, phenotype, clinical_significance
FROM patient_variants
WHERE patient_id = 'YOUR_PATIENT_ID';
```

### Drug Interactions
```sql
SELECT drug_name, gene_symbol, interaction_type, recommendation
FROM drug_to_variant_links
WHERE gene_symbol = 'CYP2D6';
```

## Data Flow

```
Patient JSON-LD → Database Loader (5 phases) → PostgreSQL
  Phase 1: Reference data (SNOMED, genes, drugs, variants)
  Phase 2: Patient core (patients, demographics)
  Phase 3: Patient clinical (conditions, medications, labs)
  Phase 4: Patient variants (PGx profiles, variants)
  Phase 5: Linking & summaries (conflicts, literature)
```

## Files

**Schema**: `Pharmacogenomics_Clinical_db.sql`  
**Loader**: `src/utils/database/`  
**This doc**: `DATABASE_INFO.md`

## Features

- **Normalized**: Proper relational design with foreign keys
- **JSONB**: Flexible array storage for complex data
- **Provenance**: Tracks data sources and versions
- **Audit**: History tables for changes
- **Views**: 6 pre-defined views for queries
- **Indexes**: Optimized for performance
- **Sources**: PharmGKB, ClinVar, UniProt, gnomAD

See full schema in `Pharmacogenomics_Clinical_db.sql` for table details.
