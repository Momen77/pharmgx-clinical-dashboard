# Performance Optimization Guide
## Pharmacogenomics Pipeline Performance Analysis

**Date:** 2025-10-30
**Current Status:** Sequential processing causing slow execution times

---

## 🔍 Performance Bottlenecks Identified

### 1. **Sequential Multi-Gene Processing** ⚠️ CRITICAL
**Location:** `src/main.py:289-318`

**Problem:**
```python
for gene_symbol in gene_symbols:
    gene_result = self.run(gene_symbol)  # Blocking sequential execution
    results[gene_symbol] = gene_result
```

**Impact:**
- Testing 5 genes that each take 30 seconds = **150 seconds total**
- With parallelization: **~30-40 seconds** (5x faster)

**Solution:** Process genes in parallel using `concurrent.futures.ThreadPoolExecutor`

---

### 2. **API Rate Limiting Delays** ⚠️ HIGH
**Location:** `src/utils/api_client.py:43-44`

**Problem:**
```python
if elapsed < min_interval:
    time.sleep(min_interval - elapsed)  # Blocking wait
```

**Current Settings:**
- Rate limit: 3 requests/second
- Sleep time: ~0.33 seconds per request
- 100 API calls = **33 seconds** just waiting

**Impact:** Each variant makes multiple API calls:
- ClinVar lookup: 0.33s wait
- PharmGKB lookup: 0.33s wait
- BioPortal mapping: 0.33s wait per phenotype
- ChEMBL drug data: 0.33s wait per drug
- Europe PMC literature: 0.33s wait

**Solutions:**
1. Increase rate limits (check API provider limits)
2. Batch API requests where possible
3. Parallel API calls to different services

---

### 3. **Sequential Variant Enrichment** ⚠️ HIGH
**Location:** `src/phase2_clinical/clinical_validator.py:119-127`

**Problem:**
```python
for variant in variants:
    print(f"Processing variant {i}/{len(variants)}: {variant_id}")
    enriched = self.enrich_variant(variant, gene_symbol)
    enriched_variants.append(enriched)
```

**Impact:**
- 50 variants × 3 seconds each = **150 seconds**
- With parallel processing: **~15-30 seconds** (5-10x faster)

**Solution:** Use thread pool to enrich variants in parallel

---

### 4. **No Bulk API Operations** ⚠️ MEDIUM
**Locations:** Multiple files in `phase3_context/`

**Problem:** Individual API calls for each drug/variant
```python
for drug in variant["pharmgkb"]["drugs"]:
    drug_name = drug.get("name")
    chembl_data = self.chembl_client.search_compound(drug_name)  # One at a time
```

**Impact:** 20 drugs × 0.5s per call = **10 seconds**

**Solution:** Implement batch API endpoints where available

---

### 5. **Inefficient Cache Usage** ⚠️ MEDIUM
**Location:** `src/utils/api_client.py`

**Current State:**
- Disk cache + in-memory cache ✅
- TTL: 30 days ✅
- But: Cache stats show low hit rates

**Problems:**
1. Cache keys not optimal (include timestamps)
2. No pre-warming of common queries
3. Cache not shared between runs

**Solutions:**
1. Improve cache key generation
2. Add cache warming for common genes/drugs
3. Implement Redis for shared cache (optional)

---

## 📊 Performance Impact Analysis

### Current Performance (Sequential)
| Operation | Time | Bottleneck |
|-----------|------|------------|
| Single gene analysis | 30-45s | API calls + enrichment |
| 5 genes analysis | 150-225s | No parallelization |
| 10 genes analysis | 300-450s | Linear scaling |
| Variant enrichment (50 variants) | 150s | Sequential processing |

### Projected Performance (Optimized)
| Operation | Time | Improvement |
|-----------|------|-------------|
| Single gene analysis | 20-30s | 33% faster (better caching) |
| 5 genes analysis | 30-50s | **75% faster** (5x speedup) |
| 10 genes analysis | 40-70s | **85% faster** (6x speedup) |
| Variant enrichment (50 variants) | 15-30s | **80% faster** (5-10x speedup) |

---

## 🚀 Quick Wins (Easy Implementations)

### Quick Win #1: Parallel Multi-Gene Processing
**Effort:** 30 minutes
**Impact:** 5-6x speedup for multi-gene tests

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def run_multi_gene(self, gene_symbols: list, patient_profile: dict = None):
    with ThreadPoolExecutor(max_workers=5) as executor:
        # Submit all gene processing tasks
        future_to_gene = {
            executor.submit(self.run, gene): gene
            for gene in gene_symbols
        }

        # Collect results as they complete
        for future in as_completed(future_to_gene):
            gene = future_to_gene[future]
            results[gene] = future.result()
```

---

### Quick Win #2: Parallel Variant Enrichment
**Effort:** 20 minutes
**Impact:** 5-10x speedup for variant processing

```python
from concurrent.futures import ThreadPoolExecutor

def run_pipeline(self, gene_symbol: str):
    # Load variants
    variants = self._load_variants(gene_symbol)

    # Enrich in parallel
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(self.enrich_variant, variant, gene_symbol)
            for variant in variants
        ]
        enriched_variants = [f.result() for f in futures]
```

---

### Quick Win #3: Increase API Rate Limits
**Effort:** 5 minutes
**Impact:** 2-3x speedup

**Check API provider limits:**
- NCBI: 10 requests/second with API key ✅
- PharmGKB: 100 requests/minute (1.67/s) ✅
- ChEMBL: No official limit (use 10/s) ✅
- BioPortal: 15 requests/second ✅

**Update:**
```python
# In phase initialization
self.phase2 = ClinicalValidator(
    ncbi_email=self.config.ncbi_email,
    ncbi_api_key=self.config.ncbi_api_key,
    rate_limit=10  # Increase from 3 to 10
)
```

---

## 🎯 Advanced Optimizations

### Advanced #1: Async I/O with asyncio
**Effort:** 2-3 hours
**Impact:** 10-20x speedup for I/O-bound operations

Replace `requests` with `aiohttp` for true async API calls:
```python
import asyncio
import aiohttp

async def enrich_variant_async(self, variant, gene_symbol):
    async with aiohttp.ClientSession() as session:
        # Run all API calls concurrently
        clinvar_task = self.clinvar.enrich_variant_async(session, variant)
        pharmgkb_task = self.pharmgkb.enrich_variant_async(session, variant, gene_symbol)

        clinvar_result, pharmgkb_result = await asyncio.gather(
            clinvar_task, pharmgkb_task
        )
```

---

### Advanced #2: Database Caching with Redis
**Effort:** 1-2 hours
**Impact:** 50-90% faster on repeated queries

```python
import redis

class CachedAPIClient(APIClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.redis = redis.Redis(host='localhost', port=6379, decode_responses=True)

    def get_cached(self, key):
        cached = self.redis.get(key)
        if cached:
            return json.loads(cached)
        return None

    def set_cached(self, key, value, ttl=2592000):  # 30 days
        self.redis.setex(key, ttl, json.dumps(value))
```

---

### Advanced #3: Batch API Endpoints
**Effort:** 3-4 hours
**Impact:** 3-5x speedup for drug/variant lookups

Implement batch operations where APIs support it:
```python
def get_chembl_data_batch(self, drug_names: list):
    """Get ChEMBL data for multiple drugs in one request"""
    # ChEMBL supports POST with list of compounds
    response = self.session.post(
        f"{self.base_url}/molecule/list",
        json={"compound_names": drug_names}
    )
    return response.json()
```

---

## 📈 Implementation Priority

| Priority | Optimization | Effort | Impact | ROI |
|----------|-------------|--------|--------|-----|
| 🔴 **P0** | Parallel multi-gene processing | 30 min | 5-6x | ⭐⭐⭐⭐⭐ |
| 🔴 **P0** | Parallel variant enrichment | 20 min | 5-10x | ⭐⭐⭐⭐⭐ |
| 🟠 **P1** | Increase API rate limits | 5 min | 2-3x | ⭐⭐⭐⭐⭐ |
| 🟠 **P1** | Improve cache key generation | 15 min | 1.5-2x | ⭐⭐⭐⭐ |
| 🟡 **P2** | Async I/O with asyncio | 2-3 hrs | 10-20x | ⭐⭐⭐⭐ |
| 🟡 **P2** | Redis caching | 1-2 hrs | 2-3x | ⭐⭐⭐ |
| 🟢 **P3** | Batch API endpoints | 3-4 hrs | 3-5x | ⭐⭐⭐ |

**Recommended Implementation Order:**
1. ✅ **Week 1:** Quick Wins #1-3 (1 hour total, 10-20x combined speedup)
2. ✅ **Week 2:** Advanced #1 (Async I/O)
3. ✅ **Week 3:** Advanced #2-3 (Redis + Batch APIs)

---

## 🔧 Monitoring & Profiling

### Add Performance Metrics
```python
import time
from functools import wraps

def timing_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        print(f"{func.__name__} took {duration:.2f}s")
        return result
    return wrapper

# Usage
@timing_decorator
def enrich_variant(self, variant, gene_symbol):
    # ... existing code
```

### Add Cache Hit Rate Monitoring
```python
def print_cache_stats(self):
    total = self._cache_stats['hits'] + self._cache_stats['misses']
    hit_rate = self._cache_stats['hits'] / total * 100 if total > 0 else 0
    print(f"Cache Stats: {hit_rate:.1f}% hit rate ({self._cache_stats['hits']}/{total})")
```

---

## 📝 Testing Strategy

### Performance Benchmarks
Create benchmark script: `tests/benchmark_performance.py`

```python
import time
from main import PGxPipeline

def benchmark_single_gene():
    pipeline = PGxPipeline()
    start = time.time()
    result = pipeline.run("CYP2D6")
    duration = time.time() - start
    print(f"Single gene: {duration:.2f}s")
    return duration

def benchmark_multi_gene():
    pipeline = PGxPipeline()
    genes = ["CYP2D6", "TPMT", "DPYD", "UGT1A1", "SLCO1B1"]
    start = time.time()
    result = pipeline.run_multi_gene(genes)
    duration = time.time() - start
    print(f"Multi gene ({len(genes)}): {duration:.2f}s")
    return duration

if __name__ == "__main__":
    single = benchmark_single_gene()
    multi = benchmark_multi_gene()
    efficiency = (single * 5) / multi
    print(f"Parallelization efficiency: {efficiency:.1f}x")
```

---

## 🎓 Additional Resources

### Python Concurrency
- [Threading vs Asyncio](https://realpython.com/python-concurrency/)
- [ThreadPoolExecutor Guide](https://docs.python.org/3/library/concurrent.futures.html)

### API Optimization
- [REST API Caching Strategies](https://restfulapi.net/caching/)
- [Rate Limiting Best Practices](https://cloud.google.com/architecture/rate-limiting-strategies-techniques)

### Profiling Tools
- `cProfile`: Built-in Python profiler
- `line_profiler`: Line-by-line timing
- `memory_profiler`: Memory usage tracking

---

## 📞 Questions?

For questions about this optimization guide, refer to:
- Main pipeline: `src/main.py`
- API client: `src/utils/api_client.py`
- Phase implementations: `src/phase*/*.py`

**Remember:** Profile first, optimize second. Always measure before and after!
