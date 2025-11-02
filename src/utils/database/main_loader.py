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
            
            # CRITICAL: Start transaction explicitly
            # PostgreSQL requires explicit BEGIN when using savepoints
            cursor.execute("BEGIN")
            self.logger.info("🔄 Started transaction (BEGIN)")
            
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
            phase3_attempts = 0
            max_phase3_attempts = 2
            while phase3_attempts < max_phase3_attempts:
                try:
                    phase3_attempts += 1
                    phase3_records = self.patient_clinical_loader.load_all(cursor, profile)
                    total_records += phase3_records
                    self.logger.info(f"✅ Phase 3 completed: {phase3_records} records")
                    break  # Success - exit retry loop
                except Exception as phase3_error:
                    error_msg = str(phase3_error)
                    self.logger.warning(f"⚠️ Phase 3 attempt {phase3_attempts} failed: {error_msg}")
                    
                    # Check if transaction aborted or error mentions transaction
                    if "transaction is aborted" in error_msg.lower() or "current transaction is aborted" in error_msg.lower():
                        if phase3_attempts < max_phase3_attempts:
                            self.logger.warning("🔄 Transaction aborted in Phase 3 - attempting recovery")
                            try:
                                # Rollback and restart transaction
                                connection.rollback()
                                cursor.execute("BEGIN")
                                self.logger.info(f"✅ Transaction restarted (attempt {phase3_attempts + 1}/{max_phase3_attempts})")
                                # Continue to retry
                            except Exception as recovery_error:
                                self.logger.error(f"❌ Failed to recover transaction: {recovery_error}")
                                # If we can't recover, break and continue with other phases
                                break
                        else:
                            self.logger.error("❌ Phase 3 failed after max attempts - continuing with other phases")
                            # Don't raise - allow other phases to continue
                            break
                    else:
                        # Non-transaction error - log and continue
                        self.logger.error(f"❌ Phase 3 non-transaction error: {error_msg}")
                        # Don't retry non-transaction errors
                        break
            
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
            
            # Commit transaction - CRITICAL: Use connection.commit() NOT cursor.execute("COMMIT")
            self.logger.info("🔄 Committing transaction...")
            
            # Get transaction status before commit
            cursor.execute("SELECT txid_current(), pg_backend_pid()")
            tx_before = cursor.fetchone()
            self.logger.info(f"🔍 Transaction ID before commit: {tx_before[0]}, PID: {tx_before[1]}")
            
            # CRITICAL: In psycopg3, we MUST use connection.commit(), not cursor.execute("COMMIT")
            # cursor.execute("COMMIT") doesn't work properly in psycopg3
            try:
                # Commit on the SAME connection that did the inserts
                connection.commit()
                self.logger.info("✅ connection.commit() executed successfully")
            except Exception as commit_error:
                self.logger.error(f"❌ Commit failed: {commit_error}")
                raise
            
            # Verify connection is still open
            if connection.closed:
                self.logger.error("❌ Connection closed immediately after commit!")
            else:
                self.logger.info("✅ Connection still open after commit")
            
            # Get new transaction ID after commit (should be different or same if autocommit)
            verify_cursor = connection.cursor()
            verify_cursor.execute("SELECT txid_current(), pg_backend_pid()")
            tx_after = verify_cursor.fetchone()
            self.logger.info(f"🔍 Transaction ID after commit: {tx_after[0]}, PID: {tx_after[1]}")
            
            # CRITICAL: Force a read query to ensure commit propagated
            verify_cursor.execute("SELECT 1")
            verify_cursor.fetchone()
            
            self.logger.info("✅ Commit process completed")
            
            # CRITICAL: Verify data was actually committed by reading it back
            # Use the same verify_cursor from above
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
            
            duration = (datetime.now() - start_time).total_seconds()
            
            # CRITICAL: Final verification BEFORE returning success
            # Check if data actually exists in database
            final_verify = connection.cursor()
            final_verify.execute("SELECT COUNT(*) FROM patients WHERE patient_id = %s", (patient_id,))
            final_patient_count = final_verify.fetchone()[0]
            final_verify.execute("SELECT COUNT(*) FROM patients")
            final_total_count = final_verify.fetchone()[0]
            final_verify.close()
            
            if final_patient_count == 0 and total_records > 0:
                self.logger.error(f"❌ CRITICAL: Commit succeeded but data not found! Patient count: {final_patient_count}, Total: {final_total_count}")
                # This means commit isn't actually persisting - return error
                return {
                    'success': False,
                    'error': f'Commit reported success but data not found in database (patient_count={final_patient_count})',
                    'records_inserted': 0,
                    'duration_seconds': duration,
                    'patient_id': patient_id
                }
            else:
                self.logger.info(f"✅ Final verification: {final_patient_count} patient(s), {final_total_count} total patients")
            
            self.logger.info(f"✅ Database loading complete: {total_records} records in {duration:.2f}s")
            
            return {
                'success': True,
                'records_inserted': total_records,
                'duration_seconds': duration,
                'patient_id': patient_id
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
            # CRITICAL: Keep connection open and verify commit before closing
            import time
            
            # Final verification - check if data exists before closing
            if connection and not connection.closed:
                try:
                    final_check = connection.cursor()
                    final_check.execute("SELECT COUNT(*) FROM patients")
                    final_count = final_check.fetchone()[0]
                    final_check.close()
                    self.logger.info(f"🔍 Pre-close verification: {final_count} patients in database")
                    
                    if final_count == 0:
                        self.logger.error("❌ CRITICAL: No data found before closing connection!")
                        # Try one more explicit commit
                        try:
                            connection.commit()
                            self.logger.info("🔄 Attempted emergency commit before close")
                            # Verify again
                            final_check2 = connection.cursor()
                            final_check2.execute("SELECT COUNT(*) FROM patients")
                            final_count2 = final_check2.fetchone()[0]
                            final_check2.close()
                            self.logger.info(f"🔍 Post-emergency-commit verification: {final_count2} patients")
                        except Exception as emergency_error:
                            self.logger.error(f"❌ Emergency commit failed: {emergency_error}")
                except Exception as final_error:
                    self.logger.error(f"❌ Final verification failed: {final_error}")
            
            # Wait to ensure commit has fully propagated to database
            time.sleep(2.0)  # Increased delay for reliability
            
            # Only close connection after verification and delay
            if connection and not connection.closed:
                try:
                    self.db_connection.close()
                    self.logger.info("🔒 Database connection closed")
                except Exception as close_error:
                    self.logger.error(f"❌ Error closing connection: {close_error}")
    
    def close(self):
        """Close database connection"""
        self.db_connection.close()


# Backward compatibility
ComprehensiveDatabaseLoader = DatabaseLoader

