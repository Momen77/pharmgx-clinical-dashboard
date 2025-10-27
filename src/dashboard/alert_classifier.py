"""
CPIC-based alert classification system
Classifies drug-gene interactions into actionable categories
"""
from typing import Dict, List, Optional

class AlertClassifier:
    """Classifies pharmacogenetic alerts based on CPIC guidelines"""
    
    # CPIC evidence levels mapping
    CPIC_LEVELS = {
        "1A": "actionable",  # Strong clinical evidence, high actionability
        "1B": "actionable",  # Strong clinical evidence, moderate actionability
        "2A": "actionable",  # Moderate clinical evidence
        "2B": "informative", # Moderate clinical evidence, lower actionability
        "3": "informative",  # Weaker clinical evidence
        "4": "no_action"     # Minimal evidence
    }
    
    # Critical drug-gene pairs (always actionable)
    CRITICAL_PAIRS = {
        ("clopidogrel", "CYP2C19"): "actionable",
        ("warfarin", "VKORC1"): "actionable",
        ("warfarin", "CYP2C9"): "actionable",
        ("codeine", "CYP2D6"): "actionable",
        ("tamoxifen", "CYP2D6"): "actionable",
        ("abacavir", "HLA-B"): "actionable",
        ("carbamazepine", "HLA-A"): "actionable",
        ("allopurinol", "HLA-B"): "actionable",
        ("simvastatin", "SLCO1B1"): "informative",
        ("5-fluorouracil", "DPYD"): "actionable",
        ("azathioprine", "TPMT"): "actionable",
        ("mercaptopurine", "TPMT"): "actionable",
        ("irinotecan", "UGT1A1"): "informative"
    }
    
    def classify(self, drug_name: str, gene: str, evidence_level: Optional[str] = None, 
                 recommendation: Optional[str] = None) -> Dict[str, str]:
        """
        Classify drug-gene interaction alert level
        
        Args:
            drug_name: Name of the drug
            gene: Gene symbol
            evidence_level: CPIC evidence level (1A, 1B, 2A, 2B, 3, 4)
            recommendation: Clinical recommendation text
        
        Returns:
            Dictionary with alert classification
        """
        drug_lower = drug_name.lower()
        gene_upper = gene.upper()
        
        # Check critical pairs first
        pair_key = (drug_lower, gene_upper)
        if pair_key in self.CRITICAL_PAIRS:
            alert_type = self.CRITICAL_PAIRS[pair_key]
        elif evidence_level:
            # Use CPIC level mapping
            alert_type = self.CPIC_LEVELS.get(evidence_level, "informative")
        else:
            # Default to informative if no evidence level
            alert_type = "informative"
        
        # Determine severity based on keywords in recommendation
        if recommendation:
            rec_lower = recommendation.lower()
            if any(word in rec_lower for word in ["avoid", "contraindicated", "not recommended", "do not use"]):
                alert_type = "actionable"
            elif any(word in rec_lower for word in ["monitor", "consider", "caution"]):
                if alert_type == "no_action":
                    alert_type = "informative"
        
        return {
            "alert_type": alert_type,
            "severity": self._get_severity(alert_type),
            "color": self._get_color(alert_type),
            "icon": self._get_icon(alert_type)
        }
    
    def _get_severity(self, alert_type: str) -> str:
        """Get severity level"""
        severity_map = {
            "actionable": "Critical",
            "informative": "Warning",
            "no_action": "Info"
        }
        return severity_map.get(alert_type, "Info")
    
    def _get_color(self, alert_type: str) -> str:
        """Get color code for alert type"""
        color_map = {
            "actionable": "#DC3545",  # Red
            "informative": "#FFD200",  # Yellow (UGent Yellow)
            "no_action": "#28A745"     # Green
        }
        return color_map.get(alert_type, "#6C757D")
    
    def _get_icon(self, alert_type: str) -> str:
        """Get icon for alert type"""
        icon_map = {
            "actionable": "🚨",
            "informative": "⚠️",
            "no_action": "✅"
        }
        return icon_map.get(alert_type, "ℹ️")
    
    def classify_from_variant_data(self, variant_data: Dict) -> List[Dict]:
        """
        Classify alerts from variant data structure
        
        Args:
            variant_data: Variant data with drugs and recommendations
        
        Returns:
            List of classified alerts
        """
        alerts = []
        
        if "drugs" in variant_data:
            for drug in variant_data["drugs"]:
                drug_name = drug.get("name", "")
                gene = variant_data.get("gene", "")
                evidence_level = drug.get("evidence_level", "")
                recommendation = drug.get("recommendation", "")
                
                classification = self.classify(
                    drug_name=drug_name,
                    gene=gene,
                    evidence_level=evidence_level,
                    recommendation=recommendation
                )
                
                alerts.append({
                    "drug": drug_name,
                    "gene": gene,
                    "recommendation": recommendation,
                    "evidence_level": evidence_level,
                    **classification
                })
        
        return alerts

