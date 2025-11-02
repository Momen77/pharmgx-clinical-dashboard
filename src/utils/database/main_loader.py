"""
Main Database Loader - Orchestrates all submodules
Complete Database Loader for Pharmacogenomics Knowledge Base + Patient Data
✅ SCHEMA-ALIGNED with complete_enhanced_schema.sql
"""

import logging
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path

from .connection import DatabaseConnection
from .reference_data import ReferenceDataLoader
from .patient_core import PatientCoreLoader
from .patient_clinical import PatientClinicalLoader
from .patient_variants import PatientVariantsLoader
from .linking_tables import LinkingTablesLoader
from .literature import LiteratureLoader
from .summaries import SummariesLoader


class DatabaseLoader:
    """
    ✅ SCHEMA-ALIGNED Database Loader
    
    Modular structure for easier maintenance and testing:
    - connection.py: Database connection management
    - reference_data.py: SNOMED, genes, drugs, variants, PharmGKB annotations
    - patient_core.py: Patients and demographics tables
    - patient_clinical.py: Conditions, medications, organ function, lifestyle
    - patient_variants.py: Patient variants and pharmacogenomics profiles
    - linking_tables.py: Medication-variant links, conflicts, ethnicity adjustments
    - literature.py: Publications and linking tables
    - summaries.py: Clinical and processing summaries
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the loader with configuration"""
        from utils.config import get_config
        self.config = get_config(config_path)
        
        # Connection manager
        self.db_connection = DatabaseConnection(self.config)
        
        # Submodule loaders (initialized later with shared caches)
        self.reference_loader = None
        self.patient_core_loader = None
        self.patient_clinical_loader = None
        self.patient_variants_loader = None
        self.linking_loader = None
        self.literature_loader = None
        self.summaries_loader = None
        
        self.logger = self._get_logger()
    
    def _get_logger(self) -> logging.Logger:
        """Configure logger"""
        logger = logging.getLogger(__name__)
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def load_patient_profile(self, profile: Dict) -> Dict[str, any]:
        """
        ✅ SCHEMA-ALIGNED: Load complete patient profile into database
        
        5-Phase Loading Strategy:
        Phase 1: Reference Data (SNOMED, genes, drugs, variants, PharmGKB)
        Phase 2: Patient Core (patients, demographics)
        Phase 3: Patient Clinical (conditions, medications, organ function, lifestyle)
        Phase 4: Patient Variants (pharmacogenomics profiles, patient variants)
        Phase 5: Linking & Summaries (medication links, conflicts, literature, summaries)
        
        Returns:
            Dict with status: {'success': bool, 'error': str, 'records_inserted': int}
        """
        if not self.db_connection.db_enabled:
            return {'success': False, 'error': 'Database loading is disabled in config'}
        
        start_time = datetime.now()
        connection = None
        total_records = 0
        
        try:
            # Connect to database
            connection = self.db_connection.connect()
            if not connection:
                return {'success': False, 'error': 'Could not establish database connection'}
            
            cursor = connection.cursor()
            
            # Initialize submodule loaders
            self.reference_loader = ReferenceDataLoader()
            self.patient_core_loader = PatientCoreLoader()
            self.patient_clinical_loader = PatientClinicalLoader(
                inserted_drugs=self.reference_loader.inserted_drugs
            )
            self.patient_variants_loader = PatientVariantsLoader()
            self.linking_loader = LinkingTablesLoader(
                inserted_drugs=self.reference_loader.inserted_drugs,
                inserted_pharmgkb_annotations=self.reference_loader.inserted_pharmgkb_annotations
            )
            self.literature_loader = LiteratureLoader()
            self.summaries_loader = SummariesLoader()
            
            # ✅ PHASE 1: Load Reference Data
            self.logger.info("📦 PHASE 1: Loading reference data...")
            total_records += self.reference_loader.load_all(cursor, profile)
            
            # ✅ PHASE 2: Load Patient Core Data
            self.logger.info("👤 PHASE 2: Loading patient core data...")
            total_records += self.patient_core_loader.load_all(cursor, profile)
            
            # ✅ PHASE 3: Load Patient Clinical Data
            self.logger.info("🏥 PHASE 3: Loading patient clinical data...")
            total_records += self.patient_clinical_loader.load_all(cursor, profile)
            
            # ✅ PHASE 4: Load Patient Variants
            self.logger.info("🧬 PHASE 4: Loading patient variants...")
            total_records += self.patient_variants_loader.load_all(cursor, profile)
            
            # ✅ PHASE 5: Load Linking Tables & Summaries
            self.logger.info("🔗 PHASE 5: Loading linking tables and summaries...")
            total_records += self.linking_loader.load_all(cursor, profile)
            total_records += self.literature_loader.load_all(cursor, profile)
            total_records += self.summaries_loader.load_all(cursor, profile)
            
            # Get patient_id for verification
            patient_id = profile.get('patient_id', '')
            
            # Commit transaction EXPLICITLY
            self.logger.info("🔄 Committing transaction...")
            self.db_connection.commit()
            self.logger.info("✅ Commit called successfully")
            
            # CRITICAL: Verify data was actually committed by reading it back
            verify_cursor = connection.cursor()
            try:
                # Check patients table
                verify_cursor.execute("SELECT COUNT(*) FROM patients WHERE patient_id = %s", (patient_id,))
                patient_count = verify_cursor.fetchone()[0]
                
                # Check total records in patients table
                verify_cursor.execute("SELECT COUNT(*) FROM patients")
                total_patients = verify_cursor.fetchone()[0]
                
                # Check demographics
                verify_cursor.execute("SELECT COUNT(*) FROM demographics WHERE patient_id = %s", (patient_id,))
                demo_count = verify_cursor.fetchone()[0]
                
                self.logger.info(f"🔍 Verification: Found {patient_count} record(s) for patient {patient_id}")
                self.logger.info(f"🔍 Verification: Total patients in database: {total_patients}")
                self.logger.info(f"🔍 Verification: Demographics records: {demo_count}")
                
                if patient_count == 0 and total_records > 0:
                    self.logger.error("❌ CRITICAL: Commit reported success but no data found in database!")
                    # Check if it's a timing issue - wait and retry
                    import time
                    time.sleep(1)
                    verify_cursor.execute("SELECT COUNT(*) FROM patients WHERE patient_id = %s", (patient_id,))
                    patient_count_retry = verify_cursor.fetchone()[0]
                    if patient_count_retry == 0:
                        self.logger.error("❌ Data verification failed after retry - commit may have rolled back silently")
                        # Log transaction status
                        verify_cursor.execute("SELECT txid_current()")
                        tx_id = verify_cursor.fetchone()[0]
                        self.logger.info(f"🔍 Current transaction ID: {tx_id}")
                    else:
                        self.logger.info(f"✅ Data found after 1s delay - timing issue confirmed")
                elif patient_count > 0:
                    self.logger.info(f"✅ Data verification PASSED - {patient_count} patient record(s) found")
                
            except Exception as verify_error:
                import traceback
                self.logger.error(f"❌ Verification query failed: {verify_error}")
                self.logger.error(f"Traceback: {traceback.format_exc()}")
            finally:
                verify_cursor.close()
                cursor.close()
            
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"✅ Database loading complete: {total_records} records in {duration:.2f}s")
            
            return {
                'success': True,
                'records_inserted': total_records,
                'duration_seconds': duration,
                'patient_id': profile.get('patient_id')
            }
        
        except Exception as e:
            import traceback
            self.logger.error(f"❌ Database loading failed: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            if connection:
                try:
                    self.db_connection.rollback()
                    self.logger.info("🔄 Transaction rolled back")
                except Exception as rollback_error:
                    self.logger.error(f"Failed to rollback: {rollback_error}")
            
            if self.db_connection.non_blocking:
                return {
                    'success': False,
                    'error': str(e),
                    'non_blocking': True
                }
            else:
                raise
        
        finally:
            # Keep connection open briefly to ensure commit propagates
            import time
            time.sleep(0.3)  # Small delay to ensure commit is fully processed
            self.db_connection.close()
            self.logger.info("🔒 Database connection closed")
    
    def close(self):
        """Close database connection"""
        self.db_connection.close()


# Backward compatibility
ComprehensiveDatabaseLoader = DatabaseLoader

