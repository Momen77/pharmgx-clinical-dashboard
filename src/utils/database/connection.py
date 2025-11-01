"""
Database Connection Management
"""

import os
import logging
from typing import Dict, Optional
import psycopg

# Try to import the Cloud SQL Connector
try:
    from google.cloud.sql.connector import Connector
    _connector = Connector()
except ImportError:
    _connector = None
    print("Warning: google-cloud-sql-connector not found. Cloud SQL connections will not work.")


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
        try:
            # Try Streamlit secrets first
            import streamlit as st
            return {
                "instance_connection_name": st.secrets.get("INSTANCE_CONNECTION_NAME", ""),
                "db_user": st.secrets.get("DB_USER", ""),
                "db_pass": st.secrets.get("DB_PASS", ""),
                "db_name": st.secrets.get("DB_NAME", "")
            }
        except Exception as e:
            # Fallback to environment variables
            self.logger.warning(f"Could not load Streamlit secrets, trying environment variables: {e}")
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
        
        if not self.db_params or not self.db_params.get("instance_connection_name"):
            self.logger.error("Database parameters not configured.")
            return None
        
        try:
            if self.connection_type == "cloud_sql" and _connector:
                self.connection = _connector.connect(
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

