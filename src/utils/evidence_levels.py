"""
Evidence Level Interpretation
Provides human-readable explanations for evidence levels from various sources
"""
from typing import Dict, Optional

class EvidenceLevelInterpreter:
    """Interprets evidence levels from pharmacogenomics databases"""
    
    def __init__(self):
        """Initialize evidence level mappings"""
        
        # PharmGKB Evidence Levels
        # Source: https://www.pharmgkb.org/page/clinAnnLevels
        self.pharmgkb_levels = {
            "1A": {
                "level": "1A",
                "strength": "High",
                "description": "Annotation for a variant-drug combination where the preponderance of evidence shows an association exists and the evidence has been replicated in multiple cohorts.",
                "clinical_actionability": "Strong - Dosing guidelines available",
                "recommendation": "Genetic testing recommended before prescribing"
            },
            "1B": {
                "level": "1B", 
                "strength": "High",
                "description": "Annotation for a variant-drug combination where the preponderance of evidence shows an association exists but the evidence has not been replicated in multiple cohorts.",
                "clinical_actionability": "Strong - Single well-powered study",
                "recommendation": "Genetic testing may be considered"
            },
            "2A": {
                "level": "2A",
                "strength": "Moderate",
                "description": "Annotation for a variant-drug combination where the preponderance of evidence suggests an association exists but the evidence is not definitive.",
                "clinical_actionability": "Moderate - Some clinical evidence",
                "recommendation": "Consider genetic testing in specific populations"
            },
            "2B": {
                "level": "2B",
                "strength": "Moderate", 
                "description": "Annotation for a variant-drug combination where the evidence suggests an association exists but the evidence is not definitive and has not been replicated.",
                "clinical_actionability": "Moderate - Limited replication",
                "recommendation": "Research setting primarily"
            },
            "3": {
                "level": "3",
                "strength": "Low",
                "description": "Annotation for a variant-drug combination based on a single significant study or multiple studies with contradictory results.",
                "clinical_actionability": "Low - Conflicting or limited evidence",
                "recommendation": "Not recommended for routine clinical use"
            },
            "4": {
                "level": "4",
                "strength": "Very Low",
                "description": "Annotation for a variant-drug combination based on case reports, in vitro, molecular or functional assay data, or non-significant statistical evidence.",
                "clinical_actionability": "Very Low - Preliminary evidence only",
                "recommendation": "Research use only"
            }
        }
        
        # ClinVar Evidence Levels (Star Ratings)
        # Source: https://www.ncbi.nlm.nih.gov/clinvar/docs/review_status/
        self.clinvar_stars = {
            0: {
                "stars": 0,
                "review_status": "no assertion criteria provided",
                "description": "No assertion criteria provided or only case reports/in vitro studies",
                "clinical_actionability": "Not recommended for clinical use",
                "confidence": "Very Low"
            },
            1: {
                "stars": 1,
                "review_status": "criteria provided, single submitter",
                "description": "Criteria provided by a single submitter with no conflicts",
                "clinical_actionability": "Limited clinical utility",
                "confidence": "Low"
            },
            2: {
                "stars": 2,
                "review_status": "criteria provided, multiple submitters, no conflicts",
                "description": "Criteria provided by multiple submitters with no conflicts",
                "clinical_actionability": "Moderate clinical utility",
                "confidence": "Moderate"
            },
            3: {
                "stars": 3,
                "review_status": "reviewed by expert panel",
                "description": "Reviewed by expert panel (e.g., ClinGen, ACMG)",
                "clinical_actionability": "High clinical utility",
                "confidence": "High"
            },
            4: {
                "stars": 4,
                "review_status": "practice guideline",
                "description": "Assertion is part of practice guidelines (highest confidence)",
                "clinical_actionability": "Recommended for clinical use",
                "confidence": "Very High"
            }
        }
        
        # CPIC Evidence Levels
        # Source: https://cpicpgx.org/resources/term-id-tables/
        self.cpic_levels = {
            "A": {
                "level": "A",
                "strength": "Strong",
                "description": "Strong recommendation - genetic information should be used to guide therapy",
                "clinical_actionability": "Genetic testing recommended",
                "recommendation": "Prescribing information should be changed based on genotype"
            },
            "B": {
                "level": "B", 
                "strength": "Moderate",
                "description": "Moderate recommendation - genetic information could be used to guide therapy",
                "clinical_actionability": "Genetic testing may be beneficial",
                "recommendation": "Consider alternative therapy or dosing based on genotype"
            },
            "C": {
                "level": "C",
                "strength": "Optional",
                "description": "Optional recommendation - genetic information may provide additional insight",
                "clinical_actionability": "Limited clinical benefit",
                "recommendation": "Genotype may provide additional information"
            },
            "D": {
                "level": "D",
                "strength": "No Recommendation",
                "description": "No recommendation - insufficient evidence to recommend genetic testing",
                "clinical_actionability": "Not recommended",
                "recommendation": "Insufficient evidence for clinical action"
            }
        }
    
    def interpret_pharmgkb_level(self, level: str) -> Dict:
        """
        Interpret PharmGKB evidence level
        
        Args:
            level: PharmGKB level (e.g., "1A", "2A", "3", "4")
            
        Returns:
            Dictionary with interpretation details
        """
        level_str = str(level).upper()
        
        if level_str in self.pharmgkb_levels:
            interpretation = self.pharmgkb_levels[level_str].copy()
            interpretation["source"] = "PharmGKB"
            interpretation["url"] = "https://www.pharmgkb.org/page/clinAnnLevels"
            return interpretation
        else:
            return {
                "level": level_str,
                "source": "PharmGKB",
                "strength": "Unknown",
                "description": f"Unknown PharmGKB evidence level: {level_str}",
                "clinical_actionability": "Cannot determine",
                "recommendation": "Consult PharmGKB documentation"
            }
    
    def interpret_clinvar_stars(self, stars: int) -> Dict:
        """
        Interpret ClinVar star rating
        
        Args:
            stars: Number of stars (0-4)
            
        Returns:
            Dictionary with interpretation details
        """
        if stars in self.clinvar_stars:
            interpretation = self.clinvar_stars[stars].copy()
            interpretation["source"] = "ClinVar"
            interpretation["url"] = "https://www.ncbi.nlm.nih.gov/clinvar/docs/review_status/"
            return interpretation
        else:
            return {
                "stars": stars,
                "source": "ClinVar",
                "confidence": "Unknown",
                "description": f"Unknown ClinVar star rating: {stars}",
                "clinical_actionability": "Cannot determine"
            }
    
    def interpret_cpic_level(self, level: str) -> Dict:
        """
        Interpret CPIC recommendation level
        
        Args:
            level: CPIC level (A, B, C, D)
            
        Returns:
            Dictionary with interpretation details
        """
        level_str = str(level).upper()
        
        if level_str in self.cpic_levels:
            interpretation = self.cpic_levels[level_str].copy()
            interpretation["source"] = "CPIC"
            interpretation["url"] = "https://cpicpgx.org/resources/term-id-tables/"
            return interpretation
        else:
            return {
                "level": level_str,
                "source": "CPIC",
                "strength": "Unknown",
                "description": f"Unknown CPIC level: {level_str}",
                "clinical_actionability": "Cannot determine"
            }
    
    def get_overall_confidence(self, pharmgkb_level: str = None, clinvar_stars: int = None, cpic_level: str = None) -> Dict:
        """
        Calculate overall confidence based on multiple evidence sources
        
        Args:
            pharmgkb_level: PharmGKB evidence level
            clinvar_stars: ClinVar star rating
            cpic_level: CPIC recommendation level
            
        Returns:
            Dictionary with overall assessment
        """
        confidence_scores = []
        sources = []
        
        # Score PharmGKB level
        if pharmgkb_level:
            pgkb_scores = {"1A": 5, "1B": 4, "2A": 3, "2B": 2, "3": 1, "4": 0}
            score = pgkb_scores.get(str(pharmgkb_level).upper(), 0)
            confidence_scores.append(score)
            sources.append(f"PharmGKB {pharmgkb_level}")
        
        # Score ClinVar stars
        if clinvar_stars is not None:
            confidence_scores.append(clinvar_stars)
            sources.append(f"ClinVar {clinvar_stars} stars")
        
        # Score CPIC level
        if cpic_level:
            cpic_scores = {"A": 5, "B": 3, "C": 1, "D": 0}
            score = cpic_scores.get(str(cpic_level).upper(), 0)
            confidence_scores.append(score)
            sources.append(f"CPIC {cpic_level}")
        
        if not confidence_scores:
            return {
                "overall_confidence": "Unknown",
                "score": 0,
                "max_score": 5,
                "sources": [],
                "recommendation": "Insufficient evidence for assessment"
            }
        
        # Calculate average confidence
        avg_score = sum(confidence_scores) / len(confidence_scores)
        
        # Determine overall confidence level
        if avg_score >= 4:
            confidence = "Very High"
            recommendation = "Strong evidence - recommended for clinical use"
        elif avg_score >= 3:
            confidence = "High" 
            recommendation = "Good evidence - consider for clinical use"
        elif avg_score >= 2:
            confidence = "Moderate"
            recommendation = "Moderate evidence - may be useful in specific contexts"
        elif avg_score >= 1:
            confidence = "Low"
            recommendation = "Limited evidence - research setting primarily"
        else:
            confidence = "Very Low"
            recommendation = "Insufficient evidence - not recommended for clinical use"
        
        return {
            "overall_confidence": confidence,
            "score": round(avg_score, 1),
            "max_score": 5,
            "sources": sources,
            "recommendation": recommendation,
            "evidence_count": len(confidence_scores)
        }
    
    def format_evidence_summary(self, pharmgkb_level: str = None, clinvar_stars: int = None, cpic_level: str = None) -> str:
        """
        Create a human-readable evidence summary
        
        Args:
            pharmgkb_level: PharmGKB evidence level
            clinvar_stars: ClinVar star rating  
            cpic_level: CPIC recommendation level
            
        Returns:
            Formatted string summary
        """
        overall = self.get_overall_confidence(pharmgkb_level, clinvar_stars, cpic_level)
        
        summary_parts = []
        
        # Overall assessment
        summary_parts.append(f"Overall Confidence: {overall['overall_confidence']} ({overall['score']}/5)")
        summary_parts.append(f"Recommendation: {overall['recommendation']}")
        
        # Individual source details
        if pharmgkb_level:
            pgkb = self.interpret_pharmgkb_level(pharmgkb_level)
            summary_parts.append(f"PharmGKB Level {pgkb['level']}: {pgkb['description']}")
        
        if clinvar_stars is not None:
            cv = self.interpret_clinvar_stars(clinvar_stars)
            summary_parts.append(f"ClinVar {cv['stars']} stars: {cv['description']}")
        
        if cpic_level:
            cpic = self.interpret_cpic_level(cpic_level)
            summary_parts.append(f"CPIC Level {cpic['level']}: {cpic['description']}")
        
        return "\n".join(summary_parts)


def demo_evidence_levels():
    """Demonstrate evidence level interpretation"""
    interpreter = EvidenceLevelInterpreter()
    
    print("EVIDENCE LEVEL INTERPRETATION DEMO")
    print("=" * 50)
    
    # Example 1: High confidence variant
    print("\nExample 1: CYP2D6*4 + Codeine (High Confidence)")
    print("-" * 45)
    summary = interpreter.format_evidence_summary(
        pharmgkb_level="1A",
        clinvar_stars=3,
        cpic_level="A"
    )
    print(summary)
    
    # Example 2: Moderate confidence variant
    print("\nExample 2: CYP2D6 + Tramadol (Moderate Confidence)")
    print("-" * 48)
    summary = interpreter.format_evidence_summary(
        pharmgkb_level="2A",
        clinvar_stars=2
    )
    print(summary)
    
    # Example 3: Low confidence variant
    print("\nExample 3: Research Variant (Low Confidence)")
    print("-" * 40)
    summary = interpreter.format_evidence_summary(
        pharmgkb_level="4",
        clinvar_stars=1
    )
    print(summary)


if __name__ == "__main__":
    demo_evidence_levels()
