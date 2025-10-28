"""
Real Human Pharmacogenetics Workflow Details
Simplified, accurate steps for PGx analysis without unnecessary complexity
"""
from __future__ import annotations

# Real PGx workflow steps based on standard clinical practice
DETAIL_SCRIPTS = {
    "lab": [
        {"id": "accession", "label": "Sample accessioned", "hint": "Patient linked, tube barcoded"},
        {"id": "extract", "label": "DNA extraction", "hint": "Lysis → binding → wash → elution"},
        {"id": "qc", "label": "Purity check", "hint": "A260/A280 ~1.8; fluorometric quant"},
        {"id": "fragment", "label": "Fragmentation", "hint": "Enzymatic or shear fragmentation"},
        {"id": "library", "label": "Library prep", "hint": "End-repair, A-tailing, adapter ligation"}
    ],
    "ngs": [
        {"id": "load", "label": "Loading flowcell", "hint": "Cluster generation ready"},
        {"id": "basecall", "label": "Basecalling", "hint": "Signal → bases (Q-scores)"},
        {"id": "trim", "label": "Read QC/trim", "hint": "Remove poor quality ends"},
        {"id": "align", "label": "Alignment", "hint": "BWA-MEM to reference genome"},
        {"id": "variants", "label": "Variant calling", "hint": "SNVs/indels in PGx genes"},
        {"id": "coverage", "label": "Coverage QC", "hint": "Depth/MAPQ over target genes"}
    ],
    "anno": [
        {"id": "coords", "label": "Coordinate linking", "hint": "Standard genomic positions"},
        {"id": "dbsnp", "label": "dbSNP rsIDs", "hint": "Attach reference SNP IDs"},
        {"id": "clinvar", "label": "ClinVar significance", "hint": "Clinical impact assessment"},
        {"id": "pharmgkb", "label": "PharmGKB evidence", "hint": "Drug-gene knowledge base"},
        {"id": "literature", "label": "Literature search", "hint": "Europe PMC citations"}
    ],
    "drug": [
        {"id": "network", "label": "Drug-gene network", "hint": "Connect meds to variants"},
        {"id": "guidelines", "label": "Clinical guidelines", "hint": "CPIC/DPWG recommendations"},
        {"id": "severity", "label": "Risk assessment", "hint": "Info/Warning/Critical levels"},
        {"id": "recommend", "label": "Recommendations", "hint": "Dose adjust/alternatives"}
    ],
    "report": [
        {"id": "compile", "label": "Compiling results", "hint": "PGx summary per drug/gene"},
        {"id": "formats", "label": "Export formats", "hint": "JSON-LD, HTML, TTL, Summary"}
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
