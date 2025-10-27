"""Base API client with rate limiting and caching"""
import requests
import time
import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from retry import retry


class APIClient:
    """Base class for API clients with rate limiting and caching"""
    
    # Shared in-memory cache across all instances
    _memory_cache = {}
    _cache_stats = {"hits": 0, "misses": 0, "file_loads": 0}
    
    def __init__(self, base_url: str, rate_limit: int = 3, cache_dir: str = "data/cache"):
        """
        Initialize API client
        
        Args:
            base_url: Base URL for the API
            rate_limit: Maximum requests per second
            cache_dir: Directory for caching responses
        """
        self.base_url = base_url
        self.rate_limit = rate_limit
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.last_request_time = 0
        self.session = requests.Session()
        self._verbose_cache = False  # Set to True for debugging
    
    def _rate_limit_wait(self):
        """Wait if necessary to respect rate limits"""
        if self.rate_limit <= 0:
            return
        
        min_interval = 1.0 / self.rate_limit
        elapsed = time.time() - self.last_request_time
        
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        
        self.last_request_time = time.time()
    
    def _get_cache_key(self, url: str, params: Optional[Dict] = None) -> str:
        """Generate cache key from URL and parameters"""
        cache_str = url
        if params:
            cache_str += json.dumps(params, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """Get cache file path"""
        return self.cache_dir / f"{cache_key}.json"
    
    def _load_from_cache(self, cache_key: str, ttl_days: int = 30) -> Optional[Dict]:
        """Load response from cache if not expired (with in-memory caching)"""
        # Check in-memory cache first (fast!)
        if cache_key in self._memory_cache:
            cached_time, data = self._memory_cache[cache_key]
            if datetime.now() - cached_time <= timedelta(days=ttl_days):
                self._cache_stats["hits"] += 1
                return data
            else:
                # Expired in memory cache
                del self._memory_cache[cache_key]
        
        # Check disk cache
        cache_path = self._get_cache_path(cache_key)
        
        if not cache_path.exists():
            self._cache_stats["misses"] += 1
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cached = json.load(f)
            
            # Check if cache is expired
            cached_time = datetime.fromisoformat(cached['timestamp'])
            if datetime.now() - cached_time > timedelta(days=ttl_days):
                self._cache_stats["misses"] += 1
                return None
            
            # Store in memory cache for faster access
            self._memory_cache[cache_key] = (cached_time, cached['data'])
            self._cache_stats["file_loads"] += 1
            return cached['data']
        except (json.JSONDecodeError, KeyError, ValueError):
            self._cache_stats["misses"] += 1
            return None
    
    def _save_to_cache(self, cache_key: str, data: Any):
        """Save response to cache"""
        cache_path = self._get_cache_path(cache_key)
        
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2)
    
    @retry(tries=3, delay=2, backoff=2)
    def get(self, endpoint: str, params: Optional[Dict] = None, 
            headers: Optional[Dict] = None, use_cache: bool = True,
            cache_ttl_days: int = 30) -> Optional[Dict]:
        """
        Make GET request with rate limiting, caching, and retry logic
        
        Args:
            endpoint: API endpoint (relative to base_url)
            params: Query parameters
            headers: HTTP headers
            use_cache: Whether to use cache
            cache_ttl_days: Cache TTL in days
            
        Returns:
            Response data as dictionary or None on failure
        """
        url = f"{self.base_url}/{endpoint}" if not endpoint.startswith('http') else endpoint
        
        # Check cache first
        if use_cache:
            cache_key = self._get_cache_key(url, params)
            cached_data = self._load_from_cache(cache_key, cache_ttl_days)
            if cached_data is not None:
                # Only print if verbose mode enabled (reduces noise)
                if self._verbose_cache:
                    print(f"  [CACHE HIT] {endpoint}")
                return cached_data
        
        # Rate limiting
        self._rate_limit_wait()
        
        # Make request
        try:
            response = self.session.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json() if response.text else {}
            
            # Save to cache
            if use_cache:
                self._save_to_cache(cache_key, data)
                # Also store in memory cache
                self._memory_cache[cache_key] = (datetime.now(), data)
            
            return data
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                print(f"  [RATE LIMIT] {endpoint}: Too many requests, waiting...")
                time.sleep(5)  # Wait 5 seconds for rate limit
                raise  # Let retry decorator handle it
            elif e.response.status_code == 404:
                # 404s are common for missing resources - don't log as errors
                return None
            else:
                print(f"  [API ERROR] {endpoint}: {e}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"  [API ERROR] {endpoint}: {e}")
            return None
        except json.JSONDecodeError:
            print(f"  [JSON ERROR] {endpoint}: Invalid JSON response")
            return None

