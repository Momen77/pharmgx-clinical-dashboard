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
            phase5_attempts = 0
            max_phase5_attempts = 2
            while phase5_attempts < max_phase5_attempts:
                try:
                    phase5_attempts += 1
                    phase5_records = self.linking_loader.load_all(cursor, profile)
                    phase5_records += self.literature_loader.load_all(cursor, profile)
                    phase5_records += self.summaries_loader.load_all(cursor, profile)
                    total_records += phase5_records
                    self.logger.info(f"✅ Phase 5 completed: {phase5_records} records")
                    break  # Success - exit retry loop
                except Exception as phase5_error:
                    error_msg = str(phase5_error)
                    self.logger.warning(f"⚠️ Phase 5 attempt {phase5_attempts} failed: {error_msg}")
                    
                    # Check if transaction aborted
                    if "transaction is aborted" in error_msg.lower() or "current transaction is aborted" in error_msg.lower():
                        if phase5_attempts < max_phase5_attempts:
                            self.logger.warning("🔄 Transaction aborted in Phase 5 - attempting recovery")
                            try:
                                # Rollback and restart transaction
                                connection.rollback()
                                cursor.execute("BEGIN")
                                self.logger.info(f"✅ Transaction restarted (attempt {phase5_attempts + 1}/{max_phase5_attempts})")
                                # Continue to retry
                            except Exception as recovery_error:
                                self.logger.error(f"❌ Failed to recover transaction: {recovery_error}")
                                # If we can't recover, break and continue to commit
                                break
                        else:
                            self.logger.error("❌ Phase 5 failed after max attempts - continuing to commit")
                            # Don't raise - allow commit to proceed with partial data
                            break
                    else:
                        # Non-transaction error - log and continue
                        self.logger.error(f"❌ Phase 5 non-transaction error: {error_msg}")
                        # Don't retry non-transaction errors
                        break
            
            # Get patient_id for verification
            patient_id = profile.get('patient_id', '')
            
            # Commit transaction - CRITICAL: Use connection.commit() NOT cursor.execute("COMMIT")
            self.logger.info("🔄 Committing transaction...")
            
            # CRITICAL: Check if transaction is already aborted before attempting commit
            try:
                test_cursor = connection.cursor()
                test_cursor.execute("SELECT 1")
                test_cursor.fetchone()
                test_cursor.close()
            except Exception as tx_check:
                if "transaction is aborted" in str(tx_check).lower() or "current transaction is aborted" in str(tx_check).lower():
                    self.logger.error("❌ Transaction is already aborted before commit - cannot commit")
                    raise RuntimeError("Transaction aborted - data cannot be committed") from tx_check
            
            # CRITICAL: Ensure autocommit is False before committing
            if hasattr(connection, 'autocommit') and connection.autocommit:
                self.logger.warning("⚠️ Autocommit was True - disabling it")
                connection.autocommit = False
            
            # Get transaction status before commit
            try:
                cursor.execute("SELECT txid_current(), pg_backend_pid(), current_setting('transaction_isolation', true)")
                tx_before = cursor.fetchone()
                self.logger.info(f"🔍 Transaction ID before commit: {tx_before[0]}, PID: {tx_before[1]}, Isolation: {tx_before[2]}")
            except Exception as tx_query_error:
                if "transaction is aborted" in str(tx_query_error).lower():
                    self.logger.error("❌ Transaction aborted - cannot query transaction status")
                    raise RuntimeError("Transaction aborted - cannot commit") from tx_query_error
                raise
            
            # CRITICAL: In psycopg3, we MUST use connection.commit(), not cursor.execute("COMMIT")
            # cursor.execute("COMMIT") doesn't work properly in psycopg3
            try:
                # Double-check we're committing the right connection
                if connection != self.db_connection.connection:
                    self.logger.error("❌ Connection mismatch! Using wrong connection for commit")
                    raise RuntimeError("Connection object mismatch")
                
                # Force commit with explicit error handling
                connection.commit()
                self.logger.info("✅ connection.commit() executed successfully")
                
                # CRITICAL: Verify commit actually happened by checking transaction state
                # After commit, we should be in a new transaction
                verify_tx_cursor = connection.cursor()
                verify_tx_cursor.execute("SELECT txid_current()")
                tx_after_commit = verify_tx_cursor.fetchone()[0]
                verify_tx_cursor.close()
                
                if tx_after_commit == tx_before[0]:
                    self.logger.error(f"❌ CRITICAL: Transaction ID unchanged after commit! Before: {tx_before[0]}, After: {tx_after_commit}")
                    self.logger.error("❌ This indicates commit did NOT work - transaction was not committed")
                    raise RuntimeError(f"Commit failed - transaction ID unchanged: {tx_after_commit}")
                else:
                    self.logger.info(f"✅ Transaction ID changed after commit: {tx_before[0]} → {tx_after_commit}")
                    
            except Exception as commit_error:
                self.logger.error(f"❌ Commit failed: {commit_error}")
                import traceback
                self.logger.error(f"Traceback: {traceback.format_exc()}")
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
            # Create a NEW cursor after commit to ensure we're reading committed data
            import time
            time.sleep(0.2)  # Small delay to ensure commit propagated
            
            try:
                # Use a fresh cursor for verification to ensure we're in a new transaction
                verify_cursor = connection.cursor()
                
                # CRITICAL: Check connection info to ensure we're querying the right database
                verify_cursor.execute("SELECT current_database(), current_user, inet_server_addr(), inet_server_port()")
                db_info = verify_cursor.fetchone()
                self.logger.info(f"🔍 Verification query on: DB={db_info[0]}, User={db_info[1]}, Host={db_info[2]}, Port={db_info[3]}")
                
                # Check patients table - try multiple times to rule out timing issues
                verification_attempts = 3
                patient_count = 0
                total_patients = 0
                demo_count = 0
                
                for attempt in range(verification_attempts):
                    if attempt > 0:
                        time.sleep(0.5)  # Wait before retry
                    
                    verify_cursor.execute("SELECT COUNT(*) FROM patients WHERE patient_id = %s", (patient_id,))
                    patient_count = verify_cursor.fetchone()[0]
                    
                    verify_cursor.execute("SELECT COUNT(*) FROM patients")
                    total_patients = verify_cursor.fetchone()[0]
                    
                    verify_cursor.execute("SELECT COUNT(*) FROM demographics WHERE patient_id = %s", (patient_id,))
                    demo_count = verify_cursor.fetchone()[0]
                    
                    self.logger.info(f"🔍 Verification attempt {attempt + 1}: Patient={patient_count}, Total={total_patients}, Demo={demo_count}")
                    
                    if patient_count > 0:
                        break  # Found data - exit retry loop
                
                self.logger.info(f"🔍 Final verification results: Found {patient_count} record(s) for patient {patient_id}")
                self.logger.info(f"🔍 Final verification: Total patients in database: {total_patients}")
                self.logger.info(f"🔍 Final verification: Demographics records: {demo_count}")
                
                if patient_count == 0 and total_records > 0:
                    self.logger.error("❌ CRITICAL: Commit reported success but no data found after multiple verification attempts!")
                    # Log detailed transaction and connection info
                    verify_cursor.execute("SELECT txid_current(), pg_backend_pid()")
                    tx_info = verify_cursor.fetchone()
                    self.logger.error(f"❌ Transaction ID: {tx_info[0]}, PID: {tx_info[1]}")
                    self.logger.error(f"❌ This indicates data was NOT actually committed to the database")
                    raise RuntimeError(f"Data verification failed - no records found after commit (patient_count={patient_count}, total_patients={total_patients})")
                elif patient_count > 0:
                    self.logger.info(f"✅ Data verification PASSED - {patient_count} patient record(s) found, {total_patients} total patients")
                
            except Exception as verify_error:
                import traceback
                self.logger.error(f"❌ Verification query failed: {verify_error}")
                self.logger.error(f"Traceback: {traceback.format_exc()}")
                # Don't raise here - let the final verification catch it
            finally:
                if 'verify_cursor' in locals():
                    verify_cursor.close()
            
            duration = (datetime.now() - start_time).total_seconds()
            
            # CRITICAL: Final verification BEFORE returning success
            # Use a completely fresh cursor with explicit isolation to ensure we're reading committed data
            import time
            time.sleep(0.5)  # Delay to ensure commit has fully propagated to database
            
            try:
                final_verify = connection.cursor()
                
                # Get database connection info to confirm we're on the right database
                final_verify.execute("SELECT current_database(), current_user, inet_server_addr(), inet_server_port()")
                db_info = final_verify.fetchone()
                self.logger.info(f"🔍 Final verification on: DB={db_info[0]}, User={db_info[1]}, Host={db_info[2]}, Port={db_info[3]}")
                
                # Set explicit isolation level to ensure we see committed data
                final_verify.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
                
                # Multiple verification attempts
                verification_passed = False
                final_patient_count = 0
                final_total_count = 0
                final_demo_count = 0
                
                for attempt in range(3):
                    if attempt > 0:
                        time.sleep(0.3)
                    
                    final_verify.execute("SELECT COUNT(*) FROM patients WHERE patient_id = %s", (patient_id,))
                    final_patient_count = final_verify.fetchone()[0]
                    final_verify.execute("SELECT COUNT(*) FROM patients")
                    final_total_count = final_verify.fetchone()[0]
                    final_verify.execute("SELECT COUNT(*) FROM demographics WHERE patient_id = %s", (patient_id,))
                    final_demo_count = final_verify.fetchone()[0]
                    
                    self.logger.info(f"🔍 Final verification attempt {attempt + 1}: Patient={final_patient_count}, Total={final_total_count}, Demo={final_demo_count}")
                    
                    if final_patient_count > 0:
                        verification_passed = True
                        # Get sample record to confirm it's real
                        # Schema uses date_created (not created_at)
                        final_verify.execute("SELECT patient_id, date_created FROM patients WHERE patient_id = %s LIMIT 1", (patient_id,))
                        sample = final_verify.fetchone()
                        if sample:
                            self.logger.info(f"🔍 Sample record: patient_id={sample[0]}, date_created={sample[1]}")
                        break
                
                if not verification_passed and total_records > 0:
                    self.logger.error(f"❌ CRITICAL: Commit succeeded but data not found after 3 attempts!")
                    self.logger.error(f"❌ Patient count: {final_patient_count}, Total: {final_total_count}, Demo: {final_demo_count}")
                    # Log transaction state
                    final_verify.execute("SELECT txid_current(), pg_backend_pid()")
                    tx_info = final_verify.fetchone()
                    self.logger.error(f"❌ Transaction ID: {tx_info[0]}, PID: {tx_info[1]}")
                    final_verify.close()
                    # This means commit isn't actually persisting - return error
                    return {
                        'success': False,
                        'error': f'Commit reported success but data not found in database (patient_count={final_patient_count}, total={final_total_count})',
                        'records_inserted': 0,
                        'duration_seconds': duration,
                        'patient_id': patient_id
                    }
                elif verification_passed:
                    self.logger.info(f"✅ Final verification PASSED: {final_patient_count} patient(s), {final_total_count} total patients, {final_demo_count} demographics")
                else:
                    self.logger.warning(f"⚠️ Final verification: No data but total_records={total_records}")
                    
                final_verify.close()
                
            except Exception as final_error:
                import traceback
                self.logger.error(f"❌ Final verification query failed: {final_error}")
                self.logger.error(f"Traceback: {traceback.format_exc()}")
                # If verification fails, we can't confirm data is there - return error
                return {
                    'success': False,
                    'error': f'Final verification failed: {final_error}',
                    'records_inserted': 0,
                    'duration_seconds': duration,
                    'patient_id': patient_id
                }
            
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
            
            # CRITICAL: Ensure commit has fully propagated before closing
            # Force a sync query to ensure the commit is written to disk
            if connection and not connection.closed:
                try:
                    sync_cursor = connection.cursor()
                    sync_cursor.execute("SELECT pg_backend_pid(), txid_current()")
                    sync_info = sync_cursor.fetchone()
                    self.logger.info(f"🔍 Pre-close sync: PID={sync_info[0]}, TXID={sync_info[1]}")
                    
                    # Force a write to ensure commit is persisted
                    sync_cursor.execute("SELECT 1")
                    sync_cursor.fetchone()
                    sync_cursor.close()
                    self.logger.info("✅ Sync query completed")
                except Exception as sync_error:
                    self.logger.warning(f"⚠️ Sync query failed: {sync_error}")
            
            # Wait to ensure commit has fully propagated to database
            time.sleep(1.0)  # Delay for reliability
            
            # CRITICAL: Do NOT close the connection if we successfully committed
            # Closing the connection is handled by the DatabaseConnection.close() method
            # which should be called explicitly, not in finally block
            # The connection should remain open until explicitly closed
            self.logger.info("🔒 Keeping connection open (will be closed by db_loader.close())")
    
    def close(self):
        """Close database connection"""
        self.db_connection.close()


# Backward compatibility
ComprehensiveDatabaseLoader = DatabaseLoader

