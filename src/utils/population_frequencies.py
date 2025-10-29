import json
import time
from pathlib import Path
from typing import Dict, Optional

import requests


ENSEMBL_VARIATION_URL = "https://rest.ensembl.org/variation/homo_sapiens/{rsid}?content-type=application/json"


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

        data = self._fetch_ensembl(rsid)
        if data is None:
            result = {"frequencies": _category_template(), "source": "unavailable"}
            self._save_cache(rsid, result)
            return result

        freqs = _category_template()
        for pop in data.get("populations", []):
            # Expect keys like {"name": "1000GENOMES:phase_3:EUR", "frequency": 0.15, ...}
            label = pop.get("name") or ""
            freq = pop.get("frequency")
            if freq is None:
                continue
            cat = _POPULATION_MAP.get(label)
            if not cat:
                continue
            # If multiple upstream sets provide a value, prefer the max (most inclusive) or keep first
            if freqs[cat] is None:
                freqs[cat] = float(freq)
            else:
                # keep the larger frequency to avoid under-reporting
                freqs[cat] = max(freqs[cat], float(freq))

        result = {"frequencies": freqs, "source": "Ensembl"}
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


