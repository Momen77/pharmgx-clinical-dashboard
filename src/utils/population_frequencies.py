import json
import time
from pathlib import Path
from typing import Dict, Optional

import requests


ENSEMBL_VARIATION_URL = "https://rest.ensembl.org/variation/homo_sapiens/{rsid}?content-type=application/json"
ENSEMBL_LOOKUP_URL = "https://rest.ensembl.org/variation/human/{rsid}?content-type=application/json"
GNOMAD_API_URL = "https://gnomad.broadinstitute.org/api"
DBSNP_SUMMARY_URL = "https://api.ncbi.nlm.nih.gov/variation/v0/beta/refsnp/{rsid_num}"
DBSNP_ALFA_URL = "https://www.ncbi.nlm.nih.gov/snp/{rsid}?report=Json"


# Map upstream population labels to our canonical ethnicity categories
_POPULATION_MAP = {
    # Ensembl/1000G
    "1000GENOMES:phase_3:AFR": "African",
    "1000GENOMES:phase_3:EAS": "Asian",
    "1000GENOMES:phase_3:EUR": "Caucasian/European",
    "1000GENOMES:phase_3:AMR": "Hispanic/Latino",
    "1000GENOMES:phase_3:SAS": "Asian",
    # gnomAD (if present in Ensembl payload)
    "gnomAD:AFR": "African",
    "gnomAD:AMR": "Hispanic/Latino",
    "gnomAD:ASJ": "Caucasian/European",  # Ashkenazi Jewish (closest canonical bucket)
    "gnomAD:EAS": "Asian",
    "gnomAD:NFE": "Caucasian/European",
    "gnomAD:FIN": "Caucasian/European",
    "gnomAD:OTH": "Mixed",
}


def _category_template() -> Dict[str, Optional[float]]:
    return {
        "African": None,
        "Asian": None,
        "Caucasian/European": None,
        "Hispanic/Latino": None,
        "Middle Eastern": None,  # Not typically present upstream; left for future sources
        "Mixed": None,
    }


class PopulationFrequencyService:
    def __init__(self, cache_dir: Path | str = "data/cache/popfreq", cache_ttl_days: int = 30, enabled: bool = True):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl_sec = cache_ttl_days * 24 * 3600
        self.enabled = enabled

    def get_population_frequencies(self, rsid: str, variant_raw_data: Optional[Dict] = None) -> Dict:
        """
        Get population frequencies for a variant
        
        Args:
            rsid: rsID (e.g., "rs123456")
            variant_raw_data: Optional variant raw data from UniProt/EMBL-EBI (for extracting genomic coordinates)
        
        Returns:
            Dict with frequencies by ethnicity category and source
        """
        if not self.enabled or not rsid or not rsid.startswith("rs"):
            return {"frequencies": _category_template(), "source": "disabled"}

        cached = self._load_cache(rsid)
        if cached is not None:
            return cached

        source = None
        freqs = _category_template()
        
        # PRIORITY 0: Extract embedded population frequencies from UniProt/EMBL-EBI raw data (if available)
        # This is the most reliable source as it's already in the variant data
        if variant_raw_data:
            embedded_freqs = self._extract_embedded_population_frequencies(variant_raw_data)
            if embedded_freqs:
                source = embedded_freqs.get("source", "UniProt")
                embedded_freq_dict = embedded_freqs.get("frequencies", {})
                # Merge embedded frequencies (prefer embedded over external)
                for cat, freq in embedded_freq_dict.items():
                    if freq is not None:
                        if freqs[cat] is None:
                            freqs[cat] = freq
                        else:
                            freqs[cat] = max(freqs[cat], freq)  # Take max if conflict
        
        # Try to extract genomic coordinates from variant raw data (if available)
        genomic_coords = None
        if variant_raw_data:
            genomic_coords = self._extract_genomic_coords_from_variant(variant_raw_data)

        # Primary: Ensembl (only if embedded frequencies not found or incomplete)
        if source is None or all(v is None for v in freqs.values()):
            ensembl_data = self._fetch_ensembl(rsid)
            if ensembl_data is not None:
                source = source or "Ensembl"
                # Extract population frequencies from Ensembl
                for pop in ensembl_data.get("populations", []):
                    label = pop.get("name") or ""
                    freq = pop.get("frequency")
                    if freq is None:
                        continue
                    cat = _POPULATION_MAP.get(label)
                    if not cat:
                        continue
                    if freqs[cat] is None:
                        freqs[cat] = float(freq)
                    else:
                        freqs[cat] = max(freqs[cat], float(freq))
                
                # Extract genomic coordinates for better gnomAD queries (if not already extracted)
                if not genomic_coords:
                    genomic_coords = self._extract_genomic_coords_from_ensembl(ensembl_data)

        # Secondary: gnomAD GraphQL (try with coordinates if available, then rsID)
        if source is None or all(v is None for v in freqs.values()):
            gnomad = self._fetch_gnomad(rsid, genomic_coords)
            if gnomad is not None:
                source = source or "gnomAD"
                # gnomAD uses subpopulations; collapse to canonical buckets
                for bucket, vals in gnomad.items():
                    # vals is a list of frequencies in that canonical bucket
                    if not vals:
                        continue
                    val = max(vals)  # take max observed among subpops
                    if freqs[bucket] is None:
                        freqs[bucket] = val
                    else:
                        freqs[bucket] = max(freqs[bucket], val)

        # Tertiary: dbSNP summary (if still empty). Note: dbSNP has limited pop data
        if source is None or all(v is None for v in freqs.values()):
            dbsnp = self._fetch_dbsnp(rsid)
            if dbsnp is not None:
                source = "dbSNP"
                for key, cat in (
                    ("AFR", "African"),
                    ("EAS", "Asian"),
                    ("EUR", "Caucasian/European"),
                    ("AMR", "Hispanic/Latino"),
                ):
                    v = dbsnp.get(key)
                    if isinstance(v, (int, float)) and 0 <= v <= 1:
                        freqs[cat] = float(v) if freqs[cat] is None else max(freqs[cat], float(v))

        result = {"frequencies": freqs, "source": source or "unavailable"}
        self._save_cache(rsid, result)
        return result

    def _fetch_ensembl(self, rsid: str) -> Optional[Dict]:
        """Fetch population frequencies from Ensembl variation API"""
        url = ENSEMBL_VARIATION_URL.format(rsid=rsid)
        try:
            resp = requests.get(url, headers={"User-Agent": "pgx-kg/ethnicity-af"}, timeout=15)
            if resp.status_code == 429:
                time.sleep(1.0)
                resp = requests.get(url, headers={"User-Agent": "pgx-kg/ethnicity-af"}, timeout=15)
            if resp.ok:
                data = resp.json()
                # Verify we got population data
                pops = data.get("populations", [])
                if pops:
                    return data
                # If no populations, try lookup endpoint for coordinates
                return self._fetch_ensembl_lookup(rsid)
        except Exception:
            pass
        return None
    
    def _fetch_ensembl_lookup(self, rsid: str) -> Optional[Dict]:
        """Try Ensembl lookup endpoint to get variant details (may include population data)"""
        url = ENSEMBL_LOOKUP_URL.format(rsid=rsid)
        try:
            resp = requests.get(url, headers={"User-Agent": "pgx-kg/ethnicity-af"}, timeout=15)
            if resp.ok:
                return resp.json()
        except Exception:
            pass
        return None
    
    def _extract_genomic_coords_from_variant(self, variant: Dict) -> Optional[str]:
        """Extract genomic coordinates from UniProt/EMBL-EBI variant data for gnomAD query"""
        import re
        # Try genomicLocation field (most common in UniProt data)
        genomic_locations = variant.get("genomicLocation", [])
        if genomic_locations:
            for loc in genomic_locations:
                # Format: "NC_000006.12:g.18130762C>T" or similar
                if ":" in loc and ">" in loc:
                    # Extract chromosome, position, ref, alt
                    # NC_000006.12:g.18130762C>T -> chr=6, pos=18130762, ref=C, alt=T
                    parts = loc.split(":")
                    if len(parts) >= 2:
                        # Get chromosome from first part
                        chrom_part = parts[0]
                        # Extract chromosome number from NC_000006.12 or similar
                        chrom = None
                        if "NC_" in chrom_part:
                            # NC_000006.12 -> extract 6
                            match = re.search(r'NC_0+(\d+)', chrom_part)
                            if match:
                                chrom = match.group(1)
                        
                        # Get position and alleles from second part
                        pos_allele = parts[1]
                        # g.18130762C>T -> extract position and alleles
                        match = re.search(r'g\.(\d+)([ACGT]+)>([ACGT]+)', pos_allele)
                        if match and chrom:
                            pos, ref, alt = match.groups()
                            # Use colon format for gnomAD (e.g., "22:42130772:A:G")
                            return f"{chrom}:{pos}:{ref}:{alt}"
        
        return None
    
    def _extract_genomic_coords_from_ensembl(self, ensembl_data: Dict) -> Optional[str]:
        """Extract genomic coordinates (chr:pos:ref:alt) from Ensembl response for gnomAD query"""
        import re
        # Ensembl may have mappings array with genomic coordinates
        mappings = ensembl_data.get("mappings", [])
        if not mappings:
            return None
        
        for mapping in mappings:
            # Try to construct gnomAD format: chr-pos-ref-alt
            location = mapping.get("location", "")
            allele_string = mapping.get("allele_string", "")
            
            # Handle different formats
            if location and ":" in location:
                parts = location.split(":")
                if len(parts) >= 2:
                    chrom = parts[0].replace("chr", "").replace("Chr", "").replace("CHR", "")
                    # Remove any non-digit prefix (like "NC_000001.11")
                    chrom = re.sub(r'^\D+', '', chrom)
                    if not chrom:
                        continue
                    
                    pos_part = parts[1]
                    # Extract position number
                    pos_match = re.search(r'(\d+)', pos_part)
                    if not pos_match:
                        continue
                    pos = pos_match.group(1)
                    
                    # Get ref/alt from allele_string or location
                    if allele_string and "/" in allele_string:
                        alleles = allele_string.split("/")
                        if len(alleles) >= 2:
                            ref, alt = alleles[0], alleles[1]
                            # Use colon format for gnomAD (e.g., "22:42130772:A:G")
                            return f"{chrom}:{pos}:{ref}:{alt}"
                    elif ">" in pos_part:
                        # Format like "18130762C>T"
                        match = re.search(r'(\d+)([ACGT]+)>([ACGT]+)', pos_part)
                        if match:
                            pos, ref, alt = match.group(1), match.group(2), match.group(3)
                            # Use colon format for gnomAD (e.g., "22:42130772:A:G")
                            return f"{chrom}:{pos}:{ref}:{alt}"
        
        return None

    def _fetch_gnomad(self, rsid: str, genomic_coords: Optional[str] = None) -> Optional[Dict[str, list]]:
        """Fetch population AFs from gnomAD GraphQL and map to canonical buckets.
        Prefers genomic coordinates over rsID for better accuracy.
        Returns a dict of canonical bucket -> list[float].
        
        Tries multiple gnomAD datasets in order: gnomad_r4, gnomad_r3, gnomad_r2_1
        """
        try:
            # Try by genomic coordinates first (more reliable)
            variant_id = genomic_coords if genomic_coords else rsid
            
            # gnomAD uses 1-based indexing for colon format (NOT 0-based!)
            # Test results show: 22:42130772:A:G (1-based) WORKS, 22:42130771:A:G (0-based) FAILS
            # Handle both colon format (22:42130772:A:G) and hyphen format (22-42130772-A-G)
            if genomic_coords:
                if ":" in genomic_coords:
                    # Colon format: 22:42130772:A:G - USE AS-IS (1-based, don't adjust!)
                    variant_id = genomic_coords
                elif "-" in genomic_coords:
                    # Hyphen format: 22-42130772-A-G (convert to colon format, keep 1-based)
                    parts = genomic_coords.split("-")
                    if len(parts) == 4:
                        chrom, pos_str, ref, alt = parts
                        # Convert to colon format, keep position as-is (1-based)
                        variant_id = f"{chrom}:{pos_str}:{ref}:{alt}"
                    else:
                        variant_id = genomic_coords
                else:
                    variant_id = genomic_coords
            
            # Try multiple datasets: v4, v3, v2.1 (in order of preference)
            datasets = ["gnomad_r4", "gnomad_r3", "gnomad_r2_1"]
            
            for dataset in datasets:
                query = {
                    "query": (
                        "query($variantId: String!, $datasetId: DatasetId!) { \n"
                        "  variant(variantId: $variantId, dataset: $datasetId) { \n"
                        "    genome { ac af an populations { id ac an ac_hom } } \n"
                        "    exome { ac af an populations { id ac an ac_hom } } \n"
                        "  } \n"
                        "}"
                    ),
                    "variables": {"variantId": variant_id, "datasetId": dataset}
                }
                
                try:
                    resp = requests.post(
                        GNOMAD_API_URL, 
                        json=query, 
                        headers={"User-Agent": "pgx-kg/ethnicity-af", "Content-Type": "application/json"}, 
                        timeout=20
                    )
                    
                    if not resp.ok:
                        continue  # Try next dataset
                    
                    json_resp = resp.json()
                    errors = json_resp.get("errors")
                    if errors:
                        continue  # Try next dataset
                    
                    data = json_resp.get("data", {})
                    variant = data.get("variant")
                    if not variant:
                        continue  # Try next dataset
                    
                    # If we get here, we have data from this dataset
                    break
                except Exception:
                    continue  # Try next dataset
            else:
                # All datasets failed
                return None
            
            if not variant:
                return None
                
            buckets = {"African": [], "Asian": [], "Caucasian/European": [], "Hispanic/Latino": [], "Middle Eastern": [], "Mixed": []}
            def collect(pop_list):
                for p in (pop_list or []):
                    pid = (p.get("id") or "").upper()
                    ac = p.get("ac") or 0
                    an = p.get("an") or 0
                    if not an:
                        continue
                    af = ac / an
                    # Map common gnomAD pop IDs
                    if pid in ("AFR",):
                        buckets["African"].append(af)
                    elif pid in ("EAS", "SAS"):
                        buckets["Asian"].append(af)
                    elif pid in ("NFE", "FIN", "ASJ"):
                        buckets["Caucasian/European"].append(af)
                    elif pid in ("AMR",):
                        buckets["Hispanic/Latino"].append(af)
                    else:
                        buckets["Mixed"].append(af)
            if variant.get("genome"):
                collect(variant["genome"].get("populations"))
            if variant.get("exome"):
                collect(variant["exome"].get("populations"))
            return buckets if any(buckets.values()) else None
        except Exception:
            return None

    def _fetch_dbsnp(self, rsid: str) -> Optional[Dict[str, float]]:
        """Fetch population AFs from dbSNP/ALFA if available."""
        try:
            if not rsid.startswith("rs"):
                return None
            
            # Try NCBI Variation API (recommended endpoint)
            num = rsid.replace("rs", "")
            url = DBSNP_SUMMARY_URL.format(rsid_num=num)
            resp = requests.get(url, headers={"User-Agent": "pgx-kg/ethnicity-af", "Accept": "application/json"}, timeout=15)
            
            out = {}
            if resp.ok:
                try:
                    data = resp.json()
                    # Try multiple possible schema locations
                    # Path 1: primary_snapshot_data -> allele_annotations -> frequency
                    psd = data.get("primary_snapshot_data") or {}
                    anns = psd.get("allele_annotations") or []
                    for ann in anns:
                        for freq in (ann.get("frequency") or []):
                            pop = freq.get("population") or {}
                            pop_code = (pop.get("name") or "").upper()
                            af = freq.get("allele_count")
                            an = freq.get("allele_number")
                            if isinstance(af, (int, float)) and isinstance(an, (int, float)) and an > 0:
                                val = float(af) / float(an)
                                if pop_code in ("AFR", "EAS", "EUR", "AMR"):
                                    if pop_code not in out or val > out[pop_code]:
                                        out[pop_code] = val
                    
                    # Path 2: Check for ALFA data (Allele Frequency Aggregator)
                    # ALFA data might be in different location - check for any frequency arrays
                    if not out:
                        # Look for any frequency-like structures
                        def extract_freqs_recursive(obj, path=""):
                            if isinstance(obj, dict):
                                for k, v in obj.items():
                                    if "freq" in k.lower() or "allele" in k.lower():
                                        extract_freqs_recursive(v, f"{path}.{k}")
                                    else:
                                        extract_freqs_recursive(v, f"{path}.{k}")
                            elif isinstance(obj, list):
                                for item in obj:
                                    extract_freqs_recursive(item, path)
                        
                        # Simplified: just try the known paths
                        pass
                except Exception as e:
                    pass
            
            # Fallback: Try HTML page scraping approach (not recommended but might work)
            # Actually, better to just return what we got
            return out or None
        except Exception:
            return None

    def _cache_path(self, rsid: str) -> Path:
        return self.cache_dir / f"{rsid}.json"

    def _load_cache(self, rsid: str) -> Optional[Dict]:
        p = self._cache_path(rsid)
        if not p.exists():
            return None
        try:
            # Expire cache
            if (time.time() - p.stat().st_mtime) > self.cache_ttl_sec:
                return None
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def _save_cache(self, rsid: str, payload: Dict) -> None:
        p = self._cache_path(rsid)
        try:
            with open(p, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception:
            pass


def classify_population_significance(freq: Optional[float]) -> Optional[str]:
    if freq is None:
        return None
    if freq < 0.01:
        return "very_rare"
    if freq < 0.05:
        return "rare"
    if freq < 0.20:
        return "moderately_common"
    return "common"


def summarize_ethnicity_context(rsid: str, gene: str, patient_ethnicity: Optional[str], freqs: Dict[str, Optional[float]]) -> str:
    parts = []
    if patient_ethnicity:
        pf = freqs.get(patient_ethnicity)
        if pf is not None:
            parts.append(f"In {patient_ethnicity}: {round(pf*100, 1)}%")
    # Provide a compact cross-pop summary (top 2 non-null)
    non_null = [(k, v) for k, v in freqs.items() if v is not None]
    non_null.sort(key=lambda kv: kv[1], reverse=True)
    if non_null:
        top = ", ".join([f"{k} {round(v*100, 1)}%" for k, v in non_null[:2]])
        parts.append(f"Across populations: {top}")
    return "; ".join(parts) or "Population frequency data unavailable"


