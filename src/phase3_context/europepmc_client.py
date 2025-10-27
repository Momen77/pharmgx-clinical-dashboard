"""
Europe PMC Client
Queries Europe PMC for literature evidence
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from typing import Dict, List, Optional
from utils.api_client import APIClient


class EuropePMCClient:
    """Client for querying Europe PMC API"""
    
    def __init__(self):
        """Initialize Europe PMC client"""
        self.base_url = "https://www.ebi.ac.uk/europepmc/webservices/rest"
        self.client = APIClient(self.base_url, rate_limit=10)
    
    def search_literature(self, gene: str, drug: str = None, disease: str = None,
                         max_results: int = 5) -> List[Dict]:
        """
        Search for literature linking gene, drug, and/or disease
        
        Args:
            gene: Gene symbol
            drug: Drug name (optional)
            disease: Disease name (optional)
            max_results: Maximum results to return
            
        Returns:
            List of publication dictionaries
        """
        # Build query
        query_parts = [gene]
        
        if drug:
            query_parts.append(drug)
        
        if disease:
            query_parts.append(disease)
        
        # Add pharmacogenomics context (without quotes around OR clause)
        query_parts.append("(pharmacogenomics OR pharmacogenetics OR drug response)")
        
        # Build query - don't quote parts that contain OR/AND operators
        formatted_parts = []
        for part in query_parts:
            if " OR " in part or " AND " in part or part.startswith("("):
                # Don't quote boolean operators
                formatted_parts.append(part)
            elif " " in part:
                # Quote multi-word terms
                formatted_parts.append(f'"{part}"')
            else:
                # Single words don't need quotes
                formatted_parts.append(part)
        
        query = " AND ".join(formatted_parts)
        
        endpoint = "search"
        params = {
            "query": query,
            "resultType": "core",
            "format": "json",
            "pageSize": max_results,
            "sort": "CITED desc"  # Sort by most cited
        }
        
        data = self.client.get(endpoint, params=params)
        
        if not data or "resultList" not in data:
            return []
        
        results = data["resultList"].get("result", [])
        
        # Extract key information
        publications = []
        for result in results:
            pub = {
                "pmid": result.get("pmid"),
                "pmcid": result.get("pmcid"),
                "doi": result.get("doi"),
                "title": result.get("title"),
                "authors": self._extract_authors(result.get("authorString", "")),
                "journal": result.get("journalTitle"),
                "pub_year": result.get("pubYear"),
                "abstract": result.get("abstractText", "")[:500],  # First 500 chars
                "citation_count": result.get("citedByCount", 0),
                "url": f"https://europepmc.org/article/MED/{result.get('pmid')}" if result.get("pmid") else None
            }
            publications.append(pub)
        
        return publications
    
    def _extract_authors(self, author_string: str) -> List[str]:
        """Parse author string into list"""
        if not author_string:
            return []
        return [a.strip() for a in author_string.split(",")[:3]]  # First 3 authors
    
    def enrich_with_literature(self, gene: str, variants: List[Dict]) -> List[Dict]:
        """
        Enrich variants with literature evidence from UniProt only
        Extract publications from UniProt variant data and fetch full text details
        
        Args:
            gene: Gene symbol
            variants: List of variants
            
        Returns:
            Enriched variants with UniProt publications and full text URLs
        """
        print(f"   Extracting literature from UniProt variant annotations...")
        
        # Process each variant to extract UniProt PubMed evidence
        for variant in variants:
            # Extract UniProt PubMed evidence with full text details
            uniprot_publications = self._extract_uniprot_pubmed_evidence(variant)
            
            # Organize literature by variant
            variant_literature = {
                "gene_publications": uniprot_publications,  # All UniProt publications
                "variant_specific_publications": uniprot_publications,  # Same publications
                "drug_publications": {}  # No drug-specific searches
            }
            
            variant["literature"] = variant_literature
        
        return variants
    
    def _extract_variant_identifiers(self, variant: Dict) -> List[str]:
        """Extract searchable variant identifiers from variant data"""
        identifiers = []
        
        # Extract rsID (most useful for literature search)
        for xref in variant.get("xrefs", []):
            if xref.get("name") == "dbSNP" and xref.get("id"):
                identifiers.append(xref["id"])
        
        # Extract protein change (useful for functional studies)
        for location in variant.get("locations", []):
            if location.get("loc") and location["loc"].startswith("p."):
                identifiers.append(location["loc"])
        
        # Extract genomic location (for molecular studies)
        genomic_locations = variant.get("genomicLocation", [])
        if genomic_locations:
            # Simplify genomic location for search
            genomic = genomic_locations[0]
            if ":" in genomic and ">" in genomic:
                # Extract just the change part: NC_000022.11:g.42130772A>G -> A>G or 42130772A>G
                parts = genomic.split(":")
                if len(parts) > 1:
                    change_part = parts[1]
                    if "." in change_part:
                        identifiers.append(change_part.split(".")[-1])  # g.42130772A>G -> 42130772A>G
        
        return identifiers[:3]  # Limit to top 3 identifiers
    
    def search_variant_literature(self, gene: str, variant_ids: List[str], max_results: int = 3) -> List[Dict]:
        """Search for literature specific to a variant"""
        all_pubs = []
        
        for variant_id in variant_ids[:2]:  # Try top 2 variant IDs
            # Build variant-specific query
            query_parts = [gene, variant_id]
            
            # Add context terms for better results
            if variant_id.startswith("rs"):
                # For rsIDs, add polymorphism context
                query_parts.append("(polymorphism OR SNP OR variant OR allele)")
            elif variant_id.startswith("p."):
                # For protein changes, add functional context
                query_parts.append("(mutation OR substitution OR function OR activity)")
            else:
                # For other identifiers, add general variant context
                query_parts.append("(variant OR mutation OR polymorphism)")
            
            # Format query
            formatted_parts = []
            for part in query_parts:
                if " OR " in part or " AND " in part or part.startswith("("):
                    formatted_parts.append(part)
                elif " " in part:
                    formatted_parts.append(f'"{part}"')
                else:
                    formatted_parts.append(part)
            
            query = " AND ".join(formatted_parts)
            
            # Search
            endpoint = "search"
            params = {
                "query": query,
                "resultType": "core",
                "format": "json",
                "pageSize": max_results,
                "sort": "CITED desc"
            }
            
            data = self.client.get(endpoint, params=params)
            
            if data and "resultList" in data:
                results = data["resultList"].get("result", [])
                for result in results:
                    pub = {
                        "pmid": result.get("pmid"),
                        "pmcid": result.get("pmcid"),
                        "doi": result.get("doi"),
                        "title": result.get("title"),
                        "authors": self._extract_authors(result.get("authorString", "")),
                        "journal": result.get("journalTitle"),
                        "pub_year": result.get("pubYear"),
                        "abstract": result.get("abstractText", "")[:500] + "..." if result.get("abstractText") and len(result.get("abstractText", "")) > 500 else result.get("abstractText"),
                        "citation_count": result.get("citedByCount", 0),
                        "search_variant": variant_id
                    }
                    all_pubs.append(pub)
            
            if len(all_pubs) >= max_results:
                break
        
        # Remove duplicates and return top results
        seen_pmids = set()
        unique_pubs = []
        for pub in all_pubs:
            pmid = pub.get("pmid")
            if pmid and pmid not in seen_pmids:
                seen_pmids.add(pmid)
                unique_pubs.append(pub)
        
        return unique_pubs[:max_results]
    
    def search_variant_drug_literature(self, gene: str, variant_id: str, drug: str, max_results: int = 2) -> List[Dict]:
        """Search for literature linking a specific variant to a drug"""
        # Build specific variant-drug query
        query_parts = [gene, variant_id, drug]
        
        # Add pharmacogenomics context
        if variant_id.startswith("rs"):
            query_parts.append("(pharmacogenomics OR drug response OR metabolism OR efficacy OR toxicity)")
        else:
            query_parts.append("(pharmacokinetics OR drug metabolism OR clinical outcome)")
        
        # Format query
        formatted_parts = []
        for part in query_parts:
            if " OR " in part or " AND " in part or part.startswith("("):
                formatted_parts.append(part)
            elif " " in part:
                formatted_parts.append(f'"{part}"')
            else:
                formatted_parts.append(part)
        
        query = " AND ".join(formatted_parts)
        
        # Search
        endpoint = "search"
        params = {
            "query": query,
            "resultType": "core",
            "format": "json",
            "pageSize": max_results,
            "sort": "CITED desc"
        }
        
        data = self.client.get(endpoint, params=params)
        
        if not data or "resultList" not in data:
            return []
        
        results = data["resultList"].get("result", [])
        publications = []
        
        for result in results:
            pub = {
                "pmid": result.get("pmid"),
                "pmcid": result.get("pmcid"),
                "doi": result.get("doi"),
                "title": result.get("title"),
                "authors": self._extract_authors(result.get("authorString", "")),
                "journal": result.get("journalTitle"),
                "pub_year": result.get("pubYear"),
                "abstract": result.get("abstractText", "")[:500] + "..." if result.get("abstractText") and len(result.get("abstractText", "")) > 500 else result.get("abstractText"),
                "citation_count": result.get("citedByCount", 0),
                "search_terms": f"{variant_id} + {drug}"
            }
            publications.append(pub)
        
        return publications
    
    def _extract_uniprot_pubmed_evidence(self, variant: Dict) -> List[Dict]:
        """
        Extract PubMed evidence directly from UniProt variant data
        Fetch full publication details from Europe PMC
        
        Args:
            variant: Variant data from UniProt
            
        Returns:
            List of publication dictionaries with UniProt evidence and full text
        """
        uniprot_publications = []
        
        # Extract evidences from the variant directly
        evidences = variant.get("evidences", [])
        
        if not evidences:
            # Debug: Check if variant has any evidence-related fields
            if "evidences" not in variant:
                print(f"     [DEBUG] Variant missing 'evidences' field. Available keys: {list(variant.keys())[:10]}")
        
        for evidence in evidences:
            source = evidence.get("source", {})
            if source.get("name") == "pubmed":
                pmid = source.get("id")
                if pmid:
                    # Fetch full publication details from Europe PMC
                    pub_details = self._fetch_pubmed_full_text(pmid)
                    
                    if pub_details:
                        # Merge UniProt evidence with Europe PMC details
                        pub = {
                            "pmid": pmid,
                            "pmcid": pub_details.get("pmcid"),
                            "doi": pub_details.get("doi"),
                            "title": pub_details.get("title", f"UniProt Evidence (PMID: {pmid})"),
                            "authors": pub_details.get("authors", []),
                            "journal": pub_details.get("journal"),
                            "pub_year": pub_details.get("pub_year"),
                            "abstract": pub_details.get("abstract", ""),
                            "citation_count": pub_details.get("citation_count", 0),
                            "url": pub_details.get("url", f"https://www.ncbi.nlm.nih.gov/pubmed/{pmid}"),
                            "source": "UniProt",
                            "evidence_code": evidence.get("code"),  # ECO code
                            "search_variant": self._get_variant_identifier(variant),
                            "full_text_url": pub_details.get("full_text_url"),
                            "pdf_url": pub_details.get("pdf_url")
                        }
                    else:
                        # Fallback if Europe PMC lookup fails
                        pub = {
                            "pmid": pmid,
                            "pmcid": None,
                            "doi": None,
                            "title": f"UniProt Evidence for Variant (PMID: {pmid})",
                            "authors": [],
                            "journal": None,
                            "pub_year": None,
                            "abstract": "Direct evidence from UniProt variant annotation",
                            "citation_count": 0,
                            "url": source.get("url", f"https://www.ncbi.nlm.nih.gov/pubmed/{pmid}"),
                            "source": "UniProt",
                            "evidence_code": evidence.get("code"),
                            "search_variant": self._get_variant_identifier(variant)
                        }
                    
                    uniprot_publications.append(pub)
        
        if uniprot_publications:
            print(f"     Found {len(uniprot_publications)} UniProt PubMed evidence entries")
        
        return uniprot_publications
    
    def _fetch_pubmed_full_text(self, pmid: str) -> Optional[Dict]:
        """
        Fetch full publication details and text availability from Europe PMC
        
        Args:
            pmid: PubMed ID
            
        Returns:
            Dictionary with publication details including full text URLs
        """
        endpoint = "search"
        params = {
            "query": f"EXT_ID:{pmid}",
            "resultType": "core",
            "format": "json",
            "pageSize": 1
        }
        
        data = self.client.get(endpoint, params=params)
        
        if not data or "resultList" not in data:
            return None
        
        results = data["resultList"].get("result", [])
        if not results:
            return None
        
        result = results[0]
        
        # Get full text availability
        full_text_url = None
        pdf_url = None
        open_access = result.get("openAccess", False)
        pmcid = result.get("pmcid")
        
        # Check for open access full text
        if open_access and pmcid:
            # Clean PMC ID (remove 'PMC' prefix if present)
            clean_pmcid = pmcid.replace('PMC', '') if pmcid.startswith('PMC') else pmcid
            # Europe PMC full text URL
            full_text_url = f"https://europepmc.org/articles/PMC{clean_pmcid}"
            # PDF URL if available
            pdf_url = f"https://europepmc.org/articles/PMC{clean_pmcid}/pdf"
        
        # Also check for PubMed Central (even if not open access, may have free full text)
        if not full_text_url and pmcid:
            clean_pmcid = pmcid.replace('PMC', '') if pmcid.startswith('PMC') else pmcid
            full_text_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{clean_pmcid}/"
            pdf_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{clean_pmcid}/pdf/"
        
        # Check if there's a full text link in the results
        if not full_text_url:
            # Check for fullTextOpenFlag or hasFullText flag
            if result.get("hasFullText") or result.get("fullTextOpenFlag"):
                # Try to construct URL from pmid
                pmid = result.get("pmid")
                if pmid:
                    full_text_url = f"https://europepmc.org/article/MED/{pmid}"
        
        return {
            "pmid": result.get("pmid"),
            "pmcid": result.get("pmcid"),
            "doi": result.get("doi"),
            "title": result.get("title"),
            "authors": self._extract_authors(result.get("authorString", "")),
            "journal": result.get("journalTitle"),
            "pub_year": result.get("pubYear"),
            "abstract": result.get("abstractText", ""),
            "citation_count": result.get("citedByCount", 0),
            "url": f"https://europepmc.org/article/MED/{result.get('pmid')}" if result.get("pmid") else None,
            "full_text_url": full_text_url,
            "pdf_url": pdf_url,
            "open_access": open_access
        }
    
    def _load_original_pubmed_evidence(self, variant: Dict) -> List[Dict]:
        """
        Load PubMed evidence from original extraction files as fallback
        
        Args:
            variant: Variant data
            
        Returns:
            List of publications from original extraction
        """
        from pathlib import Path
        import json
        
        publications = []
        
        # Try to load original PubMed extraction
        pubmed_file = Path("../assignemnt/P10635_pubmed.json")
        if not pubmed_file.exists():
            return publications
        
        try:
            with open(pubmed_file, 'r', encoding='utf-8') as f:
                original_pubmed = json.load(f)
            
            # Get variant identifier to match
            variant_id = self._get_variant_identifier(variant)
            
            # Look for this variant in the original extraction
            for category, variants in original_pubmed.items():
                for var_id, var_data in variants.items():
                    # Try to match by various identifiers
                    if self._variant_matches(variant, var_id, var_data):
                        evidences = var_data.get("evidences", [])
                        for evidence in evidences:
                            source = evidence.get("source", {})
                            if source.get("name") == "pubmed":
                                pmid = source.get("id")
                                if pmid:
                                    pub = {
                                        "pmid": pmid,
                                        "pmcid": None,
                                        "doi": None,
                                        "title": f"UniProt Evidence (Original Extraction) - PMID: {pmid}",
                                        "authors": [],
                                        "journal": None,
                                        "pub_year": None,
                                        "abstract": f"Evidence from UniProt {category} category",
                                        "citation_count": 0,
                                        "url": source.get("url", f"https://www.ncbi.nlm.nih.gov/pubmed/{pmid}"),
                                        "source": "UniProt-Original",
                                        "evidence_code": evidence.get("code"),
                                        "search_variant": variant_id,
                                        "category": category
                                    }
                                    publications.append(pub)
        
        except Exception as e:
            # Silently fail - this is a fallback method
            pass
        
        return publications
    
    def _variant_matches(self, variant: Dict, var_id: str, var_data: Dict) -> bool:
        """
        Check if a variant matches the original extraction data
        
        Args:
            variant: Current variant data
            var_id: Variant ID from original extraction
            var_data: Variant data from original extraction
            
        Returns:
            True if variants match
        """
        # This is a simplified matching - in a full implementation,
        # you would want more sophisticated matching logic
        variant_id = self._get_variant_identifier(variant)
        
        # Direct ID match
        if variant_id in var_id or var_id in variant_id:
            return True
        
        # For now, return False to be conservative
        # In practice, you might want to implement more matching logic
        return False
    
    def _get_variant_identifier(self, variant: Dict) -> str:
        """Get the best identifier for a variant"""
        # Try dbSNP rsID first
        for xref in variant.get("xrefs", []):
            if xref.get("name") == "dbSNP" and xref.get("id"):
                return xref["id"]
        
        # Try protein change
        for location in variant.get("locations", []):
            if location.get("loc") and location["loc"].startswith("p."):
                return location["loc"]
        
        # Try genomic location
        genomic_locations = variant.get("genomicLocation", [])
        if genomic_locations:
            return genomic_locations[0]
        
        return "Unknown"

