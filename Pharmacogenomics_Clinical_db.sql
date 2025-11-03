-- Unknown how to generate base type type

alter type gtrgm owner to postgres;

create table patients
(
    patient_id               varchar(50) not null
        primary key,
    name                     varchar(255),
    description              text,
    dashboard_source         boolean default true,
    date_created             timestamp,
    data_version             integer default 1,
    total_critical_conflicts integer,
    provenance_source        varchar(255),
    provenance_date          timestamp,
    rdf_context              jsonb
);

comment on column patients.provenance_source is 'Source file or system from which this patient record was ingested (for JSON-LD round-trip).';

alter table patients
    owner to postgres;

create table demographics
(
    patient_id              varchar(50) not null
        primary key
        references patients,
    first_name              varchar(100),
    last_name               varchar(100),
    additional_name         varchar(100),
    preferred_name          varchar(100),
    birth_date              timestamp,
    age                     integer,
    biological_sex          varchar(10)
        constraint chk_bio_sex
            check ((biological_sex)::text = ANY
                   ((ARRAY ['Male'::character varying, 'Female'::character varying, 'Intersex'::character varying, 'Unknown'::character varying])::text[])),
    gender                  varchar(50),
    ethnicity               jsonb,
    ethnicity_snomed_labels jsonb,
    race                    varchar(100),
    birth_place_city        varchar(100),
    birth_place_country     varchar(100),
    weight_kg               numeric(5, 2),
    height_cm               numeric(5, 2),
    bmi                     numeric(5, 2),
    current_address         text,
    current_city            varchar(100),
    current_country         varchar(100),
    postal_code             varchar(20),
    phone                   varchar(50),
    email                   varchar(255),
    emergency_contact       varchar(255),
    emergency_phone         varchar(50),
    language                varchar(50),
    interpreter_needed      boolean,
    insurance_provider      varchar(100),
    policy_number           varchar(50),
    pcp_name                varchar(255),
    pcp_contact             varchar(50),
    note                    text
);

alter table demographics
    owner to postgres;

create table pharmacogenomics_profiles
(
    profile_id        serial
        primary key,
    patient_id        varchar(50)
        unique
        references patients,
    genes_analyzed    jsonb,
    total_variants    integer,
    analysis_date     timestamp,
    provenance_source varchar(255),
    provenance_date   timestamp,
    rdf_context       jsonb
);

alter table pharmacogenomics_profiles
    owner to postgres;

create table clinical_summaries
(
    summary_id                   serial
        primary key,
    patient_id                   varchar(50)
        unique
        references patients,
    total_variants               integer,
    pathogenic_count             integer,
    likely_pathogenic_count      integer,
    uncertain_significance_count integer,
    benign_count                 integer,
    drug_response_count          integer,
    high_impact_genes            jsonb,
    analysis_timestamp           timestamp
);

alter table clinical_summaries
    owner to postgres;

create table literature_summaries
(
    summary_id                    serial
        primary key,
    patient_id                    varchar(50)
        unique
        references patients,
    total_publications            integer,
    gene_publications             integer,
    variant_specific_publications integer,
    drug_publications             integer,
    genes_with_literature         jsonb,
    variants_with_literature      jsonb,
    drugs_with_literature         jsonb,
    top_cited_pmids               jsonb
);

alter table literature_summaries
    owner to postgres;

create table processing_summary
(
    summary_id                     serial
        primary key,
    patient_id                     varchar(50)
        unique
        references patients,
    total_medication_variant_links integer,
    total_condition_disease_links  integer,
    total_variant_phenotype_links  integer,
    total_drug_variant_links       integer,
    conflicts_total                integer,
    conflicts_critical             integer,
    conflicts_warnings             integer,
    conflicts_info                 integer,
    patient_conditions_count       integer,
    patient_medications_count      integer,
    total_variants                 integer,
    variants_with_drug_data        integer,
    analysis_timestamp             timestamp,
    provenance_source              varchar(255),
    provenance_date                timestamp,
    rdf_context                    jsonb
);

alter table processing_summary
    owner to postgres;

create table snomed_concepts
(
    snomed_code     varchar(20) not null
        primary key,
    concept_url     varchar(255),
    preferred_label varchar(500),
    concept_type    varchar(50),
    search_term     varchar(255)
);

alter table snomed_concepts
    owner to postgres;

create index idx_label
    on snomed_concepts (preferred_label);

create index idx_type
    on snomed_concepts (concept_type);

create index idx_search
    on snomed_concepts (search_term);

create table genes
(
    gene_symbol varchar(20) not null
        primary key,
    protein_id  varchar(20),
    entrez_id   integer,
    hgnc_id     varchar(20),
    aliases     jsonb
);

alter table genes
    owner to postgres;

create index idx_protein
    on genes (protein_id);

create index idx_entrez
    on genes (entrez_id);

create table drugs
(
    drug_id              serial
        primary key,
    drug_name            varchar(255) not null
        unique,
    drugbank_id          varchar(20)
        unique,
    rxnorm_cui           varchar(20),
    chembl_id            varchar(20),
    snomed_code          varchar(20)
        references snomed_concepts,
    atc_code             varchar(20),
    first_approval       integer,
    max_phase            numeric(2, 1),
    synonyms             jsonb,
    trade_names          jsonb,
    chembl_molecule_type varchar(50)
);

alter table drugs
    owner to postgres;

create index idx_drugbank
    on drugs (drugbank_id);

create index idx_rxnorm
    on drugs (rxnorm_cui);

create index idx_chembl
    on drugs (chembl_id);

create index idx_name_pattern
    on drugs using gist (drug_name gist_trgm_ops);

create table variants
(
    variant_key           varchar(255) not null
        primary key,
    gene_symbol           varchar(20)
        references genes,
    variant_id            varchar(50),
    rsid                  varchar(20),
    clinical_significance varchar(100),
    consequence_type      varchar(100),
    variant_type          varchar(50),
    wild_type             varchar(255),
    mutated_type          varchar(255),
    cytogenetic_band      varchar(50),
    alternative_sequence  text,
    begin_position        integer,
    end_position          integer,
    codon                 varchar(10),
    somatic_status        boolean,
    source_type           varchar(50),
    hgvs_notation         varchar(255)
);

alter table variants
    owner to postgres;

create index idx_gene
    on variants (gene_symbol);

create index idx_rsid
    on variants (rsid);

create index idx_variant_id
    on variants (variant_id);

create index idx_significance
    on variants (clinical_significance);

create table variant_genomic_locations
(
    location_id      serial
        primary key,
    variant_id       varchar(255),
    assembly         varchar(20),
    chromosome       varchar(10),
    start_position   bigint,
    end_position     bigint,
    reference_allele text,
    alternate_allele text,
    strand           varchar(1),
    sequence_version varchar(50)
);

alter table variant_genomic_locations
    owner to postgres;

create index idx_variant_genomic_locations_variant
    on variant_genomic_locations (variant_id);

create index idx_position
    on variant_genomic_locations (chromosome, start_position, end_position);

create index idx_assembly
    on variant_genomic_locations (assembly);

create table uniprot_variant_details
(
    detail_id            serial
        primary key,
    variant_id           varchar(255),
    alternative_sequence text,
    begin_position       integer,
    end_position         integer,
    codon                varchar(10),
    consequence_type     varchar(100),
    wild_type            varchar(255),
    mutated_type         varchar(255),
    somatic_status       boolean,
    source_type          varchar(50)
);

alter table uniprot_variant_details
    owner to postgres;

create index idx_uniprot_variant_details_variant
    on uniprot_variant_details (variant_id);

create table uniprot_xrefs
(
    xref_id       serial
        primary key,
    variant_id    varchar(255),
    database_name varchar(50),
    database_id   varchar(100),
    url           varchar(500)
);

alter table uniprot_xrefs
    owner to postgres;

create index idx_uniprot_xrefs_variant
    on uniprot_xrefs (variant_id);

create index idx_database
    on uniprot_xrefs (database_name, database_id);

create table variant_predictions
(
    prediction_id serial
        primary key,
    variant_id    varchar(255),
    tool          varchar(50),
    prediction    varchar(50),
    score         numeric(10, 6),
    confidence    varchar(50)
);

alter table variant_predictions
    owner to postgres;

create index idx_variant_predictions_variant
    on variant_predictions (variant_id);

create index idx_tool
    on variant_predictions (tool);

create table clinvar_submissions
(
    submission_id         serial
        primary key,
    variant_id            varchar(255),
    clinvar_id            varchar(50),
    clinical_significance varchar(100),
    review_status         varchar(100),
    last_evaluated        date,
    submitter             varchar(255),
    condition             varchar(500)
);

alter table clinvar_submissions
    owner to postgres;

create index idx_clinvar_submissions_variant
    on clinvar_submissions (variant_id);

create index idx_clinvar
    on clinvar_submissions (clinvar_id);

create table current_conditions
(
    condition_id    serial
        primary key,
    patient_id      varchar(50)
        references patients,
    snomed_code     varchar(20) not null
        references snomed_concepts,
    snomed_url      varchar(255),
    rdfs_label      varchar(255),
    skos_pref_label varchar(255),
    search_term     varchar(255),
    condition_type  varchar(50)
);

alter table current_conditions
    owner to postgres;

create index idx_patient_conditions
    on current_conditions (patient_id);

create index idx_snomed
    on current_conditions (snomed_code);

create table current_medications
(
    medication_id           serial
        primary key,
    patient_id              varchar(50)
        references patients,
    medication_url          varchar(255),
    medication_type         varchar(50),
    drugbank_id             varchar(20),
    chembl_id               varchar(20),
    rxnorm_cui              varchar(20),
    rxnorm_uri              varchar(255),
    drug_name               varchar(255),
    schema_name             varchar(255),
    dosage_form             varchar(50),
    dose_value              numeric(10, 2),
    dose_unit               varchar(20),
    frequency               varchar(100),
    start_date              date,
    purpose                 varchar(255),
    source                  varchar(50),
    treats_condition_snomed varchar(20),
    treats_condition_label  varchar(255),
    indication_name         varchar(255),
    indication_mesh_id      varchar(50),
    indication_mesh_heading varchar(255),
    efo_id                  varchar(50),
    max_phase_for_ind       numeric(2, 1),
    max_phase_overall       numeric(2, 1),
    first_approval          integer,
    relevance_score         numeric(10, 2),
    treatment_line          varchar(100),
    clinical_phase          numeric(2, 1),
    guideline               text,
    combination_therapy     boolean,
    chembl_molecule_type    varchar(50)
);

alter table current_medications
    owner to postgres;

create index idx_patient_meds
    on current_medications (patient_id);

create index idx_current_meds_drugbank
    on current_medications (drugbank_id);

create index idx_current_meds_chembl
    on current_medications (chembl_id);

create table organ_function_labs
(
    lab_id           serial
        primary key,
    patient_id       varchar(50)
        references patients,
    organ_system     varchar(50),
    test_type        varchar(100),
    snomed_code      varchar(20)
        references snomed_concepts,
    snomed_url       varchar(255),
    rdfs_label       varchar(255),
    value            numeric(10, 4),
    unit             varchar(50),
    test_date        date,
    normal_range     varchar(100),
    status           varchar(50),
    egfr_value       numeric(5, 2),
    serum_creatinine numeric(5, 2),
    alt_value        numeric(10, 2),
    ast_value        numeric(10, 2),
    bilirubin_total  numeric(10, 2)
);

alter table organ_function_labs
    owner to postgres;

create index idx_patient_labs
    on organ_function_labs (patient_id, test_date);

create table lifestyle_factors
(
    factor_id       serial
        primary key,
    patient_id      varchar(50)
        references patients,
    factor_url      varchar(255),
    factor_type     varchar(50),
    snomed_code     varchar(20)
        references snomed_concepts,
    rdfs_label      varchar(255),
    skos_pref_label varchar(255),
    category        varchar(50),
    status          varchar(50),
    frequency       varchar(100),
    note            text
);

alter table lifestyle_factors
    owner to postgres;

create index idx_patient_lifestyle
    on lifestyle_factors (patient_id);

create index idx_lifestyle_snomed
    on lifestyle_factors (snomed_code);

create table patient_variants
(
    patient_variant_id    serial
        primary key,
    patient_id            varchar(50)
        references patients,
    gene_symbol           varchar(20)
        references genes,
    protein_id            varchar(20),
    variant_id            varchar(255),
    rsid                  varchar(20),
    genotype              varchar(50),
    diplotype             varchar(50),
    phenotype             varchar(100)
        constraint chk_phenotype
            check ((phenotype)::text = ANY
                   ((ARRAY ['Rapid Metabolizer'::character varying, 'Normal Metabolizer'::character varying, 'Intermediate Metabolizer'::character varying, 'Poor Metabolizer'::character varying, 'Ultrarapid Metabolizer'::character varying, 'Uncertain'::character varying, NULL::character varying])::text[])),
    zygosity              varchar(50),
    clinical_significance varchar(100),
    consequence_type      varchar(100),
    wild_type             varchar(255),
    alternative_sequence  text,
    begin_position        integer,
    end_position          integer,
    codon                 varchar(10),
    somatic_status        boolean,
    source_type           varchar(50),
    genomic_notation      varchar(255),
    hgvs_notation         varchar(255),
    raw_uniprot_data      jsonb,
    raw_pharmgkb_data     jsonb,
    unique (patient_id, variant_id)
);

comment on table patient_variants is 'Patient-specific genetic variants with phenotypes and clinical significance';

alter table patient_variants
    owner to postgres;

create index idx_patient_gene
    on patient_variants (patient_id, gene_symbol);

create index idx_patient_variants_variant
    on patient_variants (variant_id);

create index idx_phenotype
    on patient_variants (phenotype);

create table pharmgkb_annotations
(
    annotation_id              bigint not null
        primary key,
    accession_id               varchar(50),
    variant_id                 varchar(255),
    gene_symbol                varchar(20)
        references genes,
    annotation_name            text,
    evidence_level             varchar(10)
        constraint chk_evidence_level
            check ((evidence_level)::text = ANY
                   ((ARRAY ['1A'::character varying, '1B'::character varying, '2A'::character varying, '2B'::character varying, '3'::character varying, '4'::character varying, NULL::character varying])::text[])),
    score                      numeric(10, 2),
    clinical_annotation_types  jsonb,
    pediatric                  boolean default false,
    obj_cls                    varchar(50),
    location                   text,
    override_level             varchar(10),
    conflicting_annotation_ids jsonb,
    related_chemicals_logic    varchar(255),
    created_date               date,
    last_updated               date,
    raw_data                   jsonb
);

comment on table pharmgkb_annotations is 'Clinical annotations from PharmGKB with evidence levels and relationships';

alter table pharmgkb_annotations
    owner to postgres;

create index idx_pharmgkb_annotations_variant
    on pharmgkb_annotations (variant_id);

create index idx_evidence
    on pharmgkb_annotations (evidence_level);

create index idx_pharmgkb_annotations_gene
    on pharmgkb_annotations (gene_symbol);

create index idx_accession
    on pharmgkb_annotations (accession_id);

create index idx_annotation_fts
    on pharmgkb_annotations using gin (to_tsvector('english'::regconfig, annotation_name));

create table pharmgkb_score_details
(
    detail_id     serial
        primary key,
    annotation_id bigint
        references pharmgkb_annotations,
    category      varchar(100),
    score         numeric(5, 2),
    weight        numeric(5, 4)
);

alter table pharmgkb_score_details
    owner to postgres;

create index idx_annotation
    on pharmgkb_score_details (annotation_id);

create table pharmgkb_allele_phenotypes
(
    phenotype_id     serial
        primary key,
    annotation_id    bigint
        references pharmgkb_annotations,
    allele           varchar(50),
    genotype         varchar(50),
    phenotype_text   text,
    limited_evidence boolean default false
);

alter table pharmgkb_allele_phenotypes
    owner to postgres;

create index idx_allele_phenotypes_annotation
    on pharmgkb_allele_phenotypes (annotation_id);

create index idx_allele
    on pharmgkb_allele_phenotypes (allele);

create table pharmgkb_allele_genotypes
(
    genotype_id       serial
        primary key,
    phenotype_id      integer
        references pharmgkb_allele_phenotypes,
    genotype_notation varchar(50),
    notation_system   varchar(20)
);

alter table pharmgkb_allele_genotypes
    owner to postgres;

create index idx_allele_genotypes_phenotype
    on pharmgkb_allele_genotypes (phenotype_id);

create table pharmgkb_annotation_history
(
    history_id    serial
        primary key,
    annotation_id bigint
        references pharmgkb_annotations,
    accession_id  varchar(50),
    version       integer,
    history_date  timestamp,
    change_type   varchar(50)
);

alter table pharmgkb_annotation_history
    owner to postgres;

create index idx_annotation_history_annotation
    on pharmgkb_annotation_history (annotation_id);

create index idx_date
    on pharmgkb_annotation_history (history_date);

create table pharmgkb_chemicals
(
    chemical_id serial
        primary key,
    pharmgkb_id varchar(50)
        unique,
    name        varchar(255),
    obj_cls     varchar(50)
);

alter table pharmgkb_chemicals
    owner to postgres;

create index idx_name
    on pharmgkb_chemicals (name);

create index idx_pharmgkb
    on pharmgkb_chemicals (pharmgkb_id);

create table pharmgkb_annotation_chemicals
(
    link_id       serial
        primary key,
    annotation_id bigint
        references pharmgkb_annotations,
    chemical_id   integer
        references pharmgkb_chemicals
);

alter table pharmgkb_annotation_chemicals
    owner to postgres;

create index idx_annotation_chemicals_annotation
    on pharmgkb_annotation_chemicals (annotation_id);

create index idx_chemical
    on pharmgkb_annotation_chemicals (chemical_id);

create table pharmgkb_guidelines
(
    guideline_id serial
        primary key,
    pharmgkb_id  varchar(50)
        unique,
    name         text,
    source       varchar(100),
    url          varchar(500),
    obj_cls      varchar(50)
);

alter table pharmgkb_guidelines
    owner to postgres;

create index idx_guidelines_pharmgkb
    on pharmgkb_guidelines (pharmgkb_id);

create index idx_source
    on pharmgkb_guidelines (source);

create table pharmgkb_annotation_guidelines
(
    link_id       serial
        primary key,
    annotation_id bigint
        references pharmgkb_annotations,
    guideline_id  integer
        references pharmgkb_guidelines
);

alter table pharmgkb_annotation_guidelines
    owner to postgres;

create index idx_annotation_guidelines_annotation
    on pharmgkb_annotation_guidelines (annotation_id);

create index idx_guideline
    on pharmgkb_annotation_guidelines (guideline_id);

create table pharmgkb_labels
(
    label_id    serial
        primary key,
    pharmgkb_id varchar(50)
        unique,
    name        text,
    source      varchar(100),
    obj_cls     varchar(50)
);

alter table pharmgkb_labels
    owner to postgres;

create index idx_labels_pharmgkb
    on pharmgkb_labels (pharmgkb_id);

create index idx_labels_source
    on pharmgkb_labels (source);

create table pharmgkb_annotation_labels
(
    link_id       serial
        primary key,
    annotation_id bigint
        references pharmgkb_annotations,
    label_id      integer
        references pharmgkb_labels
);

alter table pharmgkb_annotation_labels
    owner to postgres;

create index idx_annotation_labels_annotation
    on pharmgkb_annotation_labels (annotation_id);

create table pharmgkb_diseases
(
    disease_id  serial
        primary key,
    pharmgkb_id varchar(50)
        unique,
    name        varchar(255),
    obj_cls     varchar(50)
);

alter table pharmgkb_diseases
    owner to postgres;

create index idx_diseases_pharmgkb
    on pharmgkb_diseases (pharmgkb_id);

create index idx_diseases_name
    on pharmgkb_diseases (name);

create table pharmgkb_annotation_diseases
(
    link_id       serial
        primary key,
    annotation_id bigint
        references pharmgkb_annotations,
    disease_id    integer
        references pharmgkb_diseases
);

alter table pharmgkb_annotation_diseases
    owner to postgres;

create index idx_annotation_diseases_annotation
    on pharmgkb_annotation_diseases (annotation_id);

create index idx_disease
    on pharmgkb_annotation_diseases (disease_id);

create table pharmgkb_variations
(
    variation_id serial
        primary key,
    pharmgkb_id  varchar(50)
        unique,
    name         varchar(255),
    obj_cls      varchar(50)
);

alter table pharmgkb_variations
    owner to postgres;

create index idx_variations_pharmgkb
    on pharmgkb_variations (pharmgkb_id);

create table pharmgkb_annotation_variations
(
    link_id       serial
        primary key,
    annotation_id bigint
        references pharmgkb_annotations,
    variation_id  integer
        references pharmgkb_variations
);

alter table pharmgkb_annotation_variations
    owner to postgres;

create index idx_annotation_variations_annotation
    on pharmgkb_annotation_variations (annotation_id);

create index idx_variation
    on pharmgkb_annotation_variations (variation_id);

create table medication_to_variant_links
(
    link_id                   serial
        primary key,
    patient_id                varchar(50)
        references patients,
    medication_id             integer
        references current_medications,
    variant_id                varchar(255),
    gene_symbol               varchar(20)
        references genes,
    rsid                      varchar(20),
    genotype                  varchar(50),
    diplotype                 varchar(50),
    phenotype                 varchar(100),
    allele                    varchar(50),
    recommendation            text,
    evidence_level            varchar(10),
    clinical_significance     varchar(100),
    clinical_annotation_types jsonb,
    pediatric                 boolean default false,
    severity                  varchar(20)
        constraint chk_severity
            check ((severity)::text = ANY
                   ((ARRAY ['CRITICAL'::character varying, 'WARNING'::character varying, 'INFO'::character varying, NULL::character varying])::text[])),
    match_method              varchar(50),
    pharmgkb_annotation_id    bigint
        references pharmgkb_annotations,
    timestamp                 timestamp
);

alter table medication_to_variant_links
    owner to postgres;

create index idx_patient
    on medication_to_variant_links (patient_id);

create index idx_medication
    on medication_to_variant_links (medication_id);

create index idx_med_to_variant_links_variant
    on medication_to_variant_links (variant_id);

create index idx_evidence_severity
    on medication_to_variant_links (evidence_level, severity);

create table variant_to_phenotype_links
(
    link_id        serial
        primary key,
    variant_id     varchar(255),
    gene_symbol    varchar(20)
        references genes,
    phenotype_text text,
    source         varchar(50),
    link_type      varchar(50)
);

alter table variant_to_phenotype_links
    owner to postgres;

create index idx_variant_to_phenotype_links_variant
    on variant_to_phenotype_links (variant_id);

create index idx_variant_to_phenotype_links_gene
    on variant_to_phenotype_links (gene_symbol);

create table drug_to_variant_links
(
    link_id                   serial
        primary key,
    drug_name                 varchar(255),
    snomed_code               varchar(20),
    variant_id                varchar(255),
    gene_symbol               varchar(20)
        references genes,
    rsid                      varchar(20),
    genotype                  varchar(50),
    diplotype                 varchar(50),
    phenotype                 varchar(100),
    allele                    varchar(50),
    interaction_type          varchar(50),
    recommendation            text,
    evidence_level            varchar(10),
    clinical_annotation_types jsonb,
    pediatric                 boolean default false,
    link_type                 varchar(50)
);

alter table drug_to_variant_links
    owner to postgres;

create index idx_drug
    on drug_to_variant_links (drug_name);

create index idx_drug_to_variant_links_variant
    on drug_to_variant_links (variant_id);

create index idx_drug_to_variant_links_gene
    on drug_to_variant_links (gene_symbol);

create table variant_drug_evidence
(
    evidence_id            serial
        primary key,
    variant_id             varchar(255),
    drug_name              varchar(255),
    pharmgkb_annotation_id bigint
        references pharmgkb_annotations,
    publication_pmid       integer,
    guideline_id           integer
        references pharmgkb_guidelines,
    label_id               integer
        references pharmgkb_labels,
    evidence_type          varchar(50),
    evidence_level         varchar(10)
);

comment on table variant_drug_evidence is 'Links variants to drugs with full evidence chain (annotations, guidelines, labels, publications)';

alter table variant_drug_evidence
    owner to postgres;

create index idx_variant_drug
    on variant_drug_evidence (variant_id, drug_name);

create index idx_variant_drug_evidence_annotation
    on variant_drug_evidence (pharmgkb_annotation_id);

create table disease_drug_variant_associations
(
    association_id   serial
        primary key,
    disease_snomed   varchar(20)
        references snomed_concepts,
    drug_name        varchar(255),
    variant_id       varchar(255),
    gene_symbol      varchar(20)
        references genes,
    association_type varchar(50),
    evidence_level   varchar(10),
    recommendation   text,
    source           varchar(50)
);

comment on table disease_drug_variant_associations is 'Triangle associations between diseases, drugs, and variants';

alter table disease_drug_variant_associations
    owner to postgres;

create index idx_disease_drug
    on disease_drug_variant_associations (disease_snomed, drug_name);

create index idx_drug_variant
    on disease_drug_variant_associations (drug_name, variant_id);

create table ethnicity_medication_adjustments
(
    adjustment_id           serial
        primary key,
    variant_id              varchar(255),
    gene_symbol             varchar(20)
        references genes,
    ethnicity               varchar(100),
    drug_name               varchar(255),
    adjustment_type         varchar(50),
    adjustment_factor       numeric(5, 2),
    recommendation          text,
    evidence_level          varchar(10),
    frequency_in_population numeric(10, 8)
);

comment on table ethnicity_medication_adjustments is 'Ethnicity-specific drug dosing and response adjustments';

alter table ethnicity_medication_adjustments
    owner to postgres;

create index idx_variant_ethnicity
    on ethnicity_medication_adjustments (variant_id, ethnicity);

create index idx_ethnicity_med_adj_drug
    on ethnicity_medication_adjustments (drug_name);

create index idx_ethnicity_med_adj_gene
    on ethnicity_medication_adjustments (gene_symbol);

create table patient_variant_population_context
(
    context_id                         serial
        primary key,
    patient_id                         varchar(50)
        references patients,
    variant_id                         varchar(255),
    patient_ethnicity                  varchar(100),
    frequency_in_patient_population    numeric(10, 8),
    population_significance            text,
    ethnicity_specific_drugs           jsonb,
    ethnicity_specific_recommendations jsonb
);

alter table patient_variant_population_context
    owner to postgres;

create index idx_patient_variant
    on patient_variant_population_context (patient_id, variant_id);

create table population_frequencies
(
    frequency_id     serial
        primary key,
    variant_id       varchar(255),
    gene_symbol      varchar(20)
        references genes,
    rsid             varchar(20),
    population       varchar(100),
    sub_population   varchar(100),
    allele           varchar(10),
    allele_count     integer,
    allele_number    integer,
    allele_frequency numeric(10, 8)
        constraint chk_frequency
            check ((allele_frequency >= (0)::numeric) AND (allele_frequency <= (1)::numeric)),
    homozygote_count integer,
    source           varchar(50),
    database_version varchar(50)
);

alter table population_frequencies
    owner to postgres;

create index idx_variant_pop
    on population_frequencies (variant_id, population);

create index idx_rsid_pop
    on population_frequencies (rsid, population);

create index idx_gene_pop
    on population_frequencies (gene_symbol, population);

create table recommended_tests
(
    test_id         serial
        primary key,
    variant_id      varchar(255),
    gene_symbol     varchar(20)
        references genes,
    test_name       varchar(255),
    test_type       varchar(100),
    indication      text,
    priority        varchar(20),
    lab_method      varchar(100),
    turnaround_time varchar(50)
);

alter table recommended_tests
    owner to postgres;

create index idx_recommended_tests_variant
    on recommended_tests (variant_id);

create index idx_recommended_tests_gene
    on recommended_tests (gene_symbol);

create index idx_priority
    on recommended_tests (priority);

create table publications
(
    pmid           integer not null
        primary key,
    pmcid          varchar(20),
    doi            varchar(255),
    title          text,
    authors        jsonb,
    journal        varchar(255),
    pub_year       integer,
    abstract       text,
    citation_count integer,
    url            varchar(500),
    source         varchar(50),
    evidence_code  varchar(50),
    full_text_url  varchar(500),
    pdf_url        varchar(500),
    metadata       jsonb
);

alter table publications
    owner to postgres;

create index idx_year
    on publications (pub_year);

create index idx_citations
    on publications (citation_count desc);

create index idx_title_fts
    on publications using gin (to_tsvector('english'::regconfig, title));

create index idx_abstract_fts
    on publications using gin (to_tsvector('english'::regconfig, abstract));

create table gene_publications
(
    link_id        serial
        primary key,
    gene_symbol    varchar(20)
        references genes,
    pmid           integer
        references publications,
    search_variant varchar(50)
);

alter table gene_publications
    owner to postgres;

create index idx_gene_publications_gene
    on gene_publications (gene_symbol);

create index idx_pmid
    on gene_publications (pmid);

create table variant_publications
(
    link_id     serial
        primary key,
    variant_id  varchar(255),
    gene_symbol varchar(20)
        references genes,
    pmid        integer
        references publications
);

alter table variant_publications
    owner to postgres;

create index idx_variant_publications_variant
    on variant_publications (variant_id);

create index idx_variant_publications_pmid
    on variant_publications (pmid);

create index idx_variant_publications_gene
    on variant_publications (gene_symbol);

create table pgx_conflicts
(
    conflict_id              serial
        primary key,
    patient_id               varchar(50)
        references patients,
    drug_name                varchar(255),
    medication_id            integer
        references current_medications,
    severity                 varchar(20)
        constraint chk_conflict_severity
            check ((severity)::text = ANY
                   ((ARRAY ['CRITICAL'::character varying, 'WARNING'::character varying, 'INFO'::character varying])::text[])),
    affecting_variants_count integer,
    match_method             varchar(50),
    recommendation           text,
    timestamp                timestamp
);

alter table pgx_conflicts
    owner to postgres;

create index idx_pgx_conflicts_patient
    on pgx_conflicts (patient_id);

create index idx_severity
    on pgx_conflicts (severity);

create index idx_severity_patient
    on pgx_conflicts (severity asc, patient_id asc, timestamp desc);

create table conflict_variants
(
    link_id               serial
        primary key,
    conflict_id           integer
        references pgx_conflicts,
    gene_symbol           varchar(20)
        references genes,
    variant_id            varchar(255),
    rsid                  varchar(20),
    recommendation        text,
    evidence_level        varchar(10),
    clinical_significance varchar(100)
);

alter table conflict_variants
    owner to postgres;

create index idx_conflict
    on conflict_variants (conflict_id);

create table snomed_mappings
(
    mapping_id   serial
        primary key,
    mapping_type varchar(50),
    snomed_code  varchar(20),
    label        varchar(255),
    entity_id    varchar(255),
    entity_type  varchar(50)
);

alter table snomed_mappings
    owner to postgres;

create index idx_type_code
    on snomed_mappings (mapping_type, snomed_code);

create table source_metadata
(
    source_name  varchar(50) not null
        primary key,
    version      varchar(50),
    last_updated date,
    description  text
);

comment on table source_metadata is 'Tracks the versions of external data sources (PharmGKB, ClinVar) loaded into the database.';

alter table source_metadata
    owner to postgres;

create index idx_last_updated
    on source_metadata (last_updated);

create table patient_variants_history
(
    history_id                serial
        primary key,
    patient_variant_id        integer,
    patient_id                varchar(50),
    gene_symbol               varchar(20),
    variant_id                varchar(255),
    old_phenotype             varchar(100),
    new_phenotype             varchar(100),
    old_clinical_significance varchar(100),
    new_clinical_significance varchar(100),
    changed_by                varchar(100),
    changed_at                timestamp default CURRENT_TIMESTAMP,
    change_reason             text
);

alter table patient_variants_history
    owner to postgres;

create index idx_patient_history
    on patient_variants_history (patient_id asc, changed_at desc);

create table drug_publications
(
    link_id         serial
        primary key,
    drug_name       varchar(255),
    pmid            integer
        references publications,
    relevance_score numeric(10, 4),
    search_query    text
);

alter table drug_publications
    owner to postgres;

create index idx_drug_publications_drug
    on drug_publications (drug_name);

create index idx_drug_publications_pmid
    on drug_publications (pmid);

create view current_medication_pgx
            (patient_id, name, drug_name, drugbank_id, gene_symbol, diplotype, phenotype, recommendation,
             evidence_level, severity, clinical_annotation_types, annotation_name, pediatric)
as
SELECT p.patient_id,
       p.name,
       cm.drug_name,
       cm.drugbank_id,
       pv.gene_symbol,
       pv.diplotype,
       pv.phenotype,
       mvl.recommendation,
       mvl.evidence_level,
       mvl.severity,
       mvl.clinical_annotation_types,
       pa.annotation_name,
       pa.pediatric
FROM patients p
         JOIN current_medications cm ON p.patient_id::text = cm.patient_id::text
         JOIN patient_variants pv ON p.patient_id::text = pv.patient_id::text
         LEFT JOIN medication_to_variant_links mvl
                   ON mvl.patient_id::text = p.patient_id::text AND mvl.medication_id = cm.medication_id AND
                      mvl.gene_symbol::text = pv.gene_symbol::text
         LEFT JOIN pharmgkb_annotations pa ON mvl.pharmgkb_annotation_id = pa.annotation_id;

alter table current_medication_pgx
    owner to postgres;

create view patient_pgx_profile
            (patient_id, name, ethnicity, gene_symbol, variant_id, diplotype, phenotype, clinical_significance,
             affected_drugs, highest_evidence, high_evidence_drugs)
as
SELECT p.patient_id,
       p.name,
       d.ethnicity,
       pv.gene_symbol,
       pv.variant_id,
       pv.diplotype,
       pv.phenotype,
       pv.clinical_significance,
       count(DISTINCT dvl.drug_name)                                                                                       AS affected_drugs,
       max(pa.evidence_level::text)                                                                                        AS highest_evidence,
       array_agg(DISTINCT dvl.drug_name) FILTER (WHERE dvl.evidence_level::text = ANY
                                                       (ARRAY ['1A'::character varying, '1B'::character varying]::text[])) AS high_evidence_drugs
FROM patients p
         JOIN demographics d ON p.patient_id::text = d.patient_id::text
         JOIN patient_variants pv ON p.patient_id::text = pv.patient_id::text
         LEFT JOIN drug_to_variant_links dvl ON pv.variant_id::text = dvl.variant_id::text
         LEFT JOIN pharmgkb_annotations pa ON pv.variant_id::text = pa.variant_id::text
GROUP BY p.patient_id, p.name, d.ethnicity, pv.gene_symbol, pv.variant_id, pv.diplotype, pv.phenotype,
         pv.clinical_significance;

alter table patient_pgx_profile
    owner to postgres;

create view snomed_integrated_patient
            (patient_id, name, condition_snomed, condition_name, drug_name, treats_condition_snomed, lifestyle_snomed,
             lifestyle_factor, lab_snomed, lab_test, value, unit, status)
as
SELECT p.patient_id,
       p.name,
       cc.snomed_code  AS condition_snomed,
       cc.rdfs_label   AS condition_name,
       cm.drug_name,
       cm.treats_condition_snomed,
       lf.snomed_code  AS lifestyle_snomed,
       lf.rdfs_label   AS lifestyle_factor,
       ofl.snomed_code AS lab_snomed,
       ofl.rdfs_label  AS lab_test,
       ofl.value,
       ofl.unit,
       ofl.status
FROM patients p
         LEFT JOIN current_conditions cc ON p.patient_id::text = cc.patient_id::text
         LEFT JOIN current_medications cm ON p.patient_id::text = cm.patient_id::text
         LEFT JOIN lifestyle_factors lf ON p.patient_id::text = lf.patient_id::text
         LEFT JOIN organ_function_labs ofl ON p.patient_id::text = ofl.patient_id::text;

alter table snomed_integrated_patient
    owner to postgres;

create view patient_comprehensive_risk
            (patient_id, name, ethnicity, total_variants, pathogenic_variants, medications_with_pgx_data,
             critical_drug_interactions, warning_drug_interactions, total_conflicts, affected_genes,
             high_risk_medications)
as
SELECT p.patient_id,
       p.name,
       d.ethnicity,
       count(DISTINCT pv.variant_id)                                                                         AS total_variants,
       count(DISTINCT
             CASE
                 WHEN pv.clinical_significance::text ~~ '%pathogenic%'::text THEN pv.variant_id
                 ELSE NULL::character varying
                 END)                                                                                        AS pathogenic_variants,
       count(DISTINCT mvl.medication_id)                                                                     AS medications_with_pgx_data,
       count(DISTINCT
             CASE
                 WHEN mvl.severity::text = 'CRITICAL'::text THEN mvl.medication_id
                 ELSE NULL::integer
                 END)                                                                                        AS critical_drug_interactions,
       count(DISTINCT
             CASE
                 WHEN mvl.severity::text = 'WARNING'::text THEN mvl.medication_id
                 ELSE NULL::integer
                 END)                                                                                        AS warning_drug_interactions,
       count(DISTINCT pc.conflict_id)                                                                        AS total_conflicts,
       array_agg(DISTINCT pv.gene_symbol ORDER BY pv.gene_symbol)                                            AS affected_genes,
       array_agg(DISTINCT
       CASE
           WHEN mvl.severity::text = ANY (ARRAY ['CRITICAL'::character varying, 'WARNING'::character varying]::text[])
               THEN cm.drug_name
           ELSE NULL::character varying
           END) FILTER (WHERE mvl.severity::text = ANY
                              (ARRAY ['CRITICAL'::character varying, 'WARNING'::character varying]::text[])) AS high_risk_medications
FROM patients p
         JOIN demographics d ON p.patient_id::text = d.patient_id::text
         LEFT JOIN patient_variants pv ON p.patient_id::text = pv.patient_id::text
         LEFT JOIN medication_to_variant_links mvl ON p.patient_id::text = mvl.patient_id::text
         LEFT JOIN current_medications cm ON mvl.medication_id = cm.medication_id
         LEFT JOIN pgx_conflicts pc ON p.patient_id::text = pc.patient_id::text
GROUP BY p.patient_id, p.name, d.ethnicity;

comment on view patient_comprehensive_risk is 'Complete patient risk profile including variants, medications, and conflicts';

alter table patient_comprehensive_risk
    owner to postgres;

create view ethnicity_medication_recommendations
            (ethnicity, drug_name, gene_symbol, diplotype, phenotype, population_frequency, recommendation,
             evidence_level, affected_patients)
as
SELECT d.ethnicity,
       cm.drug_name,
       pv.gene_symbol,
       pv.diplotype,
       pv.phenotype,
       pf.allele_frequency          AS population_frequency,
       mvl.recommendation,
       mvl.evidence_level,
       count(DISTINCT p.patient_id) AS affected_patients
FROM demographics d
         JOIN patients p ON d.patient_id::text = p.patient_id::text
         JOIN current_medications cm ON p.patient_id::text = cm.patient_id::text
         JOIN patient_variants pv ON p.patient_id::text = pv.patient_id::text
         JOIN medication_to_variant_links mvl
              ON mvl.patient_id::text = p.patient_id::text AND mvl.medication_id = cm.medication_id AND
                 mvl.gene_symbol::text = pv.gene_symbol::text
         LEFT JOIN population_frequencies pf
                   ON pf.variant_id::text = pv.variant_id::text AND pf.population::text = (d.ethnicity ->> 0)
WHERE mvl.evidence_level::text = ANY
      (ARRAY ['1A'::character varying, '1B'::character varying, '2A'::character varying]::text[])
GROUP BY d.ethnicity, cm.drug_name, pv.gene_symbol, pv.diplotype, pv.phenotype, pf.allele_frequency, mvl.recommendation,
         mvl.evidence_level;

alter table ethnicity_medication_recommendations
    owner to postgres;

create view high_impact_variants
            (variant_id, gene_symbol, rsid, phenotype, clinical_significance, affected_drugs, supporting_publications,
             highest_evidence_level, high_evidence_drugs, avg_citation_count)
as
SELECT pv.variant_id,
       pv.gene_symbol,
       pv.rsid,
       pv.phenotype,
       pv.clinical_significance,
       count(DISTINCT dvl.drug_name)                                                                                                                                       AS affected_drugs,
       count(DISTINCT vp.pmid)                                                                                                                                             AS supporting_publications,
       max(pa.evidence_level::text)                                                                                                                                        AS highest_evidence_level,
       array_agg(DISTINCT dvl.drug_name ORDER BY dvl.drug_name) FILTER (WHERE dvl.evidence_level::text = ANY
                                                                              (ARRAY ['1A'::character varying, '1B'::character varying, '2A'::character varying]::text[])) AS high_evidence_drugs,
       avg(pub.citation_count)                                                                                                                                             AS avg_citation_count
FROM patient_variants pv
         LEFT JOIN drug_to_variant_links dvl ON pv.variant_id::text = dvl.variant_id::text
         LEFT JOIN variant_publications vp ON pv.variant_id::text = vp.variant_id::text
         LEFT JOIN publications pub ON vp.pmid = pub.pmid
         LEFT JOIN pharmgkb_annotations pa ON pv.variant_id::text = pa.variant_id::text
WHERE pv.clinical_significance::text = ANY
      (ARRAY ['Pathogenic'::character varying, 'Likely pathogenic'::character varying, 'Drug response'::character varying]::text[])
GROUP BY pv.variant_id, pv.gene_symbol, pv.rsid, pv.phenotype, pv.clinical_significance
HAVING count(DISTINCT dvl.drug_name) > 0;

alter table high_impact_variants
    owner to postgres;

create function set_limit(real) returns real
    strict
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function set_limit(real) owner to postgres;

create function show_limit() returns real
    stable
    strict
    parallel safe
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function show_limit() owner to postgres;

create function show_trgm(text) returns text[]
    immutable
    strict
    parallel safe
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function show_trgm(text) owner to postgres;

create function similarity(text, text) returns real
    immutable
    strict
    parallel safe
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function similarity(text, text) owner to postgres;

create function similarity_op(text, text) returns boolean
    stable
    strict
    parallel safe
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function similarity_op(text, text) owner to postgres;

create function word_similarity(text, text) returns real
    immutable
    strict
    parallel safe
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function word_similarity(text, text) owner to postgres;

create function word_similarity_op(text, text) returns boolean
    stable
    strict
    parallel safe
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function word_similarity_op(text, text) owner to postgres;

create function word_similarity_commutator_op(text, text) returns boolean
    stable
    strict
    parallel safe
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function word_similarity_commutator_op(text, text) owner to postgres;

create function similarity_dist(text, text) returns real
    immutable
    strict
    parallel safe
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function similarity_dist(text, text) owner to postgres;

create function word_similarity_dist_op(text, text) returns real
    immutable
    strict
    parallel safe
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function word_similarity_dist_op(text, text) owner to postgres;

create function word_similarity_dist_commutator_op(text, text) returns real
    immutable
    strict
    parallel safe
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function word_similarity_dist_commutator_op(text, text) owner to postgres;

create function gtrgm_in(cstring) returns gtrgm
    immutable
    strict
    parallel safe
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function gtrgm_in(cstring) owner to postgres;

create function gtrgm_out(gtrgm) returns cstring
    immutable
    strict
    parallel safe
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function gtrgm_out(gtrgm) owner to postgres;

create function gtrgm_consistent(internal, text, smallint, oid, internal) returns boolean
    immutable
    strict
    parallel safe
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function gtrgm_consistent(internal, text, smallint, oid, internal) owner to postgres;

create function gtrgm_distance(internal, text, smallint, oid, internal) returns double precision
    immutable
    strict
    parallel safe
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function gtrgm_distance(internal, text, smallint, oid, internal) owner to postgres;

create function gtrgm_compress(internal) returns internal
    immutable
    strict
    parallel safe
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function gtrgm_compress(internal) owner to postgres;

create function gtrgm_decompress(internal) returns internal
    immutable
    strict
    parallel safe
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function gtrgm_decompress(internal) owner to postgres;

create function gtrgm_penalty(internal, internal, internal) returns internal
    immutable
    strict
    parallel safe
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function gtrgm_penalty(internal, internal, internal) owner to postgres;

create function gtrgm_picksplit(internal, internal) returns internal
    immutable
    strict
    parallel safe
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function gtrgm_picksplit(internal, internal) owner to postgres;

create function gtrgm_union(internal, internal) returns gtrgm
    immutable
    strict
    parallel safe
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function gtrgm_union(internal, internal) owner to postgres;

create function gtrgm_same(gtrgm, gtrgm, internal) returns internal
    immutable
    strict
    parallel safe
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function gtrgm_same(gtrgm, gtrgm, internal) owner to postgres;

create function gin_extract_value_trgm(text, internal) returns internal
    immutable
    strict
    parallel safe
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function gin_extract_value_trgm(text, internal) owner to postgres;

create function gin_extract_query_trgm(text, internal, smallint, internal, internal, internal, internal) returns internal
    immutable
    strict
    parallel safe
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function gin_extract_query_trgm(text, internal, smallint, internal, internal, internal, internal) owner to postgres;

create function gin_trgm_consistent(internal, smallint, text, integer, internal, internal, internal, internal) returns boolean
    immutable
    strict
    parallel safe
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function gin_trgm_consistent(internal, smallint, text, integer, internal, internal, internal, internal) owner to postgres;

create function gin_trgm_triconsistent(internal, smallint, text, integer, internal, internal, internal) returns "char"
    immutable
    strict
    parallel safe
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function gin_trgm_triconsistent(internal, smallint, text, integer, internal, internal, internal) owner to postgres;

create function strict_word_similarity(text, text) returns real
    immutable
    strict
    parallel safe
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function strict_word_similarity(text, text) owner to postgres;

create function strict_word_similarity_op(text, text) returns boolean
    stable
    strict
    parallel safe
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function strict_word_similarity_op(text, text) owner to postgres;

create function strict_word_similarity_commutator_op(text, text) returns boolean
    stable
    strict
    parallel safe
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function strict_word_similarity_commutator_op(text, text) owner to postgres;

create function strict_word_similarity_dist_op(text, text) returns real
    immutable
    strict
    parallel safe
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function strict_word_similarity_dist_op(text, text) owner to postgres;

create function strict_word_similarity_dist_commutator_op(text, text) returns real
    immutable
    strict
    parallel safe
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function strict_word_similarity_dist_commutator_op(text, text) owner to postgres;

create function gtrgm_options(internal) returns void
    immutable
    parallel safe
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function gtrgm_options(internal) owner to postgres;

create function track_variant_changes() returns trigger
    language plpgsql
as
$$
BEGIN
    IF OLD.phenotype IS DISTINCT FROM NEW.phenotype OR 
       OLD.clinical_significance IS DISTINCT FROM NEW.clinical_significance THEN
        INSERT INTO patient_variants_history (
            patient_variant_id, patient_id, gene_symbol, variant_id,
            old_phenotype, new_phenotype,
            old_clinical_significance, new_clinical_significance,
            changed_by, change_reason
        ) VALUES (
            OLD.patient_variant_id, OLD.patient_id, OLD.gene_symbol, OLD.variant_id,
            OLD.phenotype, NEW.phenotype,
            OLD.clinical_significance, NEW.clinical_significance,
            current_user, 'Updated via application'
        );
    END IF;
    RETURN NEW;
END;
$$;

alter function track_variant_changes() owner to postgres;

create trigger variant_change_tracker
    after update
    on patient_variants
    for each row
execute procedure track_variant_changes();

create operator % (procedure = similarity_op, leftarg = text, rightarg = text, commutator = %, join = matchingjoinsel, restrict = matchingsel);

alter operator %(text, text) owner to postgres;

create operator <-> (procedure = similarity_dist, leftarg = text, rightarg = text, commutator = <->);

alter operator <->(text, text) owner to postgres;

create operator family gist_trgm_ops using gist;

alter operator family gist_trgm_ops using gist add
    operator 1 %(text, text),
    operator 2 <->(text, text) for order by float_ops,
    operator 3 ~~(text,text),
    operator 4 ~~*(text,text),
    operator 5 ~(text,text),
    operator 6 ~*(text,text),
    operator 7 %>(text, text),
    operator 8 <->>(text, text) for order by float_ops,
    operator 9 %>>(text, text),
    operator 10 <->>>(text, text) for order by float_ops,
    operator 11 =(text,text),
    function 6(text, text) gtrgm_picksplit(internal, internal),
    function 7(text, text) gtrgm_same(gtrgm, gtrgm, internal),
    function 8(text, text) gtrgm_distance(internal, text, smallint, oid, internal),
    function 10(text, text) gtrgm_options(internal),
    function 2(text, text) gtrgm_union(internal, internal),
    function 3(text, text) gtrgm_compress(internal),
    function 4(text, text) gtrgm_decompress(internal),
    function 5(text, text) gtrgm_penalty(internal, internal, internal),
    function 1(text, text) gtrgm_consistent(internal, text, smallint, oid, internal);

alter operator family gist_trgm_ops using gist owner to postgres;

create operator class gist_trgm_ops for type text using gist as storage gtrgm function 6(text, text) gtrgm_picksplit(internal, internal),
	function 1(text, text) gtrgm_consistent(internal, text, smallint, oid, internal),
	function 7(text, text) gtrgm_same(gtrgm, gtrgm, internal),
	function 5(text, text) gtrgm_penalty(internal, internal, internal),
	function 2(text, text) gtrgm_union(internal, internal);

alter operator class gist_trgm_ops using gist owner to postgres;

create operator family gin_trgm_ops using gin;

alter operator family gin_trgm_ops using gin add
    operator 6 ~*(text,text),
    operator 7 %>(text, text),
    operator 11 =(text,text),
    operator 9 %>>(text, text),
    operator 1 %(text, text),
    operator 3 ~~(text,text),
    operator 4 ~~*(text,text),
    operator 5 ~(text,text),
    function 1(text, text) btint4cmp(integer,integer),
    function 4(text, text) gin_trgm_consistent(internal, smallint, text, integer, internal, internal, internal, internal),
    function 6(text, text) gin_trgm_triconsistent(internal, smallint, text, integer, internal, internal, internal),
    function 2(text, text) gin_extract_value_trgm(text, internal),
    function 3(text, text) gin_extract_query_trgm(text, internal, smallint, internal, internal, internal, internal);

alter operator family gin_trgm_ops using gin owner to postgres;

create operator class gin_trgm_ops for type text using gin as storage integer function 3(text, text) gin_extract_query_trgm(text, internal, smallint, internal, internal, internal, internal),
	function 2(text, text) gin_extract_value_trgm(text, internal);

alter operator class gin_trgm_ops using gin owner to postgres;

-- Cyclic dependencies found

create operator %> (procedure = word_similarity_commutator_op, leftarg = text, rightarg = text, commutator = <%, join = matchingjoinsel, restrict = matchingsel);

alter operator %>(text, text) owner to postgres;

create operator <% (procedure = word_similarity_op, leftarg = text, rightarg = text, commutator = %>, join = matchingjoinsel, restrict = matchingsel);

alter operator <%(text, text) owner to postgres;

-- Cyclic dependencies found

create operator %>> (procedure = strict_word_similarity_commutator_op, leftarg = text, rightarg = text, commutator = <<%, join = matchingjoinsel, restrict = matchingsel);

alter operator %>>(text, text) owner to postgres;

create operator <<% (procedure = strict_word_similarity_op, leftarg = text, rightarg = text, commutator = %>>, join = matchingjoinsel, restrict = matchingsel);

alter operator <<%(text, text) owner to postgres;

-- Cyclic dependencies found

create operator <->> (procedure = word_similarity_dist_commutator_op, leftarg = text, rightarg = text, commutator = <<->);

alter operator <->>(text, text) owner to postgres;

create operator <<-> (procedure = word_similarity_dist_op, leftarg = text, rightarg = text, commutator = <->>);

alter operator <<->(text, text) owner to postgres;

-- Cyclic dependencies found

create operator <->>> (procedure = strict_word_similarity_dist_commutator_op, leftarg = text, rightarg = text, commutator = <<<->);

alter operator <->>>(text, text) owner to postgres;

create operator <<<-> (procedure = strict_word_similarity_dist_op, leftarg = text, rightarg = text, commutator = <->>>);

alter operator <<<->(text, text) owner to postgres;


