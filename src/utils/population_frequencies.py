import json
import time
from pathlib import Path
from typing import Dict, Optional

import requests


ENSEMBL_VARIATION_URL = "https://rest.ensembl.org/variation/homo_sapiens/{rsid}?content-type=application/json"
GNOMAD_API_URL = "https://gnomad.broadinstitute.org/api"
DBSNP_SUMMARY_URL = "https://api.ncbi.nlm.nih.gov/variation/v0/beta/refsnp/{rsid_num}"


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

    def get_population_frequencies(self, rsid: str) -> Dict:
        if not self.enabled or not rsid or not rsid.startswith("rs"):
            return {"frequencies": _category_template(), "source": "disabled"}

        cached = self._load_cache(rsid)
        if cached is not None:
            return cached

        source = None
        freqs = _category_template()

        # Primary: Ensembl
        data = self._fetch_ensembl(rsid)
        if data is not None:
            source = "Ensembl"
            for pop in data.get("populations", []):
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

        # Secondary: gnomAD GraphQL (only if still all None)
        if source is None or all(v is None for v in freqs.values()):
            gnomad = self._fetch_gnomad(rsid)
            if gnomad is not None:
                source = "gnomAD"
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
        url = ENSEMBL_VARIATION_URL.format(rsid=rsid)
        try:
            resp = requests.get(url, headers={"User-Agent": "pgx-kg/ethnicity-af"}, timeout=15)
            if resp.status_code == 429:
                time.sleep(1.0)
                resp = requests.get(url, headers={"User-Agent": "pgx-kg/ethnicity-af"}, timeout=15)
            if resp.ok:
                return resp.json()
        except Exception:
            return None
        return None

    def _fetch_gnomad(self, rsid: str) -> Optional[Dict[str, list]]:
        """Fetch population AFs from gnomAD GraphQL and map to canonical buckets.
        Returns a dict of canonical bucket -> list[float].
        """
        try:
            query = {
                "query": (
                    "query($rsid: String!) { \n"
                    "  variant(variantId: $rsid) { \n"
                    "    genome { ac af an populations { id ac an ac_hom } } \n"
                    "    exome { ac af an populations { id ac an ac_hom } } \n"
                    "  } \n"
                    "}"
                ),
                "variables": {"rsid": rsid}
            }
            resp = requests.post(GNOMAD_API_URL, json=query, headers={"User-Agent": "pgx-kg/ethnicity-af"}, timeout=20)
            if not resp.ok:
                return None
            data = resp.json().get("data", {})
            variant = data.get("variant") or {}
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
            return buckets
        except Exception:
            return None

    def _fetch_dbsnp(self, rsid: str) -> Optional[Dict[str, float]]:
        """Fetch coarse AFs from dbSNP summary if available."""
        try:
            if not rsid.startswith("rs"):
                return None
            num = rsid.replace("rs", "")
            url = DBSNP_SUMMARY_URL.format(rsid_num=num)
            resp = requests.get(url, headers={"User-Agent": "pgx-kg/ethnicity-af"}, timeout=15)
            if not resp.ok:
                return None
            data = resp.json()
            # dbSNP schema is complex; try to aggregate if present
            # We look for "primary_snapshot_data" -> "allele_annotations" -> "frequency" style entries
            out = {}
            try:
                psd = data.get("primary_snapshot_data") or {}
                anns = psd.get("allele_annotations") or []
                for ann in anns:
                    for freq in (ann.get("frequency") or []):
                        # freq example may include study_name like "1000Genomes" and pop like "AFR"
                        pop = freq.get("population") or {}
                        pop_code = (pop.get("name") or "").upper()
                        af = freq.get("allele_count")
                        an = freq.get("allele_number")
                        if isinstance(af, int) and isinstance(an, int) and an > 0:
                            val = af / an
                            if pop_code in ("AFR", "EAS", "EUR", "AMR"):
                                # Keep the max seen
                                if pop_code not in out or val > out[pop_code]:
                                    out[pop_code] = val
            except Exception:
                pass
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


