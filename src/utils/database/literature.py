"""
Literature Loader - SCHEMA ALIGNED
Handles: publications, gene_publications, variant_publications, drug_publications
"""

import json
import logging
from typing import Dict
import psycopg
from .utils import parse_date


class LiteratureLoader:
    """Loads publications with schema-aligned structure and linking tables"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.inserted_pmids = set()
    
    def load_all(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """Load all literature data"""
        return self.insert_publications(cursor, profile)
    
    def insert_publications(self, cursor: psycopg.Cursor, profile: Dict) -> int:
        """
        ✅ SCHEMA-ALIGNED: Insert publications + linking tables
        MAJOR FIX: publications table redesigned with linking tables:
        - publications: pmid, pmcid, doi, title, authors (JSONB), journal, pub_year, 
                        abstract, citation_count, url, source, evidence_code, 
                        full_text_url, pdf_url, metadata (JSONB)
        - gene_publications: gene_symbol, pmid, relevance_score, search_query
        - variant_publications: variant_id, pmid, relevance_score, search_query
        - drug_publications: drug_name, pmid, relevance_score, search_query
        """
        count = 0
        
        # ✅ FIX: Extract publications from literature_summary (check both root and nested locations)
        literature_summary = profile.get("literature_summary", {})
        if not literature_summary:
            # Also check nested under pharmacogenomics_profile
            pharmacogenomics_profile = profile.get("pharmacogenomics_profile", {})
            literature_summary = pharmacogenomics_profile.get("literature_summary", {})
        
        # ✅ DEBUG: Log what we found
        self.logger.debug(f"🔍 Literature summary found: {bool(literature_summary)}, keys: {list(literature_summary.keys()) if literature_summary else []}")
        
        # Process gene-related publications
        gene_literature = literature_summary.get("gene_literature", {})
        self.logger.debug(f"🔍 Found gene_literature with {len(gene_literature)} genes")
        for gene_symbol, gene_pubs in gene_literature.items():
            if not gene_pubs:
                continue
            self.logger.debug(f"   Processing gene {gene_symbol} with {len(gene_pubs)} publications")
            for pub in gene_pubs:
                if not isinstance(pub, dict):
                    continue
                pmid = pub.get("pmid")
                if pmid and pmid not in self.inserted_pmids:
                    # Insert to publications table
                    if self._insert_publication_record(cursor, pub):
                        self.inserted_pmids.add(pmid)
                        count += 1
                
                # Insert to gene_publications linking table
                if pmid:
                    self._insert_gene_publication_link(cursor, gene_symbol, pub)
        
        # Process variant-related publications
        variant_literature = literature_summary.get("variant_literature", {})
        self.logger.debug(f"🔍 Found variant_literature with {len(variant_literature)} variants")
        for variant_key, variant_pubs in variant_literature.items():
            if not variant_pubs:
                continue
            self.logger.debug(f"   Processing variant {variant_key} with {len(variant_pubs)} publications")
            for pub in variant_pubs:
                if not isinstance(pub, dict):
                    continue
                pmid = pub.get("pmid")
                if pmid and pmid not in self.inserted_pmids:
                    if self._insert_publication_record(cursor, pub):
                        self.inserted_pmids.add(pmid)
                        count += 1
                
                # Insert to variant_publications linking table
                if pmid:
                    # ✅ FIX: Extract variant_id from variant_key (format: "GENE:variant_id" or just "variant_id")
                    # Try pub first, then parse variant_key
                    variant_id = pub.get("variant_id")
                    if not variant_id and variant_key:
                        # variant_key might be "GENE:variant_id" or just "variant_id"
                        if ":" in str(variant_key):
                            # Extract part after colon
                            variant_id = str(variant_key).split(":", 1)[1]
                        else:
                            variant_id = variant_key
                    
                    # Try to get gene_symbol from pub or variant_key
                    gene_symbol_from_pub = pub.get("gene_symbol") or pub.get("gene")
                    if not gene_symbol_from_pub and variant_key and ":" in str(variant_key):
                        # Extract gene from variant_key (format: "GENE:variant_id")
                        gene_symbol_from_pub = str(variant_key).split(":", 1)[0]
                    
                    # Store gene_symbol in pub dict for the link function
                    if gene_symbol_from_pub:
                        pub["gene_symbol"] = gene_symbol_from_pub
                        pub["gene"] = gene_symbol_from_pub
                    if variant_id:
                        pub["variant_id"] = variant_id
                    
                    self._insert_variant_publication_link(cursor, variant_id, pub, gene_symbol_from_pub)
        
        # Process drug-related publications
        # Note: Drug publications are tracked via variant_drug_evidence table (see linking_tables.py)
        drug_literature = literature_summary.get("drug_literature", {})
        self.logger.debug(f"🔍 Found drug_literature with {len(drug_literature)} drugs")
        for drug_name, drug_pubs in drug_literature.items():
            if not drug_pubs:
                continue
            self.logger.debug(f"   Processing drug {drug_name} with {len(drug_pubs)} publications")
            for pub in drug_pubs:
                if not isinstance(pub, dict):
                    continue
                pmid = pub.get("pmid")
                if pmid and pmid not in self.inserted_pmids:
                    if self._insert_publication_record(cursor, pub):
                        self.inserted_pmids.add(pmid)
                        count += 1
                # Drug-publication links are handled via variant_drug_evidence table (inserted by linking_tables.py)
        
        # Process additional publications from variants
        variants = profile.get("variants", [])
        self.logger.debug(f"🔍 Processing {len(variants)} variants for additional publications")
        for variant in variants:
            if not isinstance(variant, dict):
                continue
            publications = variant.get("publications", [])
            if not publications:
                continue
            gene_symbol = variant.get("gene") or variant.get("gene_symbol")
            variant_id = variant.get("variant_id")
            
            self.logger.debug(f"   Variant {variant_id} ({gene_symbol}) has {len(publications)} publications")
            for pub in publications:
                if not isinstance(pub, dict):
                    continue
                pmid = pub.get("pmid")
                if pmid and pmid not in self.inserted_pmids:
                    if self._insert_publication_record(cursor, pub):
                        self.inserted_pmids.add(pmid)
                        count += 1
                
                # Link to both gene and variant
                if pmid:
                    # Ensure pub has gene and variant_id for linking
                    if gene_symbol and not pub.get("gene_symbol"):
                        pub["gene_symbol"] = gene_symbol
                    if variant_id and not pub.get("variant_id"):
                        pub["variant_id"] = variant_id
                    
                    if gene_symbol:
                        self._insert_gene_publication_link(cursor, gene_symbol, pub)
                    if variant_id:
                        self._insert_variant_publication_link(cursor, variant_id, pub, gene_symbol)
        
        self.logger.info(f"✓ SCHEMA-ALIGNED: Inserted {count} publications (with linking tables)")
        return count
    
    def _insert_publication_record(self, cursor: psycopg.Cursor, pub: Dict) -> bool:
        """✅ Insert to publications table with ALL schema columns"""
        try:
            # SCHEMA-ALIGNED: Insert with all columns
            cursor.execute("""
                INSERT INTO publications (
                    pmid, pmcid, doi, title, authors, journal, pub_year, abstract,
                    citation_count, url, source, evidence_code,
                    full_text_url, pdf_url, metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (pmid) DO NOTHING
            """, (
                pub.get("pmid"),
                pub.get("pmcid"),
                pub.get("doi"),
                pub.get("title"),
                json.dumps(pub.get("authors", [])),  # JSONB
                pub.get("journal"),
                pub.get("pub_year") or pub.get("year"),
                pub.get("abstract"),
                pub.get("citation_count") or pub.get("citationCount"),
                pub.get("url"),
                pub.get("source", "PubMed"),
                pub.get("evidence_code"),
                pub.get("full_text_url"),
                pub.get("pdf_url"),
                json.dumps(pub) if pub else None  # metadata (JSONB)
            ))
            return True
        except Exception as e:
            self.logger.warning(f"Could not insert publication {pub.get('pmid')}: {e}")
            return False
    
    def _insert_gene_publication_link(self, cursor: psycopg.Cursor, gene_symbol: str, pub: Dict):
        """✅ Insert to gene_publications linking table (SCHEMA-ALIGNED)"""
        try:
            cursor.execute("""
                INSERT INTO gene_publications (gene_symbol, pmid, search_variant)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                gene_symbol,
                pub.get("pmid"),
                pub.get("search_variant") or pub.get("search_query") or pub.get("search_type") or gene_symbol
            ))
        except Exception as e:
            self.logger.warning(f"Could not link gene {gene_symbol} to publication: {e}")
    
    def _insert_variant_publication_link(self, cursor: psycopg.Cursor, variant_id: str, pub: Dict, gene_symbol: str = None):
        """✅ Insert to variant_publications linking table (SCHEMA-ALIGNED)"""
        try:
            # Get gene_symbol from parameter, pub dict, or try to look up from database
            if not gene_symbol:
                gene_symbol = pub.get("gene_symbol") or pub.get("gene")
            
            # If still not found and variant_id exists, try to look up from patient_variants
            if not gene_symbol and variant_id:
                try:
                    cursor.execute("""
                        SELECT gene_symbol FROM patient_variants 
                        WHERE variant_id = %s LIMIT 1
                    """, (variant_id,))
                    result = cursor.fetchone()
                    if result:
                        gene_symbol = result[0]
                except:
                    pass
            
            cursor.execute("""
                INSERT INTO variant_publications (variant_id, gene_symbol, pmid)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                variant_id,
                gene_symbol,
                pub.get("pmid")
            ))
        except Exception as e:
            self.logger.warning(f"Could not link variant {variant_id} to publication: {e}")

