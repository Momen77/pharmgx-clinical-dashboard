"""
Variant Discovery Module
Discovers clinically significant variants from EMBL-EBI Proteins API
"""
import json
import uuid
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
import sys
sys.path.append(str(Path(__file__).parent.parent))

from utils.api_client import APIClient


class ProteinFetcher:
    """Fetches protein information from UniProt"""
    
    def __init__(self):
        self.base_url = "https://rest.uniprot.org/uniprotkb/stream"
        self.client = APIClient(self.base_url, rate_limit=3)
    
    def get_protein_id(self, gene_symbol: str, organism: str = "human") -> Optional[str]:
        """
        Get UniProt protein accession ID for a human gene symbol
        
        Args:
            gene_symbol: Gene symbol (e.g., CYP2D6)
            organism: Organism name (default: human)
            
        Returns:
            UniProt accession ID or None
        """
        print(f"Fetching UniProt ID for human gene {gene_symbol}...")
        
        # Use taxonomy ID for human (9606) to ensure we only get human proteins
        # This is more precise than text search for "human"
        organism_query = "organism_id:9606" if organism.lower() == "human" else f"organism_name:{organism}"
        
        params = {
            "fields": "accession,reviewed,id,gene_names,organism_name",
            "format": "tsv",
            "query": f"(gene_exact:{gene_symbol}) AND ({organism_query}) AND (reviewed:true)"
        }
        
        try:
            # UniProt returns TSV, not JSON
            import requests
            url = self.base_url
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            lines = response.text.strip().split('\n')
            if len(lines) > 1:
                # Parse TSV response: Entry, Reviewed, Entry Name, Gene Names, Organism
                data_line = lines[1].split('\t')
                if len(data_line) >= 5:
                    accession = data_line[0]
                    organism_name = data_line[4] if len(data_line) > 4 else "Unknown"
                    print(f"   Found UniProt ID: {accession} (Organism: {organism_name})")
                    
                    # Double-check it's human data
                    if organism.lower() == "human" and "homo sapiens" not in organism_name.lower():
                        print(f"   Warning: Expected human protein but got {organism_name}")
                    
                    return accession
                else:
                    print(f"   Unexpected UniProt response format")
            else:
                print(f"   No UniProt entry found for human gene {gene_symbol}")
            
        except Exception as e:
            print(f"   Error fetching UniProt ID: {e}")
        
        return None


class VariantDiscoverer:
    """Discovers and processes genetic variants from EMBL-EBI"""
    
    def __init__(self, output_dir: str = "data/phase1"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.base_url = "https://www.ebi.ac.uk/proteins/api/variation"
        self.client = APIClient(self.base_url, rate_limit=10)
    
    def fetch_variants(self, protein_id: str) -> Optional[Dict]:
        """
        Download raw variant data for a protein
        
        Args:
            protein_id: UniProt protein accession ID
            
        Returns:
            Raw variant data or None
        """
        print(f"Downloading variants for {protein_id}...")
        
        endpoint = f"{protein_id}?format=json"
        data = self.client.get(endpoint)
        
        if data:
            print(f"   Downloaded {len(data.get('features', []))} total variants")
        
        return data
    
    def filter_clinical_variants(self, raw_data: Dict, prefer_population_data: bool = True, prefer_evidence: bool = True) -> List[Dict]:
        """
        Keep only clinically significant variants
        Optionally prioritizes variants with population frequency data and evidence citations
        
        Args:
            raw_data: Raw variant data from EMBL-EBI
            prefer_population_data: If True, prioritize variants with populationFrequencies in UniProt data
            prefer_evidence: If True, prioritize variants with evidence citations (PubMed, etc.)
            
        Returns:
            List of clinically significant variants (sorted by priority if preferences enabled)
        """
        variants = [
            feature for feature in raw_data.get("features", [])
            if "clinicalSignificances" in feature
        ]
        
        # Score variants: higher score = better for population frequency data
        if prefer_population_data or prefer_evidence:
            scored_variants = []
            for variant in variants:
                score = 0
                
                # Prefer variants with embedded population frequency data from UniProt
                if prefer_population_data:
                    pop_freqs = variant.get("populationFrequencies", [])
                    if pop_freqs:
                        # Has population data in UniProt - high priority
                        score += 100
                        # Bonus for having multiple sources (ClinVar + gnomAD)
                        sources = set(p.get("source", "") for p in pop_freqs if p.get("frequency") is not None)
                        if len(sources) > 1:
                            score += 20
                
                # Prefer variants with evidence citations (PubMed, etc.)
                if prefer_evidence:
                    evidences = variant.get("evidences", [])
                    if evidences:
                        score += 50
                        # Bonus for PubMed citations (clinical/literature evidence)
                        pubmed_count = sum(1 for e in evidences if e.get("source", {}).get("name") == "pubmed")
                        if pubmed_count > 0:
                            score += 30
                
                scored_variants.append((score, variant))
            
            # Sort by score (descending) - variants with population data and evidence first
            scored_variants.sort(key=lambda x: x[0], reverse=True)
            variants = [v for _, v in scored_variants]
            
            if prefer_population_data:
                has_pop = sum(1 for v in variants if v.get("populationFrequencies"))
                print(f"   {has_pop}/{len(variants)} variants have embedded population frequency data")
            if prefer_evidence:
                has_ev = sum(1 for v in variants if v.get("evidences"))
                print(f"   {has_ev}/{len(variants)} variants have evidence citations")
        
        print(f"   Filtered to {len(variants)} clinically significant variants")
        return variants
    
    def categorize_by_significance(self, variants: List[Dict]) -> Dict[str, List]:
        """
        Group variants by clinical significance type
        
        Args:
            variants: List of clinical variants
            
        Returns:
            Dictionary mapping significance types to variant lists
        """
        categories = {}
        for variant in variants:
            for sig in variant.get("clinicalSignificances", []):
                sig_type = sig["type"]
                if sig_type not in categories:
                    categories[sig_type] = []
                categories[sig_type].append(variant)
        
        print(f"   Categorized into {len(categories)} significance types:")
        for cat, vars in categories.items():
            print(f"      {cat}: {len(vars)} variants")
        
        return categories
    
    def extract_pubmed_evidence(self, categorized: Dict) -> Dict:
        """
        Extract PubMed citations for each variant
        
        Args:
            categorized: Categorized variants
            
        Returns:
            Dictionary mapping variants to their PubMed IDs
        """
        pubmed_data = {}
        
        for category, variants in categorized.items():
            category_pubmed = {}
            for variant in variants:
                for evidence in variant.get("evidences", []):
                    source = evidence.get("source", {})
                    if source.get("name") == "pubmed":
                        ftId = variant.get("ftId", "Unknown")
                        if ftId not in category_pubmed:
                            category_pubmed[ftId] = {
                                "variant": variant,
                                "pubmed_ids": []
                            }
                        # Extract PubMed ID from URL
                        url = source.get("url", "")
                        pmid = url.split("/")[-1] if url else None
                        if pmid and pmid.isdigit():
                            category_pubmed[ftId]["pubmed_ids"].append(pmid)
            
            if category_pubmed:
                pubmed_data[category] = category_pubmed
        
        return pubmed_data
    
    def select_realistic_diplotype(self, categorized_variants: Dict[str, List]) -> List[Dict]:
        """
        Select a realistic diplotype (2 alleles) from available variants
        
        Args:
            categorized_variants: Variants grouped by clinical significance
            
        Returns:
            List of 2 variants representing a realistic diplotype
        """
        selected_variants = []
        
        # Priority order for clinical interest
        priority_categories = [
            "Drug response",
            "Pathogenic", 
            "Likely pathogenic",
            "Variant of uncertain significance",
            "Benign",
            "Likely benign"
        ]
        
        # Try to get one high-impact and one moderate-impact variant
        for category in priority_categories:
            if category in categorized_variants and categorized_variants[category]:
                variants = categorized_variants[category]
                
                # Within each category, prefer variants with population frequency data and evidence
                # Sort variants by: 1) has populationFrequencies, 2) has evidences, 3) original order
                def variant_priority(v):
                    score = 0
                    if v.get("populationFrequencies"):
                        score += 10  # Prioritize variants with embedded population data
                    if v.get("evidences"):
                        score += 5   # Then prefer variants with evidence citations
                    return -score  # Negative for descending sort
                
                variants = sorted(variants, key=variant_priority)
                
                # Select the first (highest priority) variant from this category
                if len(selected_variants) < 2:
                    variant = variants[0].copy()  # Make a copy to preserve evidences
                    selected_variants.append(variant)
                    print(f"   Selected {category} variant: {variant.get('ftId', 'Unknown')}")
                    if variant.get('populationFrequencies'):
                        pop_sources = [p.get("source", "") for p in variant['populationFrequencies'] if p.get("frequency") is not None]
                        print(f"      Has population frequency data from: {', '.join(set(pop_sources))}")
                    if variant.get('evidences'):
                        print(f"      Has {len(variant['evidences'])} evidence entries")
                
                # If we have 2 variants, we're done
                if len(selected_variants) == 2:
                    break
        
        # If we only found 1 variant, duplicate it (homozygous)
        if len(selected_variants) == 1:
            selected_variants.append(selected_variants[0])
            print(f"   Creating homozygous diplotype (same variant on both alleles)")
        
        # If no variants found, create empty diplotype
        if len(selected_variants) == 0:
            print(f"   No variants available - creating reference diplotype")
            return []
        
        return selected_variants

    def create_virtual_patient(self, gene_symbol: str, protein_id: str, selected_variants: List[Dict] = None) -> Dict:
        """
        Create virtual human patient profile with realistic diplotype following RDF patterns
        
        Args:
            gene_symbol: Human gene symbol (e.g., CYP2D6)
            protein_id: Human UniProt protein ID (e.g., P10635)
            selected_variants: List of selected human variants (max 2)
            
        Returns:
            Virtual human patient profile dictionary with proper RDF structure
        """
        patient_id = f"virtual_patient_{gene_symbol.lower()}_{uuid.uuid4().hex[:8]}"
        
        # Determine diplotype description
        if not selected_variants or len(selected_variants) == 0:
            diplotype_desc = f"Reference diplotype (no variants)"
            genotype_summary = "Wild-type/Wild-type"
        elif len(selected_variants) == 1:
            diplotype_desc = f"Homozygous for {selected_variants[0].get('ftId', 'variant')}"
            genotype_summary = "Variant/Variant (homozygous)"
        else:
            var1 = selected_variants[0].get('ftId', 'variant1')
            var2 = selected_variants[1].get('ftId', 'variant2')
            if var1 == var2:
                diplotype_desc = f"Homozygous for {var1}"
                genotype_summary = f"{var1}/{var1} (homozygous)"
            else:
                diplotype_desc = f"Compound heterozygous: {var1} and {var2}"
                genotype_summary = f"{var1}/{var2} (heterozygous)"
        
        # Create comprehensive RDF-style patient profile
        patient_profile = {
            "@context": {
                "foaf": "http://xmlns.com/foaf/0.1/",
                "schema": "http://schema.org/",
                "sio": "http://semanticscience.org/resource/",
                "obo": "http://purl.obolibrary.org/obo/",
                "pgx": "http://pgx-kg.org/",
                "uniprot": "https://identifiers.org/uniprot:",
                "hgnc": "https://identifiers.org/hgnc:",
                "xsd": "http://www.w3.org/2001/XMLSchema#"
            },
            "@id": f"http://pgx-kg.org/patient/{patient_id}",
            "@type": ["foaf:Person", "schema:Patient"],
            
            # Basic patient information (following FOAF/Schema.org patterns)
            "foaf:identifier": patient_id,
            "schema:identifier": patient_id,
            "foaf:name": f"Virtual Human Patient - {gene_symbol} Profile",
            "schema:name": f"Virtual Human Patient - {gene_symbol} Profile",
            "schema:description": f"Virtual human patient with realistic {gene_symbol} diplotype for pharmacogenomics analysis",
            "schema:dateCreated": {
                "@type": "xsd:dateTime",
                "@value": datetime.now().isoformat()
            },
            
            # Pharmacogenomics-specific properties
            "pgx:focusGene": {
                "@id": f"hgnc:{gene_symbol}",
                "schema:name": gene_symbol,
                "@type": "obo:SO_0000704"  # Gene
            },
            "pgx:focusProtein": {
                "@id": f"uniprot:{protein_id}",
                "schema:identifier": protein_id,
                "@type": "obo:SO_0000104"  # Protein
            },
            
            # Genotype information (following GENO ontology patterns)
            "sio:SIO_000228": {  # has role
                "@id": f"http://pgx-kg.org/genotype/{patient_id}_genotype",
                "@type": "obo:GENO_0000536",  # genotype
                "schema:name": f"{gene_symbol} Pharmacogenomics Genotype",
                "schema:description": diplotype_desc,
                "pgx:genotypeCall": genotype_summary,
                "pgx:variantCount": len(selected_variants) if selected_variants else 0,
                "schema:dateCreated": {
                    "@type": "xsd:dateTime", 
                    "@value": datetime.now().isoformat()
                }
            },
            
            # Data provenance
            "schema:dataSource": [
                "EMBL-EBI Proteins API",
                "UniProt"
            ],
            "schema:creator": "PGx-KG Pipeline",
            "schema:version": "1.0",
            
            # Clinical context
            "pgx:clinicalPurpose": "Pharmacogenomics analysis for personalized medicine",
            "pgx:analysisType": "Variant discovery and diplotype determination"
        }
        
        # Add variant references if available
        if selected_variants:
            variant_refs = []
            for i, variant in enumerate(selected_variants):
                variant_id = variant.get('ftId', f'variant_{i+1}')
                variant_refs.append({
                    "@id": f"http://pgx-kg.org/variant/{variant_id}",
                    "schema:identifier": variant_id,
                    "@type": "obo:SO_0001583",  # SNV
                    "schema:position": variant.get('begin', 'unknown'),
                    "pgx:clinicalSignificance": [sig.get('type') for sig in variant.get('clinicalSignificances', [])]
                })
            
            patient_profile["sio:SIO_000228"]["sio:SIO_000008"] = variant_refs  # has attribute
        
        return patient_profile
    
    def create_patient_rdf_turtle(self, patient_profile: Dict, output_file: str = None) -> str:
        """
        Generate RDF Turtle representation of the patient profile
        Similar to the generate_person_profile_rdf.py pattern
        
        Args:
            patient_profile: Patient profile dictionary
            output_file: Optional output file path
            
        Returns:
            Turtle string representation
        """
        from rdflib import Graph, Namespace, URIRef, Literal
        from rdflib.namespace import RDF, RDFS, XSD
        
        # Define namespaces (similar to your example)
        FOAF = Namespace("http://xmlns.com/foaf/0.1/")
        SCHEMA = Namespace("http://schema.org/")
        SIO = Namespace("http://semanticscience.org/resource/")
        OBO = Namespace("http://purl.obolibrary.org/obo/")
        PGX = Namespace("http://pgx-kg.org/")
        UNIPROT = Namespace("https://identifiers.org/uniprot:")
        HGNC = Namespace("https://identifiers.org/hgnc:")
        
        # Create graph and bind namespaces
        g = Graph()
        g.bind("foaf", FOAF)
        g.bind("schema", SCHEMA)
        g.bind("sio", SIO)
        g.bind("obo", OBO)
        g.bind("pgx", PGX)
        g.bind("uniprot", UNIPROT)
        g.bind("hgnc", HGNC)
        g.bind("xsd", XSD)
        
        # Patient URI
        patient_uri = URIRef(patient_profile["@id"])
        
        # Add patient triples
        g.add((patient_uri, RDF.type, FOAF.Person))
        g.add((patient_uri, RDF.type, SCHEMA.Patient))
        g.add((patient_uri, FOAF.name, Literal(patient_profile["foaf:name"])))
        g.add((patient_uri, SCHEMA.name, Literal(patient_profile["schema:name"])))
        g.add((patient_uri, SCHEMA.description, Literal(patient_profile["schema:description"])))
        g.add((patient_uri, SCHEMA.dateCreated, Literal(patient_profile["schema:dateCreated"]["@value"], datatype=XSD.dateTime)))
        
        # Add species information to ensure it's clearly human
        g.add((patient_uri, SCHEMA.species, Literal("Homo sapiens")))
        g.add((patient_uri, PGX.taxonomyId, Literal("9606")))  # NCBI Taxonomy ID for humans
        
        # Add gene information
        gene_info = patient_profile["pgx:focusGene"]
        gene_uri = URIRef(gene_info["@id"])
        g.add((gene_uri, RDF.type, URIRef("http://purl.obolibrary.org/obo/SO_0000704")))  # Gene
        g.add((gene_uri, SCHEMA.name, Literal(gene_info["schema:name"])))
        g.add((patient_uri, PGX.focusGene, gene_uri))
        
        # Add protein information
        protein_info = patient_profile["pgx:focusProtein"]
        protein_uri = URIRef(protein_info["@id"])
        g.add((protein_uri, RDF.type, URIRef("http://purl.obolibrary.org/obo/SO_0000104")))  # Protein
        g.add((protein_uri, SCHEMA.identifier, Literal(protein_info["schema:identifier"])))
        g.add((patient_uri, PGX.focusProtein, protein_uri))
        
        # Add genotype information
        genotype_info = patient_profile["sio:SIO_000228"]
        genotype_uri = URIRef(genotype_info["@id"])
        g.add((genotype_uri, RDF.type, URIRef("http://purl.obolibrary.org/obo/GENO_0000536")))  # Genotype
        g.add((genotype_uri, SCHEMA.name, Literal(genotype_info["schema:name"])))
        g.add((genotype_uri, SCHEMA.description, Literal(genotype_info["schema:description"])))
        g.add((patient_uri, SIO.SIO_000228, genotype_uri))  # has role
        
        # Serialize to turtle
        turtle_content = g.serialize(format="turtle")
        
        # Save to file if specified
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(turtle_content)
            print(f"Patient RDF saved to: {output_file}")
        
        return turtle_content
    
    def run_pipeline(self, gene_symbol: str, protein_id: Optional[str] = None) -> Dict:
        """
        Execute full variant discovery pipeline
        
        Args:
            gene_symbol: Gene symbol (e.g., CYP2D6)
            protein_id: UniProt ID (optional, will be fetched if not provided)
            
        Returns:
            Dictionary with discovery results
        """
        print(f"\n{'='*60}")
        print(f"Phase 1: Variant Discovery for {gene_symbol}")
        print(f"{'='*60}\n")
        
        # Get protein ID if not provided
        if not protein_id:
            protein_fetcher = ProteinFetcher()
            protein_id = protein_fetcher.get_protein_id(gene_symbol)
            if not protein_id:
                raise ValueError(f"Could not find UniProt ID for gene {gene_symbol}")
        
        # Download variants
        raw_data = self.fetch_variants(protein_id)
        if not raw_data:
            raise ValueError(f"Failed to fetch variants for {protein_id}")
        
        # Filter clinical variants
        clinical_variants = self.filter_clinical_variants(raw_data)
        if not clinical_variants:
            print(f"   WARNING: No clinically significant variants found")
        
        # Categorize
        categorized = self.categorize_by_significance(clinical_variants)
        
        # Extract evidence
        pubmed_data = self.extract_pubmed_evidence(categorized)
        
        # Select realistic diplotype (2 variants max)
        print(f"\n   Selecting realistic diplotype...")
        selected_variants = self.select_realistic_diplotype(categorized)
        
        # Ensure evidences are preserved in selected variants
        # Match by comparing variant structure (locations, genomicLocation, etc.)
        for variant in selected_variants:
            if not variant.get("evidences"):
                # Try to find original variant with evidences by matching locations/genomic location
                variant_locations = variant.get("locations", [])
                variant_genomic = variant.get("genomicLocation", [])
                
                for cat_variants in categorized.values():
                    for orig_variant in cat_variants:
                        if orig_variant.get("evidences"):
                            # Match by locations
                            orig_locations = orig_variant.get("locations", [])
                            if variant_locations and orig_locations:
                                # Check if locations match
                                variant_loc_keys = {loc.get("position", {}).get("position", {}).get("value") for loc in variant_locations}
                                orig_loc_keys = {loc.get("position", {}).get("position", {}).get("value") for loc in orig_locations}
                                if variant_loc_keys == orig_loc_keys and variant_loc_keys:
                                    variant["evidences"] = orig_variant["evidences"]
                                    print(f"      Restored {len(orig_variant['evidences'])} evidence entries for variant")
                                    break
                            
                            # Also try matching by genomic location
                            if not variant.get("evidences"):
                                orig_genomic = orig_variant.get("genomicLocation", [])
                                if variant_genomic and orig_genomic and variant_genomic == orig_genomic:
                                    variant["evidences"] = orig_variant["evidences"]
                                    print(f"      Restored {len(orig_variant['evidences'])} evidence entries (by genomic location)")
                                    break
                        
                        if variant.get("evidences"):
                            break
        
        # Create virtual patient with selected diplotype
        virtual_patient = self.create_virtual_patient(gene_symbol, protein_id, selected_variants)
        
        # Prepare output
        output = {
            "gene_symbol": gene_symbol,
            "protein_id": protein_id,
            "total_variants": len(clinical_variants),
            "selected_diplotype": {
                "variants": selected_variants,
                "count": len(selected_variants),
                "description": virtual_patient.get("diplotype", {}).get("description", "")
            },
            "variant_catalog": {
                "categories": categorized,
                "pubmed_evidence": pubmed_data,
                "note": "Complete catalog of all discovered variants (for reference only)"
            },
            "raw_data": raw_data,
            "timestamp": datetime.now().isoformat()
        }
        
        # Generate RDF Turtle representation (following your example pattern)
        print(f"   Generating RDF Turtle representation...")
        turtle_file = self.output_dir / f"{gene_symbol}_virtual_patient.ttl"
        turtle_content = self.create_patient_rdf_turtle(virtual_patient, str(turtle_file))
        
        # Save outputs
        variants_file = self.output_dir / f"{gene_symbol}_variants.json"
        patient_file = self.output_dir / f"{gene_symbol}_virtual_patient.json"
        
        with open(variants_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2)
        
        with open(patient_file, 'w', encoding='utf-8') as f:
            json.dump(virtual_patient, f, indent=2)
        
        print(f"\nPhase 1 Complete!")
        print(f"   Variants saved: {variants_file}")
        print(f"   Patient profile saved: {patient_file}")
        print(f"   Patient RDF saved: {turtle_file}")
        
        return output


if __name__ == "__main__":
    # Test the module
    discoverer = VariantDiscoverer()
    result = discoverer.run_pipeline("CYP2D6")
    print(f"\n   Total variants discovered: {result['total_variants']}")

