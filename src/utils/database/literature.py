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
                    # Extract variant_id from variant_key
                    variant_id = pub.get("variant_id") or variant_key
                    self._insert_variant_publication_link(cursor, variant_id, pub)
        
        # Process drug-related publications
        drug_literature = literature_summary.get("drug_literature", {})
        for drug_name, drug_pubs in drug_literature.items():
            for pub in drug_pubs:
                pmid = pub.get("pmid")
                if pmid and pmid not in self.inserted_pmids:
                    if self._insert_publication_record(cursor, pub):
                        self.inserted_pmids.add(pmid)
                        count += 1
                
                # Insert to drug_publications linking table
                if pmid:
                    self._insert_drug_publication_link(cursor, drug_name, pub)
        
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
                    self._insert_variant_publication_link(cursor, variant_id, pub)
        
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
        """✅ Insert to gene_publications linking table"""
        try:
            cursor.execute("""
                INSERT INTO gene_publications (gene_symbol, pmid, relevance_score, search_query)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                gene_symbol,
                pub.get("pmid"),
                pub.get("relevance_score"),
                pub.get("search_query") or pub.get("search_type")
            ))
        except Exception as e:
            self.logger.warning(f"Could not link gene {gene_symbol} to publication: {e}")
    
    def _insert_variant_publication_link(self, cursor: psycopg.Cursor, variant_id: str, pub: Dict):
        """✅ Insert to variant_publications linking table"""
        try:
            cursor.execute("""
                INSERT INTO variant_publications (variant_id, pmid, relevance_score, search_query)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                variant_id,
                pub.get("pmid"),
                pub.get("relevance_score"),
                pub.get("search_query") or pub.get("search_type")
            ))
        except Exception as e:
            self.logger.warning(f"Could not link variant {variant_id} to publication: {e}")
    
    def _insert_drug_publication_link(self, cursor: psycopg.Cursor, drug_name: str, pub: Dict):
        """✅ Insert to drug_publications linking table"""
        try:
            cursor.execute("""
                INSERT INTO drug_publications (drug_name, pmid, relevance_score, search_query)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                drug_name,
                pub.get("pmid"),
                pub.get("relevance_score"),
                pub.get("search_query") or pub.get("search_type")
            ))
        except Exception as e:
            self.logger.warning(f"Could not link drug {drug_name} to publication: {e}")

