"""
Workflow Stages (stateless renderers)
Each stage renderer returns HTML segments and accepts props.
"""
from __future__ import annotations

from typing import Dict, Any


def render_lab_prep(props: Dict[str, Any]) -> str:
    tip = "Extracting genomic DNA and checking purity (A260/A280)."
    return f"""
    <div class='wf-tip'>
      <div class='tip'><b>Lab Prep</b><br/>{tip}</div>
    </div>
    """


def render_sequencing(props: Dict[str, Any]) -> str:
    variants = int(props.get('variants', 0))
    return f"""
    <div class='wf-tip'>
      <div class='tip'><b>Sequencing</b><br/>Basecalling and variant discovery in selected genes.</div>
      <div class='wf-pill'>Variants: <span class='wf-counter'>{variants}</span></div>
    </div>
    """


def render_annotation(props: Dict[str, Any]) -> str:
    pubs = int(props.get('pubs', 0))
    return f"""
    <div class='wf-tip'>
      <div class='tip'><b>Annotation</b><br/>Linking variants with ClinVar/PharmGKB and literature evidence.</div>
      <div class='wf-pill'>Literature: <span class='wf-counter'>{pubs}</span></div>
    </div>
    """


def render_drug_interactions(props: Dict[str, Any]) -> str:
    drugs = int(props.get('drugs', 0))
    return f"""
    <div class='wf-tip'>
      <div class='tip'><b>Drug Interactions</b><br/>Checking patient medications against gene variants.</div>
      <div class='wf-pill'>Drugs: <span class='wf-counter'>{drugs}</span></div>
    </div>
    """


def render_report(props: Dict[str, Any]) -> str:
    return f"""
    <div class='wf-tip'>
      <div class='tip'><b>Report</b><br/>Compiling outputs: JSON-LD, HTML, TTL, Summary.</div>
    </div>
    """
