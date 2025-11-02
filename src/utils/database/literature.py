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
        
        # Extract publications from literature_summary
        literature_summary = profile.get("literature_summary", {})
        
        # Process gene-related publications
        gene_literature = literature_summary.get("gene_literature", {})
        for gene_symbol, gene_pubs in gene_literature.items():
            for pub in gene_pubs:
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
        for variant_key, variant_pubs in variant_literature.items():
            for pub in variant_pubs:
                pmid = pub.get("pmid")
                if pmid and pmid not in self.inserted_pmids:
                    if self._insert_publication_record(cursor, pub):
                        self.inserted_pmids.add(pmid)
                        count += 1
                
                # Insert to variant_publications linking table
                if pmid:
                    # Extract variant_id and gene_symbol from variant_key or pub data
                    variant_id = pub.get("variant_id") or variant_key
                    # Try to get gene_symbol from pub or look up from variant data
                    gene_symbol_from_pub = pub.get("gene_symbol") or pub.get("gene")
                    # Store gene_symbol in pub dict for the link function
                    if gene_symbol_from_pub:
                        pub["gene_symbol"] = gene_symbol_from_pub
                    self._insert_variant_publication_link(cursor, variant_id, pub)
        
        # Process drug-related publications
        # Note: Drug publications are tracked via variant_drug_evidence table (see linking_tables.py)
        drug_literature = literature_summary.get("drug_literature", {})
        for drug_name, drug_pubs in drug_literature.items():
            for pub in drug_pubs:
                pmid = pub.get("pmid")
                if pmid and pmid not in self.inserted_pmids:
                    if self._insert_publication_record(cursor, pub):
                        self.inserted_pmids.add(pmid)
                        count += 1
                # Drug-publication links are handled via variant_drug_evidence table
        
        # Process additional publications from variants
        variants = profile.get("variants", [])
        for variant in variants:
            publications = variant.get("publications", [])
            gene_symbol = variant.get("gene")
            variant_id = variant.get("variant_id")
            
            for pub in publications:
                pmid = pub.get("pmid")
                if pmid and pmid not in self.inserted_pmids:
                    if self._insert_publication_record(cursor, pub):
                        self.inserted_pmids.add(pmid)
                        count += 1
                
                # Link to both gene and variant
                if pmid:
                    self._insert_gene_publication_link(cursor, gene_symbol, pub)
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

