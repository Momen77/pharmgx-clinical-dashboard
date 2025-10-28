"""
Enhanced animation details configuration for each stage.
This module provides textual micro-step scripts and flags
for rendering richer visuals (per-gene progress, network edges, etc.).
"""
from __future__ import annotations

DETAIL_SCRIPTS = {
    "lab": [
        {"id": "receive_sample", "label": "Sample accessioned", "hint": "Assigning MRN and accession ID"},
        {"id": "isolate_dna", "label": "DNA extraction", "hint": "Lysis → binding → wash → elution"},
        {"id": "qc_ratio", "label": "Purity check (A260/A280)", "hint": "Target ~1.8 (DNA)"},
        {"id": "library_prep", "label": "Library prep", "hint": "End-repair, A-tailing, ligation"},
        {"id": "barcoding", "label": "Barcode attachment", "hint": "Unique dual indexes"}
    ],
    "ngs": [
        {"id": "load_flowcell", "label": "Loading flowcell", "hint": "Cluster generation prepped"},
        {"id": "basecalling", "label": "Basecalling", "hint": "Signal → base probabilities"},
        {"id": "per_gene_queue", "label": "Per-gene alignment queue", "hint": "CYP2D6, CYP2C19, CYP3A4..."},
        {"id": "align_reads", "label": "Aligning reads", "hint": "BWA-MEM/Minimap2 to reference"},
        {"id": "call_variants", "label": "Variant calling", "hint": "SNVs/indels/haplotypes"},
        {"id": "qc_metrics", "label": "QC metrics", "hint": "Depth, MAPQ, coverage %"}
    ],
    "anno": [
        {"id": "normalize_variants", "label": "HGVS normalization", "hint": "Consistent variant notation"},
        {"id": "db_links", "label": "Database linking", "hint": "ClinVar, dbSNP, PharmGKB"},
        {"id": "significance", "label": "Clinical significance", "hint": "Pathogenic, drug response, VUS"},
        {"id": "evidence", "label": "Evidence curation", "hint": "Guideline levels, citations"},
        {"id": "literature", "label": "Literature mining", "hint": "Europe PMC variant+drug queries"}
    ],
    "drug": [
        {"id": "build_graph", "label": "Building interaction graph", "hint": "Medications ↔ genes/variants"},
        {"id": "apply_rules", "label": "Guideline rules", "hint": "CPIC/DPWG recommendations"},
        {"id": "severity_levels", "label": "Severity badges", "hint": "Info/Warning/Critical"},
        {"id": "alt_suggestions", "label": "Alternatives & dosing", "hint": "Dose adjust / switch"}
    ],
    "report": [
        {"id": "compile", "label": "Compiling report", "hint": "Summary + details"},
        {"id": "export_formats", "label": "Export formats", "hint": "JSON-LD, HTML, TTL, Summary"}
    ]
}

# Visual flags for the renderer
VISUAL_FLAGS = {
    "ngs": {
        "show_per_gene_activity": True,      # highlight gene chip when active
        "show_variant_counter": True,        # increment counter during calls
        "show_qc_meters": True               # small bars for depth/coverage
    },
    "anno": {
        "show_db_edges": True,               # draw variant → DB edges
        "show_significance_badges": True,    # display badges on nodes
        "show_literature_counter": True
    },
    "drug": {
        "show_network_graph": True,          # render medication-variant network
        "show_severity_colors": True,        # color edges/nodes by severity
        "animate_recommendations": True
    }
}
