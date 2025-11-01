"""Configuration management for PGx-KG"""
import yaml
from pathlib import Path
from typing import Dict, Any


class Config:
    """Loads and manages configuration from config.yaml"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize configuration
        
        Args:
            config_path: Path to config.yaml file
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-notation key
        
        Args:
            key: Configuration key (e.g., 'api.ncbi_email')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    @property
    def ncbi_email(self) -> str:
        """Get NCBI email"""
        return self.get('api.ncbi_email', 'your_email@example.com')
    
    @property
    def ncbi_api_key(self) -> str:
        """Get NCBI API key (optional)"""
        return self.get('api.ncbi_api_key')
    
    @property
    def bioportal_api_key(self) -> str:
        """Get BioPortal API key"""
        return self.get('api.bioportal_api_key')
    
    @property
    def rate_limits(self) -> Dict[str, int]:
        """Get rate limits for all APIs"""
        return self.get('rate_limits', {})
    
    @property
    def cache_enabled(self) -> bool:
        """Check if caching is enabled"""
        return self.get('cache.enabled', True)
    
    @property
    def cache_ttl_days(self) -> int:
        """Get cache TTL in days"""
        return self.get('cache.ttl_days', 30)
    
    @property
    def max_variants(self) -> int:
        """Get maximum variants per gene"""
        return self.get('output.max_variants_per_gene', 50)


# Singleton instance
_config_instance = None


def get_config(config_path: str = None) -> Config:
    """
    Get singleton Config instance
    
    Args:
        config_path: Optional path to config file
        
    Returns:
        Config instance
    """
    global _config_instance
    if _config_instance is None:
        if config_path is None:
            # Try to find config.yaml in common locations
            # Start from utils/config.py: src/pharmgx-clinical-dashboard/src/utils/config.py
            # Go up 5 levels to reach project root: utils -> src -> pharmgx-clinical-dashboard -> src -> root
            base_dir = Path(__file__).parent.parent.parent.parent.parent
            config_path = base_dir / "config.yaml"
            if not config_path.exists():
                # Try src/pharmgx-clinical-dashboard (old location)
                config_path = base_dir / "src" / "pharmgx-clinical-dashboard" / "config.yaml"
            if not config_path.exists():
                # Try current working directory
                import os
                config_path = Path(os.getcwd()) / "config.yaml"
        try:
            _config_instance = Config(str(config_path)) if config_path else Config()
        except FileNotFoundError:
            # Fallback: try relative path from current directory
            import os
            fallback_path = Path(os.getcwd()) / "config.yaml"
            if fallback_path.exists():
                _config_instance = Config(str(fallback_path))
            else:
                raise FileNotFoundError(f"Could not find config.yaml. Tried: {config_path}, {fallback_path}")
    return _config_instance