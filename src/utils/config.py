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
        self.config_path = self._resolve_config_path(config_path)
        self.config = self._load_config()
    
    def _resolve_config_path(self, config_path: str) -> Path:
        """
        Resolve config.yaml path - try multiple locations
        
        Args:
            config_path: Initial config path
            
        Returns:
            Resolved Path object
        """
        # If absolute or exists, use as-is
        path = Path(config_path)
        if path.is_absolute() and path.exists():
            return path
        if path.exists():
            return path
        
        # Try common locations
        # From: pharmgx-clinical-dashboard/src/utils/config.py
        current_file = Path(__file__).resolve()
        candidates = [
            # Current directory
            Path.cwd() / config_path,
            # Dashboard root (go up from src/utils/)
            current_file.parent.parent.parent / config_path,
            # One more level up
            current_file.parent.parent.parent.parent / config_path,
            # Project root (in case we're deep in src/)
            current_file.parent.parent.parent.parent.parent / config_path,
        ]
        
        for candidate in candidates:
            if candidate.exists():
                return candidate
        
        # Last resort: return the original path (will raise FileNotFoundError later)
        return path
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-notation key
        Falls back to Streamlit secrets if config value is empty
        
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
                value = None
                break
        
        # If value is empty/None, try Streamlit secrets as fallback
        if not value or value == "":
            value = self._get_from_secrets(key)
        
        return value if value else default
    
    def _get_from_secrets(self, key: str) -> Any:
        """
        Try to get value from Streamlit secrets or secrets.toml
        
        Args:
            key: Configuration key (e.g., 'api.bioportal_api_key')
            
        Returns:
            Value from secrets or None
        """
        # Try Streamlit secrets first (when running in Streamlit)
        try:
            import streamlit as st
            # Import the exception class if available
            try:
                from streamlit.errors import StreamlitSecretNotFoundError
            except ImportError:
                # Fallback for older Streamlit versions
                StreamlitSecretNotFoundError = type('StreamlitSecretNotFoundError', (Exception,), {})
            
            # For nested keys like 'api.ncbi_email', try both:
            # 1. secrets['api']['ncbi_email']
            # 2. secrets['ncbi_email'] (flattened)
            keys = key.split('.')
            
            # Try nested access
            try:
                value = st.secrets
                for k in keys:
                    value = value[k]
                if value:
                    return value
            except (KeyError, TypeError, StreamlitSecretNotFoundError):
                pass
            
            # Try flattened key (e.g., 'bioportal_api_key' directly)
            if len(keys) > 1:
                flat_key = keys[-1]  # Get last part
                try:
                    value = st.secrets.get(flat_key)
                    if value:
                        return value
                except (KeyError, AttributeError, StreamlitSecretNotFoundError):
                    pass
        except ImportError:
            # Not in Streamlit context, try loading secrets.toml manually
            try:
                import toml
                secrets_path = self._find_secrets_toml()
                if secrets_path and secrets_path.exists():
                    with open(secrets_path, 'r') as f:
                        secrets = toml.load(f)
                    
                    # Try nested access
                    keys = key.split('.')
                    value = secrets
                    try:
                        for k in keys:
                            value = value[k]
                        if value:
                            return value
                    except (KeyError, TypeError):
                        pass
                    
                    # Try flattened key
                    if len(keys) > 1:
                        flat_key = keys[-1]
                        value = secrets.get(flat_key)
                        if value:
                            return value
            except:
                pass
        
        return None
    
    def _find_secrets_toml(self) -> Path:
        """Find secrets.toml file"""
        # Try common locations relative to config.yaml
        base_dir = self.config_path.parent
        candidates = [
            base_dir / ".streamlit" / "secrets.toml",
            base_dir / "src" / "pharmgx-clinical-dashboard" / ".streamlit" / "secrets.toml",
            base_dir.parent / ".streamlit" / "secrets.toml",
        ]
        
        for candidate in candidates:
            if candidate.exists():
                return candidate
        
        return None
    
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
    
    @property
    def database_enabled(self) -> bool:
        """Check if database loading is enabled"""
        return self.get('database.enabled', False)
    
    @property
    def database_non_blocking(self) -> bool:
        """Check if database loading should be non-blocking"""
        return self.get('database.non_blocking', True)


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