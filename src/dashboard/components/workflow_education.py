"""
Educational content for pharmacogenomics workflow
Making complex science accessible, engaging, and fun!
"""

# Educational explanations for each workflow stage
STAGE_EDUCATION = {
    "lab": {
        "title": "🧪 Lab Preparation",
        "what_happening": """
        We're extracting your DNA from a blood or saliva sample and preparing it for sequencing.
        Think of it like preparing ingredients before cooking - we need to get the DNA clean,
        pure, and in the right format for the sequencing machine to read.
        """,
        "science_behind": """
        **DNA Extraction**: Cells are broken open (lysed) to release DNA, which is then purified
        using magnetic beads or column-based methods. We check purity using spectrophotometry
        (A260/A280 ratio should be ~1.8).

        **Fragmentation**: DNA is cut into smaller pieces (~150-300bp) because sequencers can't
        read the entire genome at once - like reading a book one page at a time.

        **Library Prep**: We add special adapters to DNA fragments (like bookmarks) so the
        sequencing machine knows where to start and stop reading.
        """,
        "fun_fact": """
        💡 **Did you know?** The DNA from one human cell is about 2 meters long when stretched out!
        But it's coiled so tightly that it fits inside a nucleus smaller than a grain of salt.
        We have about 37 trillion cells in our body - that's enough DNA to stretch from Earth
        to the Sun and back 100 times! 🌞
        """,
        "data_transform": """
        **Input**: Patient sample (blood/saliva)
        **Output**: DNA library ready for sequencing
        **Quality Metrics**: Purity (A260/A280), Concentration (ng/µL), Fragment size
        """
    },

    "ngs": {
        "title": "🧬 Next-Generation Sequencing (NGS)",
        "what_happening": """
        The sequencing machine is "reading" your DNA letter by letter. Your DNA is made up of
        four chemical letters: A (adenine), T (thymine), C (cytosine), and G (guanine).
        The machine captures light signals as each letter is read, converting them into digital data.
        """,
        "science_behind": """
        **Flowcell Loading**: DNA fragments are loaded onto a glass slide (flowcell) where they
        attach and form clusters - millions of copies of each fragment in one spot.

        **Basecalling**: As the sequencer adds fluorescent nucleotides (A, T, C, G), it takes
        pictures. Each nucleotide glows a different color. Software converts these color signals
        into DNA sequences with quality scores (Q-scores, where Q30 = 99.9% accuracy).

        **Alignment**: Using BWA-MEM algorithm, we align millions of short DNA reads to the
        reference human genome (GRCh38) - like finding where each puzzle piece fits.

        **Variant Calling**: We compare your DNA to the reference genome to find differences
        (variants). Most people have 4-5 million variants - only a tiny fraction affect medications!
        """,
        "fun_fact": """
        💡 **Time Travel!** The Human Genome Project (2003) took 13 years and cost $3 billion
        to sequence one human genome. Today's sequencers can do it in 24 hours for under $1,000.
        For pharmacogenomics, we only need to look at ~200 genes, which takes just minutes! ⚡
        """,
        "data_transform": """
        **Input**: DNA library
        **Processing**:
          - FASTQ files (raw sequences: ATCGATCGTA... with quality scores)
          - BAM files (aligned reads mapped to genome positions)
          - VCF files (variants: chr1:12345 A→G)
        **Output**: List of genetic variants in pharmacogenes
        **Metrics**: Coverage (%), Read depth (30-100x), Mapping quality
        """
    },

    "anno": {
        "title": "🔬 Variant Annotation",
        "what_happening": """
        We're looking up each genetic variant in multiple scientific databases to understand:
        What is it called? Is it clinically important? Does it affect any medications?
        It's like using multiple dictionaries to translate a word and understand all its meanings.
        """,
        "science_behind": """
        **Database Queries** (running in parallel):

        🔹 **dbSNP**: The reference SNP database assigns unique IDs (like rs4244285) to known
        variants. Think of it as the "phone book" for DNA changes - it gives each variant a name.

        🔹 **ClinVar**: Aggregates information about relationships between variants and health.
        Classifies variants as: Benign, Likely benign, Uncertain significance, Likely pathogenic,
        or Pathogenic. Curated by clinical geneticists worldwide.

        🔹 **PharmGKB**: The Pharmacogenomics Knowledge Base contains drug-gene relationships,
        clinical annotations, and dosing guidelines. Levels of evidence:
          - Level 1A: CPIC/FDA guidelines exist
          - Level 1B: Published clinical annotations
          - Levels 2-4: Lower levels of evidence

        🔹 **Europe PMC**: We search scientific literature for recent research papers about
        each variant, giving you access to cutting-edge findings.

        **Data Enrichment Pipeline**:
        ```
        chr7:117559590 G→A
          ↓ dbSNP
        rs1799853 (CYP2C9*2)
          ↓ ClinVar
        "Pathogenic for drug metabolism"
          ↓ PharmGKB
        "Reduced warfarin metabolism - 25-50% dose reduction recommended"
          ↓ Literature
        "1,247 publications"
        ```
        """,
        "fun_fact": """
        💡 **Knowledge at Scale!** PharmGKB contains:
        - 700+ drug-gene pairs
        - 150+ CPIC guidelines
        - 7,000+ clinical annotations
        - 50,000+ genetic variants

        We query all these databases in seconds using parallel API calls - like having 100
        research assistants working simultaneously! 🚀
        """,
        "data_transform": """
        **Input**: Raw variants (chr:pos ref>alt)
        **Processing**: Database lookups and evidence aggregation
        **Output**: Fully annotated variants with clinical significance
        **Databases Connected**: dbSNP, ClinVar, PharmGKB, Europe PMC, gnomAD
        """
    },

    "drug": {
        "title": "💊 Drug-Gene Interaction Analysis",
        "what_happening": """
        Now we connect the dots! We're building a network showing how your genetic variants
        affect medications you might take. Each connection is color-coded by severity:
        Green (safe), Yellow (caution), Red (critical - needs dosing change).
        """,
        "science_behind": """
        **Drug-Gene Network Construction**:
        We create a knowledge graph linking:
        - Your genetic variants (genotype)
        - Your phenotype (how the gene functions: Normal, Intermediate, Poor metabolizer)
        - Medications affected by those genes
        - Clinical guidelines (CPIC, DPWG, FDA)

        **Risk Assessment Algorithm**:
        1. **Phenotype Prediction**: Determine metabolizer status from diplotypes
           - Example: CYP2D6 *1/*4 = Intermediate Metabolizer

        2. **Guideline Matching**: Look up CPIC recommendations for each drug-gene pair
           - Example: CYP2D6 IM + Codeine = "Use alternative analgesic"

        3. **Severity Scoring**:
           - 🟢 **Low**: No dosing change needed
           - 🟡 **Moderate**: Consider dose adjustment or monitoring
           - 🔴 **High**: Strong recommendation for alternative or significant dose change
           - ⚫ **Critical**: Contraindicated or life-threatening interaction

        **Clinical Guidelines Sources**:
        - **CPIC** (Clinical Pharmacogenetics Implementation Consortium): Evidence-based guidelines
        - **DPWG** (Dutch Pharmacogenetics Working Group): European recommendations
        - **FDA**: Drug labeling updates with PGx information
        - **PharmGKB**: Curated clinical annotations
        """,
        "fun_fact": """
        💡 **Real-World Impact!** Studies show:
        - 99% of people carry at least one actionable pharmacogenetic variant
        - Implementing PGx testing reduces adverse drug events by 30-50%
        - For every $1 spent on PGx testing, healthcare systems save $4-7 in reduced complications

        One genetic test can guide medication choices for your entire life! 🎯
        """,
        "data_transform": """
        **Input**: Annotated variants + patient medications
        **Processing**:
          - Diplotype → Phenotype translation
          - Guideline lookups (CPIC/DPWG/FDA)
          - Risk scoring and prioritization
        **Output**: Actionable drug-gene interaction alerts with recommendations
        **Network Nodes**: Genes, Variants, Drugs, Guidelines, Recommendations
        """
    },

    "report": {
        "title": "📊 Report Generation",
        "what_happening": """
        We're compiling everything into a comprehensive clinical report that doctors can use
        to make informed medication decisions. The report is generated in multiple formats
        for different uses - from human-readable PDFs to machine-readable data for health systems.
        """,
        "science_behind": """
        **Report Compilation Pipeline**:

        1. **Data Aggregation**: Collect all analysis results:
           - Genetic variants per gene
           - Phenotype predictions
           - Drug interactions
           - Clinical guidelines
           - Literature evidence

        2. **Prioritization**: Sort findings by clinical importance:
           - Critical alerts first (actionable, high-evidence)
           - Moderate recommendations
           - Informational findings

        3. **Multi-Format Export**:

           📄 **PDF/HTML**: Human-readable clinical report with:
           - Executive summary
           - Gene-by-gene results
           - Drug interaction matrix
           - Evidence levels and references
           - Clinical recommendations

           💾 **JSON-LD**: Machine-readable structured data using standardized vocabularies:
           - Schema.org for general structure
           - FHIR (Fast Healthcare Interoperability Resources) compatible
           - Ready for EHR integration

           🔗 **RDF/Turtle**: Semantic web format for:
           - Knowledge graph representation
           - Interoperability with research databases
           - Advanced querying capabilities

           📋 **Summary TXT**: Quick reference for providers

        **Quality Assurance**:
        - Automated checks for completeness
        - Cross-referencing with latest guidelines
        - Citation tracking for all claims
        """,
        "fun_fact": """
        💡 **From Research to Bedside!** This report format follows international standards:
        - HL7 FHIR for healthcare interoperability
        - GA4GH (Global Alliance for Genomics and Health) standards
        - ACMG (American College of Medical Genetics) recommendations

        Your report can be understood by health systems worldwide! 🌍

        **Bonus**: The entire analysis that used to require a PhD bioinformatician and take
        days now happens automatically in minutes. Welcome to the future of precision medicine! ✨
        """,
        "data_transform": """
        **Input**: All analysis results + clinical annotations
        **Processing**: Template rendering, format conversion, quality checks
        **Output**: Multi-format clinical reports
        **Formats**: PDF, HTML, JSON-LD, RDF/Turtle, Plain Text Summary
        """
    }
}

# Data flow visualization for the entire pipeline
PIPELINE_DATA_FLOW = {
    "title": "📊 Complete Data Flow Pipeline",
    "description": "From patient sample to clinical decision",
    "flow_steps": [
        {
            "step": 1,
            "icon": "🩸",
            "name": "Patient Sample",
            "description": "Blood, saliva, or buccal swab",
            "data_type": "Biological material",
            "example": "5mL blood in EDTA tube"
        },
        {
            "step": 2,
            "icon": "🧬",
            "name": "DNA Molecules",
            "description": "Extracted and purified genomic DNA",
            "data_type": "Biological macromolecule",
            "example": "50 ng/µL DNA, A260/A280 = 1.8"
        },
        {
            "step": 3,
            "icon": "📝",
            "name": "FASTQ Files",
            "description": "Raw sequencing reads with quality scores",
            "data_type": "Text file (~5-10 GB)",
            "example": "@READ1\\nATCGATCG...\\n+\\nFFFFFFFF... (Q30+ scores)"
        },
        {
            "step": 4,
            "icon": "🗺️",
            "name": "BAM Files",
            "description": "Aligned reads mapped to reference genome",
            "data_type": "Binary alignment file (~2-5 GB)",
            "example": "chr7:117559590 30M, MAPQ=60"
        },
        {
            "step": 5,
            "icon": "🔍",
            "name": "VCF Files",
            "description": "Called variants (differences from reference)",
            "data_type": "Variant call format (~1-10 MB)",
            "example": "chr7:117559590 G>A, DP=45, GQ=99"
        },
        {
            "step": 6,
            "icon": "📚",
            "name": "Annotated Variants",
            "description": "Variants enriched with clinical information",
            "data_type": "Structured database records",
            "example": "rs1799853, CYP2C9*2, Pathogenic, Warfarin"
        },
        {
            "step": 7,
            "icon": "⚕️",
            "name": "Clinical Report",
            "description": "Actionable medication recommendations",
            "data_type": "Multi-format report",
            "example": "CYP2C9 IM: Reduce warfarin dose 25-50%"
        }
    ]
}

# Database connection explanations
DATABASE_CONNECTIONS = {
    "title": "🗄️ Scientific Databases We Query",
    "description": "Your genetic data is enriched using world-class research databases",
    "databases": [
        {
            "name": "dbSNP",
            "icon": "🆔",
            "full_name": "Single Nucleotide Polymorphism Database",
            "purpose": "Assigns unique IDs to genetic variants",
            "maintained_by": "NCBI (National Center for Biotechnology Information)",
            "size": "~1 billion variants catalogued",
            "analogy": "Like a phone book - gives each variant a unique name (rs number)",
            "example": "chr7:117559590 G>A → rs1799853",
            "url": "https://www.ncbi.nlm.nih.gov/snp/"
        },
        {
            "name": "ClinVar",
            "icon": "🏥",
            "full_name": "Clinical Variant Database",
            "purpose": "Clinical significance and disease associations",
            "maintained_by": "NCBI, submitted by clinical laboratories worldwide",
            "size": "~2.5 million variant-condition relationships",
            "analogy": "Like a medical encyclopedia - tells us if a variant causes disease",
            "example": "rs1799853 → Pathogenic for drug metabolism",
            "url": "https://www.ncbi.nlm.nih.gov/clinvar/"
        },
        {
            "name": "PharmGKB",
            "icon": "💊",
            "full_name": "Pharmacogenomics Knowledge Base",
            "purpose": "Drug-gene interactions and dosing guidelines",
            "maintained_by": "Stanford University, NIH-funded",
            "size": "700+ drug-gene pairs, 150+ CPIC guidelines",
            "analogy": "Like a medication safety manual - tells us how genes affect drugs",
            "example": "CYP2C9*2 + Warfarin → Reduce dose 25-50%",
            "url": "https://www.pharmgkb.org/"
        },
        {
            "name": "CPIC",
            "icon": "📋",
            "full_name": "Clinical Pharmacogenetics Implementation Consortium",
            "purpose": "Evidence-based prescribing guidelines",
            "maintained_by": "International consortium of experts",
            "size": "24 genes, 90+ drug guidelines",
            "analogy": "Like a recipe book - gives step-by-step medication guidance",
            "example": "CYP2D6 PM: Avoid codeine, use alternative",
            "url": "https://cpicpgx.org/"
        },
        {
            "name": "gnomAD",
            "icon": "🌍",
            "full_name": "Genome Aggregation Database",
            "purpose": "Population frequency of variants",
            "maintained_by": "Broad Institute",
            "size": "750,000+ genomes and exomes",
            "analogy": "Like a census - shows how common each variant is",
            "example": "rs1799853: 12% frequency in Europeans",
            "url": "https://gnomad.broadinstitute.org/"
        },
        {
            "name": "Europe PMC",
            "icon": "📖",
            "full_name": "Europe PubMed Central",
            "purpose": "Scientific literature search",
            "maintained_by": "European Bioinformatics Institute",
            "size": "40+ million scientific articles",
            "analogy": "Like Google Scholar - finds research papers about variants",
            "example": "1,247 publications about CYP2C9*2",
            "url": "https://europepmc.org/"
        }
    ]
}

# How this app works explanation
APP_ARCHITECTURE = {
    "title": "🔧 How This App Works",
    "description": "Behind the scenes of automated pharmacogenomic analysis",
    "components": [
        {
            "name": "Frontend Interface",
            "icon": "🖥️",
            "tech": "Streamlit (Python)",
            "purpose": "User interface for patient data and results",
            "features": ["Patient profile creation", "Gene selection", "Report visualization"]
        },
        {
            "name": "Analysis Pipeline",
            "icon": "⚙️",
            "tech": "Multi-threaded Python workers",
            "purpose": "Orchestrates the entire analysis workflow",
            "features": ["Parallel processing", "Event-driven updates", "Error handling"]
        },
        {
            "name": "Variant Annotator",
            "icon": "🔬",
            "tech": "RESTful API integrations",
            "purpose": "Queries external databases for variant information",
            "features": ["Parallel API calls", "Caching", "Fallback strategies"]
        },
        {
            "name": "Drug-Gene Matcher",
            "icon": "🧩",
            "tech": "Knowledge graph algorithms",
            "purpose": "Builds drug-gene interaction networks",
            "features": ["Diplotype calling", "Phenotype prediction", "Guideline matching"]
        },
        {
            "name": "Report Generator",
            "icon": "📄",
            "tech": "Templating engines (Jinja2, HTML/CSS)",
            "purpose": "Creates multi-format clinical reports",
            "features": ["PDF export", "JSON-LD", "RDF/Turtle", "HTML reports"]
        },
        {
            "name": "Data Storage",
            "icon": "💾",
            "tech": "File-based + Session state",
            "purpose": "Stores analysis results and patient data",
            "features": ["Output directory structure", "Session management", "Export options"]
        }
    ],
    "processing_flow": """
    **Real-time Processing Pipeline:**

    1. **User Input** → Patient demographics + Gene selection
    2. **Pipeline Initialization** → Create worker threads for each gene
    3. **Parallel Processing** → Each gene analyzed independently:
       - Simulate/load genetic variants
       - Query databases (parallel API calls)
       - Annotate with clinical significance
    4. **Integration Phase** → Combine results from all genes
    5. **Drug Analysis** → Build interaction networks
    6. **Report Generation** → Create multiple output formats
    7. **User Display** → Show results with interactive visualizations

    **Performance Optimizations:**
    - ⚡ Parallel API calls (5-10x faster than sequential)
    - 💾 Response caching (avoid redundant queries)
    - 🔄 Asynchronous processing (non-blocking UI)
    - 📊 Progressive rendering (show results as they arrive)
    """
}

# Fun facts and statistics
FUN_FACTS = [
    {
        "category": "Scale",
        "icon": "🌌",
        "fact": "Your genome has ~3.2 billion base pairs. If you could read 1 letter per second, it would take 100 years to read your entire genome!",
        "impact": "That's why we focus on the ~200 pharmacogenes (< 0.01% of your genome) that affect medications."
    },
    {
        "category": "Speed",
        "icon": "⚡",
        "fact": "Modern sequencers generate 1 terabyte of data per day - that's like streaming 4K video for 2 weeks straight!",
        "impact": "Advanced bioinformatics helps us find the important needles in this massive haystack."
    },
    {
        "category": "Accuracy",
        "icon": "🎯",
        "fact": "DNA replication has an error rate of ~1 in 10 billion. Our cells are better proofreaders than any human editor!",
        "impact": "But sequencing isn't perfect - that's why we require 30-100x coverage to be confident."
    },
    {
        "category": "Diversity",
        "icon": "🧬",
        "fact": "Humans are 99.9% genetically identical. That 0.1% difference accounts for ~4-5 million variants per person!",
        "impact": "Most variants are harmless, but ~100-200 can significantly affect medication response."
    },
    {
        "category": "Evolution",
        "icon": "🌍",
        "fact": "CYP2D6 (a key drug-metabolizing gene) has over 100 known variants. Some populations evolved different versions based on diet and environment!",
        "impact": "This is why personalized medicine matters - one size doesn't fit all."
    },
    {
        "category": "Clinical Impact",
        "icon": "⚕️",
        "fact": "Adverse drug reactions are the 4th leading cause of death in hospitals. 30-50% could be prevented with pharmacogenetic testing.",
        "impact": "One genetic test can guide medication decisions for life, improving safety and efficacy."
    }
]
