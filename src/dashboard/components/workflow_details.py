"""
Real Human Pharmacogenetics Workflow Details
Simplified, accurate steps for PGx analysis without unnecessary complexity
Enhanced with detailed explanations for educational purposes
"""
from __future__ import annotations

# Real PGx workflow steps based on standard clinical practice
DETAIL_SCRIPTS = {
    "lab": [
        {
            "id": "accession",
            "label": "Sample accessioned",
            "hint": "Patient linked, tube barcoded",
            "detail": "Sample receives unique identifier and enters laboratory tracking system"
        },
        {
            "id": "extract",
            "label": "DNA extraction",
            "hint": "Lysis → binding → wash → elution",
            "detail": "Cells are broken open to release DNA, which is purified and isolated"
        },
        {
            "id": "qc",
            "label": "Purity check",
            "hint": "A260/A280 ~1.8; fluorometric quant",
            "detail": "Quality control ensures DNA is pure (no protein/RNA contamination) and concentrated enough"
        },
        {
            "id": "fragment",
            "label": "Fragmentation",
            "hint": "Enzymatic or shear fragmentation",
            "detail": "DNA is cut into smaller pieces (~150-300bp) that sequencers can read"
        },
        {
            "id": "library",
            "label": "Library prep",
            "hint": "End-repair, A-tailing, adapter ligation",
            "detail": "Special adapters are attached to DNA fragments so the sequencer can read them"
        }
    ],
    "ngs": [
        {
            "id": "load",
            "label": "Loading flowcell",
            "hint": "Cluster generation ready",
            "detail": "DNA library is loaded onto the sequencing flowcell where millions of copies form clusters"
        },
        {
            "id": "basecall",
            "label": "Basecalling",
            "hint": "Signal → bases (Q-scores)",
            "detail": "Converting fluorescent light signals into DNA letters (A, T, C, G) with quality scores"
        },
        {
            "id": "trim",
            "label": "Read QC/trim",
            "hint": "Remove poor quality ends",
            "detail": "Removing low-quality bases from read ends to ensure accurate analysis"
        },
        {
            "id": "align",
            "label": "Alignment",
            "hint": "BWA-MEM to reference genome",
            "detail": "Mapping millions of DNA reads to their correct positions on the reference human genome"
        },
        {
            "id": "variants",
            "label": "Variant calling",
            "hint": "SNVs/indels in PGx genes",
            "detail": "Identifying genetic differences (variants) in pharmacogenes by comparing to reference"
        },
        {
            "id": "coverage",
            "label": "Coverage QC",
            "hint": "Depth/MAPQ over target genes",
            "detail": "Ensuring every gene position was read enough times (30-100x) for confident variant calls"
        }
    ],
    "anno": [
        {
            "id": "coords",
            "label": "Coordinate linking",
            "hint": "Standard genomic positions",
            "detail": "Converting variant positions to standardized genomic coordinates (chr:position)"
        },
        {
            "id": "dbsnp",
            "label": "dbSNP rsIDs",
            "hint": "Attach reference SNP IDs",
            "detail": "Looking up unique identifiers (rs numbers) for known variants from the dbSNP database"
        },
        {
            "id": "clinvar",
            "label": "ClinVar significance",
            "hint": "Clinical impact assessment",
            "detail": "Checking clinical significance: Benign, Uncertain, Likely pathogenic, or Pathogenic"
        },
        {
            "id": "pharmgkb",
            "label": "PharmGKB evidence",
            "hint": "Drug-gene knowledge base",
            "detail": "Querying PharmGKB for drug-gene relationships and evidence levels"
        },
        {
            "id": "literature",
            "label": "Literature search",
            "hint": "Europe PMC citations",
            "detail": "Searching scientific literature for recent research publications about each variant"
        }
    ],
    "drug": [
        {
            "id": "network",
            "label": "Drug-gene network",
            "hint": "Connect meds to variants",
            "detail": "Building network graph connecting your genetic variants to affected medications"
        },
        {
            "id": "guidelines",
            "label": "Clinical guidelines",
            "hint": "CPIC/DPWG recommendations",
            "detail": "Applying evidence-based prescribing guidelines from expert consortiums (CPIC, DPWG)"
        },
        {
            "id": "severity",
            "label": "Risk assessment",
            "hint": "Info/Warning/Critical levels",
            "detail": "Categorizing drug-gene interactions by severity: Low, Moderate, High, or Critical"
        },
        {
            "id": "recommend",
            "label": "Recommendations",
            "hint": "Dose adjust/alternatives",
            "detail": "Generating actionable recommendations: dose adjustments, monitoring, or alternative drugs"
        }
    ],
    "report": [
        {
            "id": "compile",
            "label": "Compiling results",
            "hint": "PGx summary per drug/gene",
            "detail": "Aggregating all analysis results into comprehensive pharmacogenomic profile"
        },
        {
            "id": "formats",
            "label": "Export formats",
            "hint": "JSON-LD, HTML, TTL, Summary",
            "detail": "Creating multiple report formats: PDF/HTML for clinicians, JSON-LD for health systems"
        }
    ]
}

# Visual enhancements for each stage
VISUAL_FLAGS = {
    "lab": {
        "show_tube_to_dna": True,
        "show_qc_badge": True
    },
    "ngs": {
        "show_per_gene_chips": True,
        "show_variant_counter": True,
        "show_coverage_meters": True
    },
    "anno": {
        "show_db_connections": True,
        "show_significance_badges": True,
        "show_literature_counter": True
    },
    "drug": {
        "show_network_graph": True,
        "show_severity_colors": True,
        "animate_recommendations": True
    },
    "report": {
        "show_format_badges": True
    }
}

# Network visualization data for drug interactions
NETWORK_TEMPLATES = {
    "medications": [
        {"name": "Warfarin", "color": "#dc2626", "type": "anticoagulant"},
        {"name": "Clopidogrel", "color": "#ea580c", "type": "antiplatelet"},
        {"name": "Codeine", "color": "#9333ea", "type": "analgesic"},
        {"name": "Simvastatin", "color": "#0891b2", "type": "statin"}
    ],
    "genes": [
        {"name": "CYP2D6", "variants": ["*4", "*10"], "color": "#2563eb"},
        {"name": "CYP2C19", "variants": ["*2", "*17"], "color": "#16a34a"},
        {"name": "CYP3A4", "variants": ["*22"], "color": "#7c3aed"},
        {"name": "VKORC1", "variants": ["-1639G>A"], "color": "#dc2626"}
    ]
}
