"""
HTML Reporter
Generates HTML summary reports
"""
import json
from pathlib import Path
from datetime import datetime


class HTMLReporter:
    """Generates HTML summary reports"""
    
    def __init__(self):
        """Initialize HTML reporter"""
        self.output_dir = Path("output/reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_report(self, enriched_data: dict, gene_symbol: str) -> str:
        """Generate HTML report"""
        variants = enriched_data.get("variants", [])
        
        # Get metabolizer phenotype
        phenotype_info = enriched_data.get("metabolizer_phenotype", {})
        phenotype = phenotype_info.get("phenotype", "Not determined")
        diplotype = phenotype_info.get("diplotype", "Unknown/Unknown")
        functionality = phenotype_info.get("functionality", "Unknown/Unknown")
        
        # Count statistics
        total_variants = len(variants)
        drug_response_count = sum(1 for v in variants if self._has_drug_response(v))
        pathogenic_count = sum(1 for v in variants if self._is_pathogenic(v))
        
        # Collect all drugs
        all_drugs = {}
        for variant in variants:
            if "pharmgkb" in variant and "drugs" in variant["pharmgkb"]:
                for drug in variant["pharmgkb"]["drugs"]:
                    drug_name = drug["name"]
                    if drug_name not in all_drugs:
                        all_drugs[drug_name] = {
                            "name": drug_name,
                            "variants": [],
                            "recommendation": drug.get("recommendation", ""),
                            "evidence_level": drug.get("evidence_level", ""),
                            "evidence_strength": drug.get("evidence_interpretation", {}).get("strength", "Unknown"),
                            "evidence_description": drug.get("evidence_interpretation", {}).get("description", "")
                        }
                    rsid = self._get_rsid(variant)
                    if rsid:
                        all_drugs[drug_name]["variants"].append(f"rs{rsid}")
        
        # Determine phenotype color
        phenotype_color = "#7f8c8d"  # Default gray
        if "Normal" in phenotype:
            phenotype_color = "#27ae60"  # Green
        elif "Poor" in phenotype:
            phenotype_color = "#e74c3c"  # Red
        elif "Intermediate" in phenotype:
            phenotype_color = "#f39c12"  # Orange
        elif "Ultrarapid" in phenotype:
            phenotype_color = "#3498db"  # Blue
        
        # Build HTML
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>PGx-KG Report: {gene_symbol}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .phenotype-box {{ background: #ecf0f1; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 5px solid {phenotype_color}; }}
        .phenotype-title {{ font-size: 18px; font-weight: bold; color: #2c3e50; margin-bottom: 10px; }}
        .phenotype-value {{ font-size: 24px; font-weight: bold; color: {phenotype_color}; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .stat-card {{ background: #ecf0f1; padding: 20px; border-radius: 5px; text-align: center; }}
        .stat-number {{ font-size: 36px; font-weight: bold; color: #3498db; }}
        .stat-label {{ color: #7f8c8d; margin-top: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th {{ background: #3498db; color: white; padding: 12px; text-align: left; }}
        td {{ padding: 12px; border-bottom: 1px solid #ddd; }}
        tr:hover {{ background: #f8f9fa; }}
        .drug-response {{ color: #27ae60; font-weight: bold; }}
        .pathogenic {{ color: #e74c3c; font-weight: bold; }}
        .vus {{ color: #f39c12; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #7f8c8d; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🧬 Pharmacogenomics Knowledge Graph Report</h1>
        <h2>Gene: {gene_symbol}</h2>
        <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <div class="phenotype-box">
            <div class="phenotype-title">Metabolizer Phenotype</div>
            <div class="phenotype-value">{phenotype}</div>
            <p style="margin-top: 10px; color: #7f8c8d;">
                <strong>Diplotype:</strong> {diplotype} | 
                <strong>Functionality:</strong> {functionality}
            </p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{total_variants}</div>
                <div class="stat-label">Total Variants</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{drug_response_count}</div>
                <div class="stat-label">Drug Response</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{pathogenic_count}</div>
                <div class="stat-label">Pathogenic</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{len(all_drugs)}</div>
                <div class="stat-label">Affected Drugs</div>
            </div>
        </div>
        
        <h2>📊 Variant Summary</h2>
        <table>
            <tr>
                <th>Variant</th>
                <th>Clinical Significance</th>
                <th>Protein Change</th>
                <th>ClinVar Rating</th>
                <th>Affected Drugs</th>
            </tr>
"""
        
        # Add variant rows
        for variant in variants[:20]:  # Limit to 20
            rsid = self._get_rsid(variant)
            if not rsid:
                continue
            
            clin_sig = self._get_clinical_significance(variant)
            protein_change = self._get_protein_change(variant)
            star_rating = variant.get("clinvar", {}).get("star_rating", 0)
            star_display = "⭐" * star_rating if star_rating else "N/A"
            
            # Get ClinVar evidence interpretation
            clinvar_evidence = variant.get("clinvar", {}).get("evidence_interpretation", {})
            star_tooltip = ""
            if clinvar_evidence:
                star_tooltip = f"title=\"{clinvar_evidence.get('description', '')} - {clinvar_evidence.get('clinical_actionability', '')}\""
            
            # Get drug names
            drug_names = []
            if "pharmgkb" in variant and "drugs" in variant["pharmgkb"]:
                drug_names = [d["name"] for d in variant["pharmgkb"]["drugs"][:3]]
            drugs_str = ", ".join(drug_names) if drug_names else "None"
            
            # Apply CSS class based on significance
            css_class = ""
            if "drug" in clin_sig.lower():
                css_class = "drug-response"
            elif "pathogenic" in clin_sig.lower():
                css_class = "pathogenic"
            elif "uncertain" in clin_sig.lower():
                css_class = "vus"
            
            html += f"""            <tr>
                <td>rs{rsid}</td>
                <td class="{css_class}">{clin_sig}</td>
                <td>{protein_change or "N/A"}</td>
                <td><span {star_tooltip}>{star_display}</span></td>
                <td>{drugs_str}</td>
            </tr>
"""
        
        html += """        </table>
        
        <h2>Drug Interactions</h2>
        <table>
            <tr>
                <th>Drug</th>
                <th>Associated Variants</th>
                <th>Evidence Level</th>
                <th>Recommendation</th>
            </tr>
"""
        
        # Add drug rows
        for drug_name, drug_info in list(all_drugs.items())[:15]:  # Limit to 15
            variants_str = ", ".join(drug_info["variants"][:5])
            recommendation = drug_info["recommendation"][:100] + "..." if len(drug_info["recommendation"]) > 100 else drug_info["recommendation"]
            
            # Get evidence level info
            evidence_level = drug_info.get("evidence_level", "")
            evidence_strength = drug_info.get("evidence_strength", "Unknown")
            evidence_color = self._get_evidence_color(evidence_strength)
            evidence_description = drug_info.get("evidence_description", "")
            evidence_recommendation = ""
            
            # Get full evidence interpretation if available from variant data
            for variant in variants:
                if "pharmgkb" in variant and "drugs" in variant["pharmgkb"]:
                    for drug in variant["pharmgkb"]["drugs"]:
                        if drug.get("name") == drug_name and drug.get("evidence_interpretation"):
                            ev_int = drug["evidence_interpretation"]
                            evidence_recommendation = ev_int.get("recommendation", "")
                            if not evidence_description:
                                evidence_description = ev_int.get("description", "")
                            break
            
            # Build tooltip with full evidence interpretation
            tooltip_parts = []
            if evidence_description:
                tooltip_parts.append(evidence_description)
            if evidence_recommendation:
                tooltip_parts.append(f"Recommendation: {evidence_recommendation}")
            tooltip = " | ".join(tooltip_parts) if tooltip_parts else ""
            
            html += f"""            <tr>
                <td><strong>{drug_name}</strong></td>
                <td>{variants_str}</td>
                <td><span style="color: {evidence_color}; font-weight: bold;" title="{tooltip}">{evidence_level} ({evidence_strength})</span></td>
                <td>{recommendation or "See clinical guidelines"}</td>
            </tr>
"""
        
        html += """        </table>
        
        <div class="footer">
            <p>Generated by PGx-KG: Pharmacogenomics Knowledge Graph Builder</p>
            <p>Data sources: UniProt, EMBL-EBI, ClinVar, PharmGKB, OpenFDA, Europe PMC</p>
        </div>
    </div>
</body>
</html>
"""
        
        # Save
        output_file = self.output_dir / f"{gene_symbol}_report.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"   HTML report saved: {output_file}")
        return str(output_file)
    
    def _get_rsid(self, variant: dict) -> str:
        """Extract rsID from variant"""
        for xref in variant.get("xrefs", []):
            if xref.get("name") == "dbSNP":
                return xref.get("id", "").replace("rs", "")
        return None
    
    def _get_clinical_significance(self, variant: dict) -> str:
        """Get clinical significance"""
        clin_sigs = [sig["type"] for sig in variant.get("clinicalSignificances", [])]
        return clin_sigs[0] if clin_sigs else "Unknown"
    
    def _get_protein_change(self, variant: dict) -> str:
        """Extract protein change from variant"""
        for loc in variant.get("locations", []):
            if "loc" in loc and loc["loc"].startswith("p."):
                return loc["loc"]
        return None
    
    def _has_drug_response(self, variant: dict) -> bool:
        """Check if variant affects drug response"""
        for sig in variant.get("clinicalSignificances", []):
            if "drug" in sig["type"].lower() or "response" in sig["type"].lower():
                return True
        return False
    
    def _get_evidence_color(self, strength: str) -> str:
        """Get color for evidence strength"""
        strength_lower = strength.lower()
        if strength_lower in ["very high", "high"]:
            return "#27ae60"  # Green
        elif strength_lower == "moderate":
            return "#f39c12"  # Orange
        elif strength_lower == "low":
            return "#e67e22"  # Dark orange
        elif strength_lower == "very low":
            return "#e74c3c"  # Red
        else:
            return "#7f8c8d"  # Gray
    
    def _is_pathogenic(self, variant: dict) -> bool:
        """Check if variant is pathogenic"""
        for sig in variant.get("clinicalSignificances", []):
            if "pathogenic" in sig["type"].lower():
                return True
        return False
    
    def run_pipeline(self, gene_symbol: str, phase3_file: str = None) -> str:
        """Execute HTML report generation"""
        print(f"Generating HTML report...")
        
        # Load data
        if not phase3_file:
            phase3_file = f"data/phase3/{gene_symbol}_enriched.json"
        
        with open(phase3_file, 'r', encoding='utf-8') as f:
            enriched_data = json.load(f)
        
        return self.generate_report(enriched_data, gene_symbol)

