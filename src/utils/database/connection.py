"""
Database Connection Management
"""

import os
import logging
from typing import Dict, Optional
import psycopg

# Try to import the Cloud SQL Connector (but don't instantiate yet)
try:
    from google.cloud.sql.connector import Connector
    _connector_available = True
except ImportError:
    _connector_available = False
    print("Warning: google-cloud-sql-connector not found. Cloud SQL connections will not work.")

# Global connector instance (created lazily only when needed)
_connector = None


def _get_connector():
    """Get or create the Cloud SQL Connector (lazy initialization)"""
    global _connector
    if _connector is None and _connector_available:
        try:
            _connector = Connector()
        except Exception as e:
            # Silently handle metadata service errors when not on GCP
            logging.getLogger(__name__).debug(f"Could not initialize Cloud SQL Connector: {e}")
            _connector = None
    return _connector


class DatabaseConnection:
    """Manages database connections for Cloud SQL"""
    
    def __init__(self, config):
        self.config = config
        self.db_enabled = config.database_enabled
        self.non_blocking = config.database_non_blocking
        self.connection_type = "cloud_sql"
        self.db_params = self._get_db_params()
        self.logger = logging.getLogger(__name__)
        self.connection = None
    
    def _get_db_params(self) -> Dict[str, str]:
        """Read database credentials from Streamlit secrets or environment variables"""
        # Try Streamlit secrets first
        try:
            import streamlit as st
            # Check for PostgreSQL connection first
            db_host = st.secrets.get("DB_HOST", "")
            if db_host:
                # Direct PostgreSQL connection
                self.connection_type = "postgresql"
                self.logger.debug("Using direct PostgreSQL connection from Streamlit secrets")
                return {
                    "db_host": db_host,
                    "db_port": st.secrets.get("DB_PORT", "5432"),
                    "db_user": st.secrets.get("DB_USER", ""),
                    "db_pass": st.secrets.get("DB_PASS", ""),
                    "db_name": st.secrets.get("DB_NAME", "")
                }
            else:
                # Cloud SQL connection
                return {
                    "instance_connection_name": st.secrets.get("INSTANCE_CONNECTION_NAME", ""),
                    "db_user": st.secrets.get("DB_USER", ""),
                    "db_pass": st.secrets.get("DB_PASS", ""),
                    "db_name": st.secrets.get("DB_NAME", "")
                }
        except Exception as e:
            # Fallback to environment variables
            self.logger.warning(f"Could not load Streamlit secrets, trying environment variables: {e}")
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
                
                # Build connection string
                conn_string = f"host={db_host} port={db_port} dbname={db_name} user={db_user} password={db_pass}"
                self.connection = psycopg.connect(conn_string)
                self.logger.info(f"✓ Connected to PostgreSQL at {db_host}:{db_port}")
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
        """Commit current transaction"""
        if self.connection:
            self.connection.commit()
    
    def rollback(self):
        """Rollback current transaction"""
        if self.connection:
            self.connection.rollback()

