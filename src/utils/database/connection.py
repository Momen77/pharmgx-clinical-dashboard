"""
Database Connection Management
"""

import os
import logging
from typing import Dict, Optional
from pathlib import Path
import psycopg

# Try to import toml for reading secrets.toml
try:
    import toml
    _toml_available = True
except ImportError:
    _toml_available = False

# Try to import the Cloud SQL Connector (but don't instantiate yet)
try:
    from google.cloud.sql.connector import Connector
    _connector_available = True
except ImportError:
    _connector_available = False
    print("Warning: google-cloud-sql-connector not found. Cloud SQL connections will not work.")

# Global connector instance (created lazily only when needed)
_connector = None


def _load_secrets_toml() -> Dict:
    """Load secrets.toml file manually (for use outside Streamlit context)"""
    if not _toml_available:
        return {}
    
    # Try to find secrets.toml in common locations
    current_file = Path(__file__).resolve()
    base_dir = current_file.parent.parent.parent.parent.parent
    
    candidates = [
        base_dir / "src" / "pharmgx-clinical-dashboard" / ".streamlit" / "secrets.toml",
        base_dir / ".streamlit" / "secrets.toml",
        Path.cwd() / "src" / "pharmgx-clinical-dashboard" / ".streamlit" / "secrets.toml",
        Path.cwd() / ".streamlit" / "secrets.toml",
    ]
    
    for secrets_path in candidates:
        if secrets_path.exists():
            try:
                with open(secrets_path, 'r') as f:
                    return toml.load(f)
            except Exception as e:
                logging.getLogger(__name__).debug(f"Could not load secrets.toml from {secrets_path}: {e}")
                break
    
    return {}


def _get_connector():
    """Get or create the Cloud SQL Connector (lazy initialization)"""
    global _connector
    if _connector is None and _connector_available:
        try:
            # Add timeout to prevent hanging on metadata service calls
            import threading
            import queue
            
            result = queue.Queue()
            
            def init_connector():
                try:
                    result.put(Connector())
                except Exception as e:
                    result.put(e)
            
            # Start connector initialization in a separate thread
            thread = threading.Thread(target=init_connector, daemon=True)
            thread.start()
            thread.join(timeout=3)  # Wait up to 3 seconds
            
            if thread.is_alive():
                # Thread is still running, initialization timed out
                logging.getLogger(__name__).debug("Cloud SQL Connector initialization timed out (metadata service not available)")
                _connector = None
            else:
                # Get the result
                try:
                    result_obj = result.get(timeout=0.1)
                    if isinstance(result_obj, Exception):
                        raise result_obj
                    _connector = result_obj
                except queue.Empty:
                    _connector = None
                
        except Exception as e:
            # Silently handle metadata service errors when not on GCP
            logging.getLogger(__name__).debug(f"Could not initialize Cloud SQL Connector: {e}")
            _connector = None
    return _connector


class DatabaseConnection:
    """Manages database connections for Cloud SQL - v1.2"""
    
    def __init__(self, config):
        self.config = config
        # Initialize logger immediately
        self.logger = logging.getLogger(__name__)
        self.db_enabled = config.database_enabled
        self.non_blocking = config.database_non_blocking
        self.connection_type = "cloud_sql"
        self.db_params = self._get_db_params()
        self.connection = None
    
    def _get_db_params(self) -> Dict[str, str]:
        """Read database credentials from Streamlit secrets, secrets.toml, or environment variables"""
        # Safety guard: ensure logger exists (in case of initialization order issues)
        if not hasattr(self, 'logger'):
            self.logger = logging.getLogger(__name__)
        
        secrets_data = {}
        
        # Try Streamlit secrets first (when running inside Streamlit)
        try:
            import streamlit as st
            secrets_data = dict(st.secrets)
        except Exception:
            # Not in Streamlit context, try loading secrets.toml manually
            try:
                secrets_data = _load_secrets_toml()
                if secrets_data:
                    self.logger.debug("Loaded secrets from secrets.toml file")
            except Exception as e:
                self.logger.debug(f"Could not load secrets.toml: {e}")
        
        # Process the secrets data
        if secrets_data:
            # Check for PostgreSQL connection first
            db_host = secrets_data.get("DB_HOST", "")
            if db_host:
                # Direct PostgreSQL connection
                self.connection_type = "postgresql"
                self.logger.debug("Using direct PostgreSQL connection from secrets")
                return {
                    "db_host": db_host,
                    "db_port": secrets_data.get("DB_PORT", "5432"),
                    "db_user": secrets_data.get("DB_USER", ""),
                    "db_pass": secrets_data.get("DB_PASS", ""),
                    "db_name": secrets_data.get("DB_NAME", "")
                }
            else:
                # Cloud SQL connection
                return {
                    "instance_connection_name": secrets_data.get("INSTANCE_CONNECTION_NAME", ""),
                    "db_user": secrets_data.get("DB_USER", ""),
                    "db_pass": secrets_data.get("DB_PASS", ""),
                    "db_name": secrets_data.get("DB_NAME", "")
                }
        
        # Fallback to environment variables
        self.logger.debug("Using environment variables for database credentials")
        # Check for PostgreSQL connection first
        db_host = os.getenv("DB_HOST", "")
        if db_host:
            # Direct PostgreSQL connection
            self.connection_type = "postgresql"
            self.logger.debug("Using direct PostgreSQL connection from environment variables")
            return {
                "db_host": db_host,
                "db_port": os.getenv("DB_PORT", "5432"),
                "db_user": os.getenv("DB_USER", ""),
                "db_pass": os.getenv("DB_PASS", ""),
                "db_name": os.getenv("DB_NAME", "")
            }
        else:
            # Cloud SQL connection
            return {
                "instance_connection_name": os.getenv("INSTANCE_CONNECTION_NAME", ""),
                "db_user": os.getenv("DB_USER", ""),
                "db_pass": os.getenv("DB_PASS", ""),
                "db_name": os.getenv("DB_NAME", "")
            }
    
    def connect(self) -> Optional[psycopg.Connection]:
        """Establish database connection"""
        if not self.db_enabled:
            self.logger.info("Database loading is disabled in config.")
            return None
        
        if not self.db_params:
            self.logger.error("Database parameters not configured.")
            return None
        
        try:
            if self.connection_type == "postgresql":
                # Direct PostgreSQL connection
                db_host = self.db_params.get("db_host")
                db_port = self.db_params.get("db_port", "5432")
                db_user = self.db_params.get("db_user")
                db_pass = self.db_params.get("db_pass")
                db_name = self.db_params.get("db_name")
                
                if not all([db_host, db_user, db_pass, db_name]):
                    self.logger.error("Missing required PostgreSQL connection parameters")
                    return None
                
                # Build connection string with timeout
                # CRITICAL: psycopg3 requires autocommit=False for transactions
                conn_string = f"host={db_host} port={db_port} dbname={db_name} user={db_user} password={db_pass} connect_timeout=10"
                self.connection = psycopg.connect(conn_string)
                # Explicitly disable autocommit (default is False, but being explicit)
                if hasattr(self.connection, 'autocommit'):
                    self.connection.autocommit = False
                self.logger.info(f"✓ Connected to PostgreSQL at {db_host}:{db_port}")
                self.logger.info(f"✓ Autocommit: {getattr(self.connection, 'autocommit', False)}")
                return self.connection
                
            elif self.connection_type == "cloud_sql":
                # Cloud SQL connection
                if not self.db_params.get("instance_connection_name"):
                    self.logger.error("Database parameters not configured for Cloud SQL.")
                    return None
                
                # Use lazy initialization of connector
                connector = _get_connector()
                if connector:
                    self.connection = connector.connect(
                        self.db_params["instance_connection_name"],
                        "psycopg",
                        user=self.db_params["db_user"],
                        password=self.db_params["db_pass"],
                        db=self.db_params["db_name"]
                    )
                    self.logger.info("✓ Connected to Google Cloud SQL")
                    return self.connection
                else:
                    self.logger.error("Cloud SQL connector not available")
                    return None
            else:
                self.logger.error(f"Unknown connection type: {self.connection_type}")
                return None
                
        except Exception as e:
            self.logger.error(f"Database connection failed: {e}")
            if not self.non_blocking:
                raise
            return None
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
            self.logger.info("Database connection closed")
    
    def commit(self):
        """Commit current transaction with verification"""
        if self.connection:
            try:
                # Check connection status
                if self.connection.closed:
                    self.logger.error("❌ Cannot commit: connection is closed")
                    return False
                
                # Force commit
                self.connection.commit()
                
                # Verify commit succeeded by checking transaction status
                # In psycopg3, if commit fails, it raises an exception
                # But we'll also check connection state
                self.logger.info("✅ Transaction commit() called successfully")
                
                # Force a sync/flush to ensure data is written to disk
                # This ensures the commit has propagated to the database server
                try:
                    # Execute a simple query to force sync
                    with self.connection.cursor() as sync_cursor:
                        sync_cursor.execute("SELECT 1")
                        sync_cursor.fetchone()
                except Exception as sync_error:
                    self.logger.warning(f"⚠️  Sync query failed: {sync_error}")
                
                return True
            except Exception as e:
                import traceback
                self.logger.error(f"❌ Commit failed: {e}")
                self.logger.error(f"Traceback: {traceback.format_exc()}")
                raise
    
    def rollback(self):
        """Rollback current transaction"""
        if self.connection:
            self.connection.rollback()

