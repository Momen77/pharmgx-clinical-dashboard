"""PGx-KG Main Pipeline - Enhanced for Dashboard Integration
Orchestrates all 5 phases to build pharmacogenomics knowledge graphs
Now includes proper patient profile handling and comprehensive output generation
"""
import argparse
import sys
import json
import random
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Add src to path
sys.path.append(str(Path(__file__).parent))

from utils.config import Config
from utils.dynamic_clinical_generator import DynamicClinicalGenerator
from utils.variant_phenotype_linker import VariantPhenotypeLinker
from phase1_discovery.variant_discoverer import VariantDiscoverer
from phase2_clinical.clinical_validator import ClinicalValidator
from phase3_context.drug_disease_linker import DrugDiseaseLinker
from phase4_rdf.graph_builder import RDFGraphBuilder
from phase5_export.json_exporter import JSONLDExporter
from phase5_export.html_reporter import HTMLReporter

# Try to import EventBus for dashboard integration
try:
    from utils.event_bus import PipelineEvent as _PipelineEventImported, emit as queue_emit
    # Adapter: provide a compatible PipelineEvent callable with default level
    def PipelineEvent(stage, substage, message, progress=None, level="info", payload=None):
        # utils.event_bus.PipelineEvent signature is (stage, substage, level, message, progress, payload)
        return _PipelineEventImported(stage, substage, level, message, progress, payload)
    # Provide a minimal EventBus wrapper that uses the queue when available
    class EventBus:
        """Queue-backed EventBus wrapper for dashboard integration"""
        def __init__(self, event_queue=None):
            self.event_queue = event_queue
            self.subscribers = []

        def subscribe(self, callback):
            self.subscribers.append(callback)

        def emit(self, event):
            # Prefer queue for thread-safe UI communication
            if self.event_queue is not None:
                try:
                    self.event_queue.put(event, block=False)
                except Exception:
                    pass
            # Also call local subscribers (optional)
            for callback in self.subscribers:
                try:
                    callback(event)
                except Exception:
                    pass
except ImportError:
    queue_emit = None

    # Fallback for when EventBus is not available
    class PipelineEvent:
        def __init__(self, stage, substage, message, progress=None, level="info", payload=None):
            self.stage = stage
            self.substage = substage
            self.message = message
            self.progress = progress
            self.level = level
            self.payload = payload

    class EventBus:
        """Thread-safe EventBus with improved error handling"""
        def __init__(self, event_queue=None):
            self.subscribers = []
            self.event_queue = event_queue

        def subscribe(self, callback):
            self.subscribers.append(callback)

        def emit(self, event):
            # If we have a queue, use it (thread-safe)
            if self.event_queue is not None:
                try:
                    self.event_queue.put(event, block=False)
                except Exception as e:
                    import traceback
                    print(f"Queue emit error: {e}")
                    print(f"Full traceback:\n{traceback.format_exc()}")

            # Also call subscribers (for compatibility)
            for callback in self.subscribers:
                try:
                    callback(event)
                except Exception as e:
                    import traceback
                    print(f"Event callback error: {e}")
                    print(f"Full traceback:\n{traceback.format_exc()}")


class PGxPipeline:
    """Enhanced Pipeline for Dashboard Integration"""

    def __init__(self, config_path: str = "config.yaml", event_bus=None, event_queue=None):
        """Initialize pipeline with optional event bus or event queue for dashboard integration

        Args:
            config_path: Path to config.yaml
            event_bus: Optional EventBus instance (callback-based, not thread-safe for Streamlit)
            event_queue: Optional Queue instance (thread-safe, recommended for Streamlit)
        """
        self.config = Config(config_path)
        self.event_queue = event_queue

        # Create EventBus with queue support if queue provided
        if event_queue is not None:
            self.event_bus = EventBus(event_queue=event_queue)
        elif event_bus is not None:
            self.event_bus = event_bus
        else:
            self.event_bus = EventBus()
        
        # Initialize phase modules
        self.phase1 = VariantDiscoverer()
        self.phase2 = ClinicalValidator(
            ncbi_email=self.config.ncbi_email,
            ncbi_api_key=self.config.ncbi_api_key,
            bioportal_api_key=self.config.bioportal_api_key
        )
        self.phase3 = DrugDiseaseLinker(
            bioportal_api_key=self.config.bioportal_api_key
        )
        self.phase4 = RDFGraphBuilder()
        self.phase5_jsonld = JSONLDExporter()
        self.phase5_html = HTMLReporter()
        
        # Dynamic clinical data generator
        self.dynamic_clinical = DynamicClinicalGenerator(
            bioportal_api_key=self.config.bioportal_api_key
        )
        
        # Variant-phenotype-drug linker with conflict detection
        self.variant_linker = VariantPhenotypeLinker(
            bioportal_api_key=self.config.bioportal_api_key
        )
    
    def run_single_gene(self, gene_symbol: str, protein_id: str = None, patient_profile: dict = None):
        """Run pipeline for a single gene with optional patient profile"""
        return self.run(gene_symbol, protein_id, patient_profile)
    
    def run(self, gene_symbol: str, protein_id: str = None, patient_profile: dict = None):
        """Run complete pipeline for a gene with patient profile support"""
        start_time = datetime.now()
        
        self.event_bus.emit(PipelineEvent(
            stage="lab_prep",
            substage="start",
            message=f"Starting analysis for {gene_symbol}...",
            progress=0.0
        ))
        
        print(f"\n{'='*70}")
        print(f"PGx-KG: Pharmacogenomics Knowledge Graph Builder")
        print(f"{'='*70}")
        print(f"Gene: {gene_symbol}")
        print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        if patient_profile:
            print(f"Patient Profile: {patient_profile.get('patient_id', 'Dashboard Patient')}")
        print(f"{'='*70}\n")
        
        try:
            # Phase 1: Variant Discovery
            self.event_bus.emit(PipelineEvent(
                stage="lab_prep",
                substage="variant_discovery",
                message="Discovering variants...",
                progress=0.1
            ))
            
            print("PHASE 1: Variant Discovery")
            print("-" * 70)
            phase1_result = self.phase1.run_pipeline(gene_symbol, protein_id)
            protein_id = phase1_result["protein_id"]
            
            # Phase 2: Clinical Validation
            self.event_bus.emit(PipelineEvent(
                stage="ngs",
                substage="clinical_validation",
                message="Validating clinical significance...",
                progress=0.3
            ))
            
            print(f"\n{'='*70}")
            print("PHASE 2: Clinical Validation")
            print("-" * 70)
            self.phase2.run_pipeline(gene_symbol)
            
            # Phase 3: Drug & Disease Context
            self.event_bus.emit(PipelineEvent(
                stage="annotation",
                substage="drug_disease_context",
                message="Adding drug and disease context...",
                progress=0.5
            ))
            
            print(f"\n{'='*70}")
            print("PHASE 3: Drug & Disease Context")
            print("-" * 70)
            self.phase3.run_pipeline(gene_symbol)
            
            # Phase 4: RDF Graph Assembly
            self.event_bus.emit(PipelineEvent(
                stage="enrichment",
                substage="rdf_assembly",
                message="Assembling RDF knowledge graph...",
                progress=0.7
            ))
            
            print(f"\n{'='*70}")
            print("PHASE 4: RDF Knowledge Graph Assembly")
            print("-" * 70)
            rdf_output = self.phase4.run_pipeline(gene_symbol)
            
            # Phase 5: Export & Visualization
            self.event_bus.emit(PipelineEvent(
                stage="report",
                substage="export",
                message="Generating outputs...",
                progress=0.9
            ))
            
            print(f"\n{'='*70}")
            print("PHASE 5: Export & Visualization")
            print("-" * 70)
            jsonld_output = self.phase5_jsonld.run_pipeline(gene_symbol)
            html_output = self.phase5_html.run_pipeline(gene_symbol)
            
            # Summary
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            self.event_bus.emit(PipelineEvent(
                stage="report",
                substage="complete",
                message="Single gene analysis complete!",
                progress=1.0
            ))
            
            print(f"\n{'='*70}")
            print("PIPELINE COMPLETE!")
            print(f"{'='*70}")
            print(f"\nGene: {gene_symbol}")
            print(f"Protein ID: {protein_id}")
            print(f"Duration: {duration:.1f} seconds")
            print(f"\nOutputs:")
            print(f"  RDF Turtle:  {rdf_output}")
            print(f"  JSON-LD:     {jsonld_output}")
            print(f"  HTML Report: {html_output}")
            print(f"\nVariants processed: {phase1_result['total_variants']}")
            print(f"{'='*70}\n")
            
            return {
                "success": True,
                "gene": gene_symbol,
                "protein_id": protein_id,
                "duration": duration,
                "variants_processed": phase1_result['total_variants'],
                "outputs": {
                    "rdf": rdf_output,
                    "jsonld": jsonld_output,
                    "html": html_output
                }
            }
            
        except Exception as e:
            self.event_bus.emit(PipelineEvent(
                stage="error",
                substage="pipeline",
                message=f"Pipeline error: {str(e)}",
                progress=0.0
            ))
            
            print(f"\n{'='*70}")
            print(f"PIPELINE FAILED")
            print(f"{'='*70}")
            print(f"Error: {str(e)}")
            print(f"{'='*70}\n")
            
            import traceback
            traceback.print_exc()
            
            return {
                "success": False,
                "gene": gene_symbol,
                "error": str(e)
            }
    
    def run_multi_gene(self, gene_symbols: list, patient_profile: dict = None) -> dict:
        """Enhanced multi-gene analysis with proper patient profile integration"""
        start_time = datetime.now()
        
        self.event_bus.emit(PipelineEvent(
            stage="lab_prep",
            substage="init",
            message=f"Starting multi-gene analysis for {len(gene_symbols)} genes...",
            progress=0.0
        ))
        
        print(f"\n{'='*70}")
        print(f"PGx-KG: Multi-Gene Pharmacogenomics Knowledge Graph Builder")
        print(f"{'='*70}")
        print(f"Genes: {', '.join(gene_symbols)}")
        print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        if patient_profile:
            print(f"Using patient profile: {patient_profile.get('patient_id', 'Dashboard Patient')}")
        print(f"{'='*70}\n")
        
        results = {}
        all_variants = []
        all_drugs = set()
        all_diseases = set()
        
        # Determine patient ID and profile source
        dashboard_source = False
        if patient_profile:
            # Check if this is a dashboard-created profile
            dashboard_source = patient_profile.get("dashboard_source", False)
            
            # Prefer MRN as the canonical identifier for patient_id
            patient_id = None
            demographics = (patient_profile.get("clinical_information", {}) or {}).get("demographics", {})
            mrn = demographics.get("mrn")
            if isinstance(mrn, str) and mrn.strip():
                patient_id = mrn.strip()  # keep MRN format as-is (e.g., MRN-12345)
            else:
                # Fallback to explicit patient_id if present
                patient_id = patient_profile.get("patient_id")
                
            # If still missing, final fallback
            
            # Final fallback
            if not patient_id:
                patient_id = f"dashboard_patient_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            print(f"Using patient profile from dashboard: {patient_id}")
        else:
            patient_id = f"comprehensive_patient_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            print(f"Generating new patient profile: {patient_id}")
        
        try:
            # Thread-safe lock for shared data structures
            lock = threading.Lock()

            # PARALLEL PROCESSING: Process genes concurrently
            # Optimize thread pool size based on:
            # 1. Number of genes to process
            # 2. CPU count (for I/O-bound tasks like API calls, can be higher)
            # 3. Maximum limit to avoid overwhelming APIs
            import os
            cpu_count = os.cpu_count() or 4
            # For I/O-bound tasks, use 2x CPU count, but cap at 8
            max_workers = min(len(gene_symbols), min(cpu_count * 2, 8))

            print(f"\n{'='*70}")
            print(f"PARALLEL PROCESSING: Running {len(gene_symbols)} genes with {max_workers} workers")
            print(f"CPU Count: {cpu_count}, Optimized workers: {max_workers}")
            print(f"{'='*70}\n")

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all gene processing tasks
                future_to_gene = {
                    executor.submit(self.run, gene_symbol): gene_symbol
                    for gene_symbol in gene_symbols
                }

                # Process results as they complete
                completed = 0
                for future in as_completed(future_to_gene):
                    gene_symbol = future_to_gene[future]
                    completed += 1

                    progress = 0.1 + (0.6 * completed / len(gene_symbols))  # 10-70% for gene processing

                    try:
                        gene_result = future.result()

                        # Thread-safe updates
                        with lock:
                            results[gene_symbol] = gene_result

                        self.event_bus.emit(PipelineEvent(
                            stage="ngs" if completed <= len(gene_symbols)/2 else "annotation",
                            substage="processing",
                            message=f"Completed gene {gene_symbol} ({completed}/{len(gene_symbols)})...",
                            progress=progress
                        ))

                        print(f"\n{'='*70}")
                        print(f"COMPLETED GENE {completed}/{len(gene_symbols)}: {gene_symbol}")
                        print(f"{'='*70}")

                        if gene_result["success"]:
                            # Collect variants from this gene
                            gene_variants = self._extract_gene_variants(gene_symbol)
                            # Resolve exact rsIDs as early as possible using allele tuple
                            try:
                                gene_variants = self._assign_exact_rsid(gene_variants)
                            except Exception:
                                pass
                            gene_drugs, gene_diseases = self._extract_drugs_diseases(gene_symbol)

                            # Thread-safe updates
                            with lock:
                                all_variants.extend(gene_variants)
                                all_drugs.update(gene_drugs)
                                all_diseases.update(gene_diseases)
                        else:
                            print(f"WARNING: Failed to process {gene_symbol}: {gene_result.get('error', 'Unknown error')}")

                    except Exception as e:
                        print(f"ERROR: Exception processing {gene_symbol}: {str(e)}")
                        with lock:
                            results[gene_symbol] = {
                                "success": False,
                                "gene": gene_symbol,
                                "error": str(e)
                            }
            
            # Create comprehensive patient profile
            self.event_bus.emit(PipelineEvent(
                stage="enrichment",
                substage="profile_generation",
                message="Creating comprehensive patient profile...",
                progress=0.75
            ))
            
            print(f"\n{'='*70}")
            print("CREATING COMPREHENSIVE PATIENT PROFILE")
            print(f"{'='*70}")
            
            comprehensive_profile = self._create_comprehensive_profile(
                patient_id, gene_symbols, all_variants, all_drugs, all_diseases, patient_profile, dashboard_source
            )
            
            # Link patient profile to variants and detect conflicts
            self.event_bus.emit(PipelineEvent(
                stage="enrichment",
                substage="variant_linking",
                message="Linking patient profile to variants...",
                progress=0.85
            ))
            
            print(f"\n{'='*70}")
            print("LINKING PATIENT PROFILE TO VARIANTS")
            print(f"{'='*70}")
            linking_results = self.variant_linker.link_patient_profile_to_variants(
                patient_profile=comprehensive_profile,
                variants=all_variants
            )
            
            # Add linking results to comprehensive profile
            comprehensive_profile["variant_linking"] = linking_results

            # Enrich variants with patient-specific population frequency context
            try:
                from utils.population_frequencies import classify_population_significance, summarize_ethnicity_context
                from utils.dosing_adjustments import suggest_ethnicity_adjustments
                patient_ethnicity = None
                patient_ethnicity_snomed_code = None
                try:
                    demo = comprehensive_profile.get("clinical_information", {}).get("demographics", {})
                    eth = demo.get("ethnicity")
                    if isinstance(eth, list) and eth:
                        patient_ethnicity = eth[0]
                    elif isinstance(eth, str):
                        patient_ethnicity = eth
                    # Attach SNOMED code for patient's ethnicity if available
                    eth_snomed = comprehensive_profile.get("clinical_information", {}).get("ethnicity_snomed")
                    if isinstance(eth_snomed, list) and patient_ethnicity:
                        for ent in eth_snomed:
                            label = ent.get("label") or ent.get("rdfs:label") or ent.get("skos:prefLabel")
                            if label == patient_ethnicity:
                                patient_ethnicity_snomed_code = ent.get("snomed:code")
                                break
                except Exception:
                    patient_ethnicity = None

                for v in all_variants:
                    freqs = v.get("population_frequencies") or {}
                    pf = None
                    if patient_ethnicity:
                        pf = freqs.get(patient_ethnicity)
                    v["patient_population_frequency"] = pf
                    v["population_significance"] = classify_population_significance(pf)
                    v["ethnicity_context"] = summarize_ethnicity_context(
                        v.get("rsid") or v.get("variant_id", ""),
                        v.get("gene", ""),
                        patient_ethnicity,
                        freqs,
                    )
                    if patient_ethnicity_snomed_code:
                        v["patient_ethnicity_snomed_code"] = patient_ethnicity_snomed_code

                # Ethnicity-aware medication adjustment hints (non-binding)
                adjustments = suggest_ethnicity_adjustments(all_variants, patient_ethnicity)
                if adjustments:
                    # Enrich with SNOMED CT codes where possible
                    try:
                        if hasattr(self, 'variant_linker') and self.variant_linker and hasattr(self.variant_linker, '_search_drug_snomed'):
                            for adj in adjustments:
                                dname = adj.get("drug")
                                if not dname:
                                    continue
                                snomed = self.variant_linker._search_drug_snomed(dname)
                                if snomed and snomed.get("code"):
                                    adj["snomed:code"] = snomed["code"]
                                    adj["snomed:uri"] = f"http://snomed.info/id/{snomed['code']}"
                    except Exception:
                        pass
                    comprehensive_profile["ethnicity_medication_adjustments"] = adjustments
            except Exception:
                pass
            
            # Generate all output formats
            self.event_bus.emit(PipelineEvent(
                stage="report",
                substage="export",
                message="Generating all output formats...",
                progress=0.95
            ))
            
            outputs = self._generate_all_outputs(comprehensive_profile, results)
            
            # Summary
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            self.event_bus.emit(PipelineEvent(
                stage="report",
                substage="complete",
                message="Multi-gene analysis complete!",
                progress=1.0
            ))
            
            print(f"\n{'='*70}")
            print("MULTI-GENE PIPELINE COMPLETE!")
            print(f"{'='*70}")
            print(f"\nGenes processed: {len(gene_symbols)}")
            print(f"Total variants: {len(all_variants)}")
            print(f"Affected drugs: {len(all_drugs)}")
            print(f"Associated diseases: {len(all_diseases)}")
            
            # Display conflict summary if available
            if "variant_linking" in comprehensive_profile:
                linking_summary = comprehensive_profile["variant_linking"].get("summary", {})
                conflicts_summary = linking_summary.get("conflicts", {})
                print(f"\n{'='*70}")
                print("VARIANT LINKING & CONFLICT ANALYSIS")
                print(f"{'='*70}")
                print(f"Total conflicts detected: {conflicts_summary.get('total', 0)}")
                print(f"  ⚠️  Critical: {conflicts_summary.get('critical', 0)}")
                print(f"  ⚠️  Warnings: {conflicts_summary.get('warnings', 0)}")
                print(f"  ℹ️  Info: {conflicts_summary.get('info', 0)}")
                
                links_summary = linking_summary.get("total_links", {})
                print(f"\nLinks created:")
                print(f"  💊 Medication-to-Variant: {links_summary.get('medication_to_variant', 0)}")
                print(f"  🏥 Condition-to-Disease: {links_summary.get('condition_to_disease', 0)}")
                print(f"  🧬 Variant-to-Phenotype: {links_summary.get('variant_to_phenotype', 0)}")
                print(f"  💉 Drug-to-Variant: {links_summary.get('drug_to_variant', 0)}")
            
            print(f"\nDuration: {duration:.1f} seconds")
            print(f"\nComprehensive outputs:")
            for output_type, path in outputs.items():
                print(f"  {output_type}: {path}")
            print(f"{'='*70}\n")
            
            return {
                "success": True,
                "patient_id": patient_id,
                "dashboard_source": dashboard_source,
                "genes": gene_symbols,
                "total_variants": len(all_variants),
                "affected_drugs": len(all_drugs),
                "associated_diseases": len(all_diseases),
                "duration": duration,
                "gene_results": results,
                "comprehensive_profile": comprehensive_profile,
                "comprehensive_outputs": outputs,  # Use "comprehensive_outputs" to avoid confusion
                "outputs": outputs  # Keep for backward compatibility
            }
            
        except Exception as e:
            self.event_bus.emit(PipelineEvent(
                stage="error",
                substage="pipeline",
                message=f"Multi-gene pipeline error: {str(e)}",
                progress=0.0
            ))
            
            print(f"\n{'='*70}")
            print(f"MULTI-GENE PIPELINE FAILED")
            print(f"{'='*70}")
            print(f"Error: {str(e)}")
            print(f"{'='*70}\n")
            
            import traceback
            traceback.print_exc()
            
            return {
                "success": False,
                "genes": gene_symbols,
                "error": str(e),
                "partial_results": results
            }
    
    def _extract_gene_variants(self, gene_symbol: str) -> list:
        """Extract variants from a processed gene"""
        try:
            # Load Phase 2 data (enriched variants)
            phase2_file = f"data/phase2/{gene_symbol}_clinical.json"
            with open(phase2_file, 'r', encoding='utf-8') as f:
                phase2_data = json.load(f)
            
            # Load Phase 3 data (enriched with literature)
            phase3_file = f"data/phase3/{gene_symbol}_enriched.json"
            phase3_data = {}
            try:
                with open(phase3_file, 'r', encoding='utf-8') as f:
                    phase3_data = json.load(f)
            except FileNotFoundError:
                print(f"Warning: Phase 3 file not found for {gene_symbol}")
            
            variants = []
            # Lazy init of population frequency service
            popfreq_service = None
            try:
                from utils.population_frequencies import PopulationFrequencyService, classify_population_significance, summarize_ethnicity_context
                popfreq_service = PopulationFrequencyService()
            except Exception:
                popfreq_service = None
            for i, variant in enumerate(phase2_data.get("variants", [])):
                # Get corresponding Phase 3 variant (with literature)
                phase3_variant = {}
                if "variants" in phase3_data and i < len(phase3_data["variants"]):
                    phase3_variant = phase3_data["variants"][i]
                
                variant_info = {
                    "gene": gene_symbol,
                    "protein_id": phase2_data.get("protein_id"),
                    "variant_id": self._extract_variant_id(variant),
                    "rsid": self._extract_rsid(variant),
                    "clinical_significance": self._get_clinical_significance(variant),
                    "drugs": self._extract_variant_drugs(variant),
                    "diseases": self._extract_variant_diseases(variant),
                    "literature": phase3_variant.get("literature", {}),
                    "raw_data": variant
                }

                # Enrich with population allele frequencies (ethnicity-aware)
                try:
                    if popfreq_service:
                        rs = variant_info.get("rsid")
                        if rs:
                            rsid_full = rs if rs.startswith("rs") else f"rs{rs}"
                            pf_payload = popfreq_service.get_population_frequencies(rsid_full)
                            freqs = pf_payload.get("frequencies", {})
                            variant_info["population_frequencies"] = freqs
                            variant_info["population_frequency_source"] = pf_payload.get("source")
                except Exception:
                    pass
                variants.append(variant_info)
            
            return variants
            
        except Exception as e:
            print(f"Warning: Could not extract variants for {gene_symbol}: {e}")
            return []
    
    def _extract_drugs_diseases(self, gene_symbol: str) -> tuple:
        """Extract unique drugs and diseases from a gene"""
        drugs = set()
        diseases = set()
        
        try:
            # Load Phase 3 data (enriched with drugs/diseases)
            phase3_file = f"data/phase3/{gene_symbol}_enriched.json"
            with open(phase3_file, 'r', encoding='utf-8') as f:
                phase3_data = json.load(f)
            
            for variant in phase3_data.get("variants", []):
                # Extract drugs
                if "pharmgkb" in variant and "drugs" in variant["pharmgkb"]:
                    for drug in variant["pharmgkb"]["drugs"]:
                        drugs.add(drug.get("name", "Unknown"))
                
                # Extract diseases from ClinVar
                if "clinvar" in variant and "phenotypes" in variant["clinvar"]:
                    for phenotype in variant["clinvar"]["phenotypes"]:
                        diseases.add(phenotype)
            
            # Also extract gene-level phenotypes (often more comprehensive)
            gene_phenotypes = phase3_data.get("gene_level_phenotypes", [])
            for phenotype in gene_phenotypes:
                # Extract disease/condition names from phenotype descriptions
                # Look for key disease terms
                phenotype_lower = phenotype.lower()
                if any(term in phenotype_lower for term in ["disease", "disorder", "syndrome", "cancer", "toxicity", "deficiency"]):
                    # Extract the key disease term (simplified)
                    if "toxicity" in phenotype_lower:
                        diseases.add("Drug toxicity")
                    elif "deficiency" in phenotype_lower:
                        diseases.add("Enzyme deficiency")
                    elif "cancer" in phenotype_lower:
                        diseases.add("Cancer")
                    else:
                        # Add the phenotype as a potential disease
                        diseases.add(phenotype[:100])  # Truncate long descriptions
                
        except Exception as e:
            print(f"Warning: Could not extract drugs/diseases for {gene_symbol}: {e}")
        
        return drugs, diseases
    
    def _extract_variant_id(self, variant: dict) -> str:
        """Extract the best available variant identifier"""
        # Try different identifier sources in order of preference
        
        # 1. Try ftId (if available)
        if variant.get("ftId"):
            return variant["ftId"]
        
        # 2. Try dbSNP rsID
        for xref in variant.get("xrefs", []):
            if xref.get("name") == "dbSNP" and xref.get("id"):
                return xref["id"]
        
        # 3. Try ClinVar ID
        for xref in variant.get("xrefs", []):
            if xref.get("name") == "ClinVar" and xref.get("id"):
                return xref["id"]
        
        # 4. Try genomic location
        genomic_locations = variant.get("genomicLocation", [])
        if genomic_locations:
            return genomic_locations[0]
        
        # 5. Try protein change
        locations = variant.get("locations", [])
        for loc in locations:
            if loc.get("loc") and loc["loc"].startswith("p."):
                return loc["loc"]
        
        # 6. Fallback to position-based ID
        begin = variant.get("begin")
        end = variant.get("end")
        alt_seq = variant.get("alternativeSequence")
        if begin and alt_seq:
            return f"pos_{begin}_{alt_seq}"
        
        return "Unknown"
    
    def _extract_rsid(self, variant: dict) -> str:
        """Extract rsID from variant"""
        for xref in variant.get("xrefs", []):
            if xref.get("name") == "dbSNP":
                return xref.get("id", "").replace("rs", "")
        return None
    
    def _get_clinical_significance(self, variant: dict) -> str:
        """Get clinical significance from variant"""
        clin_sigs = [sig["type"] for sig in variant.get("clinicalSignificances", [])]
        return clin_sigs[0] if clin_sigs else "Unknown"
    
    def _extract_variant_drugs(self, variant: dict) -> list:
        """Extract drugs affected by variant with SNOMED CT codes"""
        drugs = []
        if "pharmgkb" in variant and "drugs" in variant["pharmgkb"]:
            for drug in variant["pharmgkb"]["drugs"]:
                drug_name = drug.get("name")
                drug_info = {
                    "name": drug_name,
                    "recommendation": drug.get("recommendation", "")[:100] + "..." if len(drug.get("recommendation", "")) > 100 else drug.get("recommendation", ""),
                    "evidence_level": drug.get("evidence_level", "")
                }
                
                # Add SNOMED CT code if available from linker
                if self.variant_linker and drug_name:
                    snomed_data = self.variant_linker._search_drug_snomed(drug_name)
                    if snomed_data:
                        drug_info["snomed:code"] = snomed_data.get("code")
                        drug_info["snomed:uri"] = f"http://snomed.info/id/{snomed_data.get('code')}"
                
                drugs.append(drug_info)
        return drugs
    
    def _extract_variant_diseases(self, variant: dict) -> list:
        """Extract diseases associated with variant"""
        diseases = []
        
        # Extract from ClinVar
        if "clinvar" in variant and "phenotypes" in variant["clinvar"]:
            for phenotype in variant["clinvar"]["phenotypes"]:
                disease_info = {"name": phenotype, "source": "ClinVar"}
                
                # Add SNOMED CT code if available
                if self.variant_linker:
                    snomed_data = self.variant_linker._search_snomed(phenotype)
                    if snomed_data:
                        disease_info["snomed:code"] = snomed_data.get("code")
                        disease_info["snomed:uri"] = f"http://snomed.info/id/{snomed_data.get('code')}"
                
                diseases.append(disease_info)
        
        # Extract from PharmGKB phenotypes (often more informative)
        if "pharmgkb" in variant and "phenotypes" in variant["pharmgkb"]:
            for phenotype in variant["pharmgkb"]["phenotypes"]:
                # Extract disease-related terms from phenotype descriptions
                phenotype_lower = phenotype.lower()
                if any(term in phenotype_lower for term in ["disease", "disorder", "syndrome", "toxicity", "adverse"]):
                    disease_info = {
                        "name": phenotype[:80],  # Truncate for readability
                        "source": "PharmGKB"
                    }
                    
                    # Add SNOMED CT code if available
                    if self.variant_linker:
                        snomed_data = self.variant_linker._search_snomed(phenotype)
                        if snomed_data:
                            disease_info["snomed:code"] = snomed_data.get("code")
                            disease_info["snomed:uri"] = f"http://snomed.info/id/{snomed_data.get('code')}"
                    
                    diseases.append(disease_info)
        
        return diseases
    
    def _create_comprehensive_profile(self, patient_id: str, genes: list, variants: list, drugs: set, diseases: set, dashboard_profile: dict = None, dashboard_source: bool = False) -> dict:
        """Create comprehensive patient profile with enhanced clinical information"""
        # Use dashboard profile if provided, otherwise generate clinical information
        if dashboard_profile and "clinical_information" in dashboard_profile:
            print("✅ Using patient profile from dashboard")
            clinical_info = dashboard_profile["clinical_information"]
            # Don't override patient_id - it was already extracted correctly in run_multi_gene
        else:
            print("🔄 Generating new clinical information")
            clinical_info = self._generate_clinical_information(patient_id)
        
        # Get patient name from demographics if available
        demographics = clinical_info.get("demographics", {})
        # Prefer MRN as canonical identifier for entity id
        mrn_value = demographics.get("mrn")
        canonical_id = mrn_value if isinstance(mrn_value, str) and mrn_value.strip() else patient_id
        first_name = demographics.get("foaf:firstName") or demographics.get("schema:givenName", "")
        last_name = demographics.get("foaf:familyName") or demographics.get("schema:familyName", "")
        
        if first_name and last_name:
            profile_name = f"{first_name} {last_name} - Pharmacogenomics Profile"
        else:
            profile_name = "Comprehensive Pharmacogenomics Patient Profile"
        
        # Enrich clinical_info demographics ethnicity with SNOMED CT codes if possible
        try:
            if hasattr(self, 'variant_linker') and self.variant_linker:
                demo = clinical_info.get("demographics", {})
                eth_list = demo.get("ethnicity")
                if isinstance(eth_list, list) and eth_list:
                    enriched = []
                    for label in eth_list:
                        snomed = self.variant_linker._search_snomed(str(label))
                        if snomed and snomed.get("code"):
                            enriched.append({
                                "label": label,
                                "snomed:code": snomed["code"],
                                "snomed:uri": f"http://snomed.info/id/{snomed['code']}"
                            })
                        else:
                            enriched.append({"label": label})
                    clinical_info["ethnicity_snomed"] = enriched
        except Exception:
            pass
        
        profile = {
            "@context": {
                "foaf": "http://xmlns.com/foaf/0.1/",
                "schema": "http://schema.org/",
                "pgx": "http://pgx-kg.org/",
                "sdisco": "http://ugent.be/sdisco/",
                "snomed": "http://snomed.info/id/",
                "drugbank": "https://go.drugbank.com/drugs/",
                "ugent": "http://ugent.be/person/",
                "dbsnp": "https://identifiers.org/dbsnp/",
                "ncbigene": "https://identifiers.org/ncbigene/",
                "clinpgx": "https://www.clinpgx.org/haplotype/",
                "gn": "http://www.geonames.org/ontology#",
                "skos": "http://www.w3.org/2004/02/skos/core#",
                "xsd": "http://www.w3.org/2001/XMLSchema#",
                # JSON-LD terms for new patient-specific properties
                "population_frequencies": "pgx:populationFrequencies",
                "patient_population_frequency": "pgx:patientPopulationFrequency",
                "population_significance": "pgx:populationSignificance",
                "population_frequency_source": "pgx:populationFrequencySource",
                "ethnicity_context": "pgx:ethnicityContext",
                "ethnicity_medication_adjustments": "pgx:ethnicityMedicationAdjustments",
                "ethnicity_snomed": "pgx:ethnicitySnomed"
            },
            "@id": f"http://ugent.be/person/{canonical_id}",
            "@type": ["foaf:Person", "schema:Person", "schema:Patient"],
            "identifier": canonical_id,
            "other_identifiers": {"legacy_patient_id": patient_id} if canonical_id != patient_id else None,
            "patient_id": canonical_id,
            "dashboard_source": dashboard_source,  # Flag to indicate source
            "name": profile_name,
            "description": f"Multi-gene pharmacogenomics profile covering {len(genes)} genes with {len(variants)} variants",
            "dateCreated": datetime.now().isoformat(),
            
            # Enhanced Clinical Information
            "clinical_information": clinical_info,
            
            "pharmacogenomics_profile": {
                "genes_analyzed": genes,
                "total_variants": len(variants),
                "variants_by_gene": {gene: len([v for v in variants if v["gene"] == gene]) for gene in genes},
                "affected_drugs": list(drugs),
                "associated_diseases": list(diseases),
                "clinical_summary": self._generate_clinical_summary(variants),
                "literature_summary": self._generate_literature_summary(variants)
            },
            "variants": variants,
            "dataSource": "EMBL-EBI Proteins API + UniProt + ClinVar + PharmGKB + OpenFDA + Europe PMC"
        }
        
        return profile
    
    def _generate_clinical_information(self, patient_id: str) -> dict:
        """Generate comprehensive clinical information for patient profile using dynamic APIs"""
        # Use patient_id as seed for reproducibility (same patient_id = same clinical data)
        random.seed(hash(patient_id) % (2**32))
        
        # Generate demographics first (needed for age/lifestyle)
        demographics = self._generate_demographics()
        age = demographics.get("age", 50)
        
        # Generate lifestyle factors
        lifestyle_factors = self._generate_lifestyle_factors()
        
        # DYNAMIC: Query SNOMED CT for conditions based on age and lifestyle
        print("\n🔄 Dynamically querying SNOMED CT for conditions...")
        conditions = self.dynamic_clinical.get_conditions_by_age_lifestyle(age, lifestyle_factors)
        
        # Add diagnosis dates and status to conditions
        current_date = datetime.now()
        for condition in conditions:
            years_ago = random.randint(1, 10)
            condition["diagnosis_date"] = (current_date - timedelta(days=years_ago * 365)).strftime("%Y-%m-%d")
            condition["status"] = random.choice(["active", "controlled", "remission"])
        
        # DYNAMIC: Query drug APIs for medications based on conditions
        print(f"🔄 Dynamically querying drug APIs for {len(conditions)} conditions...")
        medications = []
        for condition in conditions:
            snomed_code = condition.get("snomed:code")
            condition_label = condition.get("rdfs:label", "")
            if snomed_code:
                condition_meds = self.dynamic_clinical.get_drugs_for_condition(snomed_code, condition_label)
                medications.extend(condition_meds)
        
        clinical_info = {
            "demographics": demographics,
            "current_conditions": conditions,
            "current_medications": medications,
            "organ_function": self._generate_organ_function(),
            "lifestyle_factors": lifestyle_factors
        }

        # Post-generation SNOMED validation summary
        clinical_info["snomed_validation"] = self._validate_snomed(clinical_info)

        return clinical_info

    def _validate_snomed(self, clinical_info: dict) -> dict:
        """Validate presence of SNOMED codes across clinical info and emit a concise summary"""
        missing = {"conditions": [], "medications": [], "lifestyle": [], "labs": []}

        # Conditions
        for c in clinical_info.get("current_conditions", []) or []:
            if not c.get("snomed:code"):
                missing["conditions"].append(c.get("rdfs:label") or c.get("skos:prefLabel") or c.get("search_term") or "")

        # Medications
        for m in clinical_info.get("current_medications", []) or []:
            if not m.get("snomed:code"):
                name = m.get("name") or m.get("drug_name") or m.get("rdfs:label") or m.get("schema:name") or ""
                missing["medications"].append(name)

        # Lifestyle
        for lf in clinical_info.get("lifestyle_factors", []) or []:
            if not lf.get("snomed:code") and lf.get("factor_type") in ("smoking", "alcohol", "diet"):
                missing["lifestyle"].append(lf.get("rdfs:label") or lf.get("skos:prefLabel") or lf.get("factor_type") or "")

        # Labs
        organ = clinical_info.get("organ_function", {}) or {}
        kidney = (organ.get("kidney_function", {}) or {}).get("creatinine_clearance", {})
        if kidney and not kidney.get("snomed:code"):
            missing["labs"].append("creatinine_clearance")
        alt = (organ.get("liver_function", {}) or {}).get("alt", {})
        if alt and not alt.get("snomed:code"):
            missing["labs"].append("ALT")
        ast = (organ.get("liver_function", {}) or {}).get("ast", {})
        if ast and not ast.get("snomed:code"):
            missing["labs"].append("AST")

        totals = {
            "conditions": len(clinical_info.get("current_conditions", []) or []),
            "medications": len(clinical_info.get("current_medications", []) or []),
            "lifestyle": len(clinical_info.get("lifestyle_factors", []) or []),
            "labs": 3  # we check 3 lab entries above
        }

        return {
            "totals": totals,
            "missing_counts": {k: len(v) for k, v in missing.items()},
            "missing_examples": {k: v[:5] for k, v in missing.items() if v}
        }
    
    def _generate_demographics(self) -> dict:
        """Generate comprehensive demographic information with random but realistic values including ethnicity for PGx"""
        
        # Ethnicity-aware name and demographic generation
        # Important: Different ethnic groups have different pharmacogenetic variant frequencies
        ethnicity_profiles = [
            {
                "ethnicity": ["Caucasian/European"],
                "weight": 0.45,  # 45% probability
                "first_names": ["Emma", "James", "Sophia", "William", "Olivia", "Michael", "Isabella", "David"],
                "last_names": ["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Wilson"],
                "cities": [
                    {"id": "2800866", "name": "Brussels", "alt": "Bruxelles", "country": "Belgium"},
                    {"id": "2950159", "name": "Berlin", "alt": "Berlin", "country": "Germany"},
                    {"id": "2988507", "name": "Paris", "alt": "Paris", "country": "France"},
                    {"id": "2643743", "name": "London", "alt": "London", "country": "United Kingdom"}
                ]
            },
            {
                "ethnicity": ["Asian"],
                "weight": 0.20,
                "first_names": ["Wei", "Yuki", "Min-ho", "Sakura", "Chen", "Hana", "Raj", "Priya"],
                "last_names": ["Wang", "Kim", "Chen", "Tanaka", "Zhang", "Lee", "Patel", "Kumar"],
                "cities": [
                    {"id": "1816670", "name": "Beijing", "alt": "Beijing", "country": "China"},
                    {"id": "1835848", "name": "Seoul", "alt": "Seoul", "country": "South Korea"},
                    {"id": "1850147", "name": "Tokyo", "alt": "Tokyo", "country": "Japan"},
                    {"id": "1275339", "name": "Mumbai", "alt": "Mumbai", "country": "India"}
                ]
            },
            {
                "ethnicity": ["African"],
                "weight": 0.15,
                "first_names": ["Amara", "Kwame", "Zara", "Kofi", "Nia", "Jabari", "Aisha", "Malik"],
                "last_names": ["Okafor", "Mensah", "Diallo", "Nkosi", "Kamau", "Adeyemi", "Mwangi", "Banda"],
                "cities": [
                    {"id": "2332459", "name": "Lagos", "alt": "Lagos", "country": "Nigeria"},
                    {"id": "184745", "name": "Nairobi", "alt": "Nairobi", "country": "Kenya"},
                    {"id": "993800", "name": "Johannesburg", "alt": "Johannesburg", "country": "South Africa"}
                ]
            },
            {
                "ethnicity": ["Hispanic/Latino"],
                "weight": 0.12,
                "first_names": ["Sofia", "Diego", "Maria", "Carlos", "Isabella", "Miguel", "Valentina", "Javier"],
                "last_names": ["Garcia", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Perez", "Sanchez"],
                "cities": [
                    {"id": "3530597", "name": "Mexico City", "alt": "Ciudad de México", "country": "Mexico"},
                    {"id": "3117735", "name": "Madrid", "alt": "Madrid", "country": "Spain"},
                    {"id": "3435910", "name": "Buenos Aires", "alt": "Buenos Aires", "country": "Argentina"}
                ]
            },
            {
                "ethnicity": ["Middle Eastern"],
                "weight": 0.05,
                "first_names": ["Fatima", "Omar", "Layla", "Ahmed", "Zainab", "Hassan", "Amina", "Ali"],
                "last_names": ["Al-Rashid", "Ibrahim", "Hassan", "Mansour", "Khalil", "Rahman", "Aziz", "Mahmoud"],
                "cities": [
                    {"id": "360630", "name": "Cairo", "alt": "Cairo", "country": "Egypt"},
                    {"id": "292223", "name": "Dubai", "alt": "Dubai", "country": "UAE"},
                    {"id": "281184", "name": "Beirut", "alt": "Beirut", "country": "Lebanon"}
                ]
            },
            {
                "ethnicity": ["Mixed"],
                "weight": 0.03,
                "first_names": ["Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Skyler", "Avery"],
                "last_names": ["Santos", "Silva", "Costa", "Morales", "Nguyen", "Patel", "Anderson", "Williams"],
                "cities": [
                    {"id": "3448439", "name": "São Paulo", "alt": "São Paulo", "country": "Brazil"},
                    {"id": "5128581", "name": "New York", "alt": "New York", "country": "USA"},
                    {"id": "6167865", "name": "Toronto", "alt": "Toronto", "country": "Canada"}
                ]
            }
        ]
        
        # Select ethnicity based on weighted probabilities
        ethnicity_choice = random.choices(
            ethnicity_profiles,
            weights=[p["weight"] for p in ethnicity_profiles],
            k=1
        )[0]
        
        # Generate name based on ethnicity
        first_name = random.choice(ethnicity_choice["first_names"])
        last_name = random.choice(ethnicity_choice["last_names"])
        
        # Generate middle name occasionally
        middle_name = ""
        if random.random() < 0.3:  # 30% have middle name
            middle_name = random.choice(ethnicity_choice["first_names"])
        
        # Preferred name (sometimes nickname)
        preferred_name = first_name
        if random.random() < 0.15:  # 15% use nickname
            nicknames = {
                "William": "Bill", "Michael": "Mike", "Robert": "Rob", "James": "Jim",
                "Isabella": "Bella", "Alexander": "Alex", "Elizabeth": "Liz"
            }
            preferred_name = nicknames.get(first_name, first_name)
        
        # Random age between 25-75
        age = random.randint(25, 75)
        birth_year = datetime.now().year - age
        birth_month = random.randint(1, 12)
        birth_day = random.randint(1, 28)  # Use 28 to avoid month-end issues
        birth_date = f"{birth_year}-{birth_month:02d}-{birth_day:02d}"
        
        # Random gender and biological sex
        gender_choice = random.choice(["Male", "Female"])
        gender = f"http://schema.org/{gender_choice}"
        biological_sex = gender_choice  # Usually same, but kept separate for clinical accuracy
        
        # Random weight and height (realistic ranges based on biological sex)
        if biological_sex == "Female":
            weight_kg = round(random.uniform(50, 90), 1)
            height_cm = round(random.uniform(150, 175), 1)
        else:
            weight_kg = round(random.uniform(60, 100), 1)
            height_cm = round(random.uniform(160, 190), 1)
        
        # Calculate BMI
        height_m = height_cm / 100
        bmi = round(weight_kg / (height_m ** 2), 1)
        
        # Select birthplace based on ethnicity
        birthplace = random.choice(ethnicity_choice["cities"])
        
        # Current location (may be different from birthplace - migration)
        if random.random() < 0.3:  # 30% migrated to different location
            # Select random city from any profile
            all_cities = []
            for profile in ethnicity_profiles:
                all_cities.extend(profile["cities"])
            current_city = random.choice(all_cities)
        else:
            current_city = birthplace
        
        # Generate contact information
        phone_country_codes = {
            "Belgium": "+32", "Germany": "+49", "France": "+33", "United Kingdom": "+44",
            "China": "+86", "South Korea": "+82", "Japan": "+81", "India": "+91",
            "Nigeria": "+234", "Kenya": "+254", "South Africa": "+27",
            "Mexico": "+52", "Spain": "+34", "Argentina": "+54",
            "Egypt": "+20", "UAE": "+971", "Lebanon": "+961",
            "Brazil": "+55", "USA": "+1", "Canada": "+1"
        }
        phone_code = phone_country_codes.get(current_city["country"], "+32")
        phone = f"{phone_code} {random.randint(100, 999)} {random.randint(1000, 9999)}"
        
        # Email (based on name)
        email_domains = ["gmail.com", "outlook.com", "yahoo.com", "hotmail.com", "icloud.com"]
        email = f"{first_name.lower()}.{last_name.lower()}{random.randint(1, 99)}@{random.choice(email_domains)}"
        
        # Emergency contact
        emergency_relations = ["Spouse", "Parent", "Sibling", "Child", "Friend"]
        emergency_contact = f"{random.choice(ethnicity_choice['first_names'])} {last_name} ({random.choice(emergency_relations)})"
        emergency_phone = f"{phone_code} {random.randint(100, 999)} {random.randint(1000, 9999)}"
        
        # Address in current city
        street_number = random.randint(1, 999)
        street_names = ["Main St", "High St", "Church St", "Market St", "Station Rd", "Park Ave", "Oak Ln", "Elm Dr"]
        address = f"{street_number} {random.choice(street_names)}"
        postal_code = f"{random.randint(1000, 9999)}"
        
        # Language (based on location)
        languages = {
            "Belgium": "Dutch", "Germany": "German", "France": "French", "United Kingdom": "English",
            "China": "Mandarin", "South Korea": "Korean", "Japan": "Japanese", "India": "Hindi",
            "Nigeria": "English", "Kenya": "Swahili", "South Africa": "English",
            "Mexico": "Spanish", "Spain": "Spanish", "Argentina": "Spanish",
            "Egypt": "Arabic", "UAE": "Arabic", "Lebanon": "Arabic",
            "Brazil": "Portuguese", "USA": "English", "Canada": "English"
        }
        language = languages.get(current_city["country"], "English")
        
        # Interpreter needed (if not English/local language)
        interpreter_needed = (language not in ["English", "Dutch", "French", "German"]) and random.random() < 0.2
        
        # Insurance provider (varies by region)
        insurance_providers = [
            "National Health Service", "Private Health Insurance", "Medicare", "Medicaid",
            "Blue Cross", "United Healthcare", "Aetna", "Cigna", "None"
        ]
        insurance_provider = random.choice(insurance_providers)
        insurance_policy = f"POL-{random.randint(100000, 999999)}" if insurance_provider != "None" else ""
        
        # Primary care physician
        pcp_titles = ["Dr.", "Prof.", ""]
        pcp_first = random.choice(ethnicity_choice["first_names"])
        pcp_last = random.choice(ethnicity_choice["last_names"])
        pcp_name = f"{random.choice(pcp_titles)} {pcp_first} {pcp_last}".strip()
        pcp_contact = f"{phone_code} {random.randint(100, 999)} {random.randint(1000, 9999)}"
        
        return {
            "@id": "http://ugent.be/person/demographics",
            "foaf:firstName": first_name,
            "foaf:familyName": last_name,
            "schema:givenName": first_name,
            "schema:familyName": last_name,
            "schema:additionalName": middle_name,
            "preferredName": preferred_name,
            "schema:birthDate": birth_date,
            "age": age,
            "schema:gender": gender,
            "biological_sex": biological_sex,
            
            # IMPORTANT: Ethnicity for pharmacogenetics
            # Different populations have different allele frequencies for drug-metabolizing enzymes
            "ethnicity": ethnicity_choice["ethnicity"],
            "ethnicity_note": "Critical for interpreting pharmacogenetic variants - allele frequencies vary significantly by ancestry",
            
            "schema:birthPlace": {
                "@id": f"https://www.geonames.org/{birthplace['id']}",
                "gn:name": birthplace["name"],
                "gn:alternateName": birthplace["alt"],
                "country": birthplace["country"]
            },
            
            # Current location
            "current_location": {
                "address": address,
                "city": current_city["name"],
                "country": current_city["country"],
                "postal_code": postal_code
            },
            
            # Contact information
            "contact": {
                "phone": phone,
                "email": email,
                "emergency_contact": emergency_contact,
                "emergency_phone": emergency_phone
            },
            
            "schema:weight": {
                "@type": "schema:QuantitativeValue",
                "schema:value": weight_kg,
                "schema:unitCode": "kg",
                "schema:unitText": "kilograms"
            },
            "schema:height": {
                "@type": "schema:QuantitativeValue",
                "schema:value": height_cm,
                "schema:unitCode": "cm",
                "schema:unitText": "centimeters"
            },
            "bmi": bmi,
            
            "mrn": f"MRN_{str(uuid.uuid4())[:8].upper()}",
            "language": language,
            "interpreter_needed": interpreter_needed,
            
            "insurance": {
                "provider": insurance_provider,
                "policy_number": insurance_policy
            },
            
            "pcp": {
                "name": pcp_name,
                "contact": pcp_contact
            },
            
            "note": "Auto-generated demographics with ethnicity-aware distribution for pharmacogenomic analysis"
        }
    
    def _generate_organ_function(self) -> dict:
        """Generate organ function test results with random but realistic values"""
        test_date = (datetime.now() - timedelta(days=random.randint(1, 90))).strftime("%Y-%m-%d")
        
        # Kidney function - normal range: 90-120 mL/min/1.73m²
        # Occasionally abnormal (15% chance of mild reduction)
        if random.random() < 0.15:
            creatinine_clearance = round(random.uniform(60, 89), 1)
            status_kidney = "mild_reduction"
        else:
            creatinine_clearance = round(random.uniform(90, 120), 1)
            status_kidney = "normal"
        
        serum_creatinine = round(random.uniform(0.6, 1.1), 2)
        
        # Liver function - normal ALT: 7-56 U/L, AST: 10-40 U/L
        # Occasionally elevated (10% chance)
        if random.random() < 0.10:
            alt_value = round(random.uniform(57, 100), 0)
            ast_value = round(random.uniform(41, 80), 0)
            status_liver = "elevated"
        else:
            alt_value = round(random.uniform(10, 50), 0)
            ast_value = round(random.uniform(15, 38), 0)
            status_liver = "normal"
        
        bilirubin_total = round(random.uniform(0.3, 1.0), 2)
        
        return {
            "kidney_function": {
                "creatinine_clearance": {
                    "@id": "http://snomed.info/id/102001005",
                    "snomed:code": "102001005",
                    "rdfs:label": "Creatinine clearance test",
                    "value": creatinine_clearance,
                    "unit": "mL/min/1.73m²",
                    "date": test_date,
                    "normal_range": "90-120 mL/min/1.73m²",
                    "status": status_kidney
                },
                "serum_creatinine": {
                    "value": serum_creatinine,
                    "unit": "mg/dL",
                    "date": test_date,
                    "normal_range": "0.6-1.1 mg/dL",
                    "status": "normal" if serum_creatinine <= 1.1 else "elevated"
                }
            },
            "liver_function": {
                "alt": {
                    "@id": "http://snomed.info/id/102711005",
                    "snomed:code": "102711005",
                    "rdfs:label": "Alanine aminotransferase measurement",
                    "value": alt_value,
                    "unit": "U/L",
                    "date": test_date,
                    "normal_range": "7-56 U/L",
                    "status": status_liver
                },
                "ast": {
                    "@id": "http://snomed.info/id/102712005",
                    "snomed:code": "102712005",
                    "rdfs:label": "Aspartate aminotransferase measurement",
                    "value": ast_value,
                    "unit": "U/L",
                    "date": test_date,
                    "normal_range": "10-40 U/L",
                    "status": status_liver
                },
                "bilirubin_total": {
                    "value": bilirubin_total,
                    "unit": "mg/dL",
                    "date": test_date,
                    "normal_range": "0.1-1.2 mg/dL",
                    "status": "normal" if bilirubin_total <= 1.2 else "elevated"
                }
            },
            "note": "Critical for drug dosing - particularly important for drugs cleared by kidney/liver"
        }
    
    def _generate_lifestyle_factors(self) -> list:
        """Generate lifestyle factors affecting drug metabolism - randomly selected"""
        factors = []
        
        # Smoking status
        smoking_options = [
            {
                "@id": "http://snomed.info/id/228150001",
                "@type": "sdisco:LifestyleFactor",
                "snomed:code": "228150001",
                "rdfs:label": "Non-smoker",
                "skos:prefLabel": "Non-smoker",
                "factor_type": "smoking",
                "status": "never",
                "note": "No CYP1A2 induction from smoking",
                "probability": 0.75  # 75% non-smokers
            },
            {
                "@id": "http://snomed.info/id/77176002",
                "@type": "sdisco:LifestyleFactor",
                "snomed:code": "77176002",
                "rdfs:label": "Smoker",
                "skos:prefLabel": "Smoker",
                "factor_type": "smoking",
                "status": "current",
                "frequency": f"{random.randint(5, 30)} cigarettes/day",
                "note": "CYP1A2 induction from smoking",
                "probability": 0.25  # 25% smokers
            }
        ]
        
        # Select smoking status
        smoking_choice = random.choices(smoking_options, weights=[s["probability"] for s in smoking_options])[0]
        smoking_copy = smoking_choice.copy()
        smoking_copy.pop("probability")
        factors.append(smoking_copy)
        
        # Alcohol consumption
        alcohol_options = [
            {
                "@id": "http://snomed.info/id/228273003",
                "@type": "sdisco:LifestyleFactor",
                "snomed:code": "228273003",
                "rdfs:label": "Drinks alcohol",
                "skos:prefLabel": "Moderate alcohol consumption",
                "factor_type": "alcohol",
                "frequency": f"{random.randint(1, 14)} drinks/week",
                "note": "May affect CYP2E1 and liver function"
            },
            {
                "@id": "http://snomed.info/id/228276006",
                "@type": "sdisco:LifestyleFactor",
                "snomed:code": "228276006",
                "rdfs:label": "Does not drink alcohol",
                "skos:prefLabel": "Non-drinker",
                "factor_type": "alcohol",
                "note": "No alcohol-related drug interactions"
            }
        ]
        factors.append(random.choice(alcohol_options))

        # Exercise frequency (no stable SNOMED code used here yet)
        exercise_choice = random.choice([
            {
                "@type": "sdisco:LifestyleFactor",
                "factor_type": "exercise",
                "rdfs:label": "Regular exercise",
                "frequency": f"{random.randint(2, 7)} times/week",
                "note": "May improve drug metabolism"
            },
            {
                "@type": "sdisco:LifestyleFactor",
                "factor_type": "exercise",
                "rdfs:label": "Sedentary lifestyle",
                "frequency": "Minimal physical activity",
                "note": "May affect drug distribution"
            }
        ])
        factors.append(exercise_choice)

        # Grapefruit consumption (important for CYP3A4)
        if random.random() < 0.3:
            factors.append({
                "@id": "http://snomed.info/id/226529007",
                "@type": "sdisco:LifestyleFactor",
                "snomed:code": "226529007",
                "factor_type": "diet",
                "rdfs:label": "Regular grapefruit consumption",
                "frequency": "Daily",
                "note": "IMPORTANT: Inhibits CYP3A4 - affects many drugs"
            })

        return factors
    
    def _generate_clinical_summary(self, variants: list) -> dict:
        """Generate clinical summary from variants"""
        summary = {
            "total_variants": len(variants),
            "by_significance": {},
            "drug_response_variants": 0,
            "pathogenic_variants": 0,
            "high_impact_genes": []
        }
        
        gene_impact = {}
        
        for variant in variants:
            # Count by significance
            sig = variant.get("clinical_significance", "Unknown")
            summary["by_significance"][sig] = summary["by_significance"].get(sig, 0) + 1
            
            # Count special categories
            if "drug response" in sig.lower():
                summary["drug_response_variants"] += 1
            if "pathogenic" in sig.lower():
                summary["pathogenic_variants"] += 1
            
            # Track gene impact
            gene = variant.get("gene")
            if gene:
                gene_impact[gene] = gene_impact.get(gene, 0) + len(variant.get("drugs", []))
        
        # Identify high-impact genes (>3 drug interactions)
        summary["high_impact_genes"] = [gene for gene, impact in gene_impact.items() if impact > 3]
        
        return summary
    
    def _generate_literature_summary(self, variants: list) -> dict:
        """Generate literature summary from variants with enhanced variant-specific data"""
        total_publications = 0
        total_gene_pubs = 0
        total_variant_pubs = 0
        total_drug_pubs = 0
        genes_with_literature = set()
        drugs_with_literature = set()
        variants_with_literature = set()
        top_publications = []
        
        for variant in variants:
            literature = variant.get("literature", {})
            variant_id = variant.get("variant_id", "Unknown")
            gene = variant.get("gene")
            
            # Count gene publications
            gene_pubs = literature.get("gene_publications", [])
            total_gene_pubs += len(gene_pubs)
            
            # Count variant-specific publications (NEW)
            variant_pubs = literature.get("variant_specific_publications", [])
            total_variant_pubs += len(variant_pubs)
            
            if gene_pubs or variant_pubs:
                genes_with_literature.add(gene)
                
            if variant_pubs:
                variants_with_literature.add(f"{gene}:{variant_id}")
                
            # Collect top publications from gene-level sources
            for pub in gene_pubs:
                if pub.get("citation_count", 0) > 50:  # Lowered threshold for more results
                    top_publications.append({
                        "pmid": pub.get("pmid"),
                        "title": pub.get("title", "")[:100] + "..." if len(pub.get("title", "")) > 100 else pub.get("title", ""),
                        "citation_count": pub.get("citation_count", 0),
                        "gene": gene,
                        "variant": None,  # Gene-level publications don't have specific variants
                        "search_type": "gene-level"
                    })
            
            # Count drug publications
            drug_pubs = literature.get("drug_publications", {})
            for drug, pubs in drug_pubs.items():
                total_drug_pubs += len(pubs)
                if pubs:
                    drugs_with_literature.add(drug)
        
        total_publications = total_gene_pubs + total_variant_pubs + total_drug_pubs
        
        # Sort top publications by citation count
        top_publications.sort(key=lambda x: x.get("citation_count", 0), reverse=True)
        
        return {
            "total_publications": total_publications,
            "gene_publications": total_gene_pubs,
            "variant_specific_publications": total_variant_pubs,
            "drug_publications": total_drug_pubs,
            "genes_with_literature": len(genes_with_literature),
            "variants_with_literature": len(variants_with_literature),
            "drugs_with_literature": len(drugs_with_literature),
            "top_publications": top_publications[:10],  # Top 10 most cited
            "coverage": {
                "genes_covered": list(genes_with_literature),
                "variants_covered": list(variants_with_literature)[:10],
                "drugs_covered": list(drugs_with_literature)[:10]
            }
        }
    
    def _generate_all_outputs(self, profile: dict, gene_results: dict) -> dict:
        """Generate all output formats: JSON-LD, TTL, HTML, Summary JSON, etc."""
        from pathlib import Path
        import json
        
        outputs = {}
        patient_id = profile.get("patient_id", "unknown")
        
        # Create comprehensive output directory
        comp_dir = Path("output/comprehensive")
        comp_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # 1. Comprehensive JSON-LD with all gene knowledge graphs merged
            jsonld_file = comp_dir / f"{patient_id}_comprehensive.jsonld"
            
            # Merge all gene knowledge graphs into the profile
            comprehensive_jsonld = profile.copy()
            
            # Load and merge each gene's knowledge graph
            json_output_dir = Path("output/json")
            if json_output_dir.exists():
                all_variants_detailed = []
                
                for gene in gene_results.keys():
                    gene_kg_file = json_output_dir / f"{gene}_knowledge_graph.jsonld"
                    if gene_kg_file.exists():
                        try:
                            with open(gene_kg_file, 'r', encoding='utf-8') as f:
                                gene_kg = json.load(f)
                            
                            # Extract variants from gene knowledge graph
                            if isinstance(gene_kg, dict):
                                # Check for variants in various possible locations
                                if 'variants' in gene_kg:
                                    all_variants_detailed.extend(gene_kg['variants'])
                                elif '@graph' in gene_kg:
                                    # If using @graph format, extract variant nodes
                                    for node in gene_kg['@graph']:
                                        if node.get('@type') in ['Variant', 'GeneticVariant', 'pgx:Variant']:
                                            all_variants_detailed.append(node)
                                
                        except Exception as e:
                            print(f"Error merging {gene} knowledge graph: {e}")
                
                # Add all detailed variants to comprehensive profile
                if all_variants_detailed:
                    comprehensive_jsonld['variants'] = all_variants_detailed
            
            # Merge patient-specific variant annotations into detailed variants (if present)
            try:
                if isinstance(comprehensive_jsonld.get('variants'), list) and isinstance(profile.get('variants'), list):
                    # Build lookup from original enriched variants by rsid/variant_id
                    enriched_map = {}
                    for v in profile.get('variants', []):
                        key = v.get('rsid') or v.get('variant_id')
                        if not key:
                            # Fallback: try genomic location
                            gl = None
                            try:
                                glc = v.get('raw_data', {}).get('genomicLocation')
                                if isinstance(glc, list) and glc:
                                    gl = glc[0]
                            except Exception:
                                gl = None
                            key = gl
                        if key:
                            enriched_map[str(key)] = v
                    merged_variants = []
                    for dv in comprehensive_jsonld.get('variants', []):
                        dv_key = dv.get('rsid') or dv.get('variant_id') or dv.get('id')
                        if not dv_key:
                            # Fallback: attempt to use genomicLocation or similar field
                            gl2 = dv.get('genomicLocation')
                            if isinstance(gl2, list) and gl2:
                                dv_key = gl2[0]
                        ev = enriched_map.get(str(dv_key)) if dv_key else None
                        if ev:
                            # Attach patient-specific population context fields if missing
                            for k in (
                                'population_frequencies',
                                'patient_population_frequency',
                                'population_significance',
                                'ethnicity_context',
                                'population_frequency_source',
                            ):
                                if k not in dv and k in ev:
                                    dv[k] = ev[k]
                        merged_variants.append(dv)
                    comprehensive_jsonld['variants'] = merged_variants
            except Exception:
                pass
            
            # Save comprehensive JSON-LD
            with open(jsonld_file, 'w', encoding='utf-8') as f:
                json.dump(comprehensive_jsonld, f, indent=2)
            outputs["JSON-LD"] = str(jsonld_file)
            
            # 2. Turtle RDF
            ttl_file = comp_dir / f"{patient_id}_comprehensive.ttl"
            ttl_content = self._generate_ttl_from_profile(profile)
            with open(ttl_file, 'w', encoding='utf-8') as f:
                f.write(ttl_content)
            outputs["TTL"] = str(ttl_file)
            
            # 3. HTML Report
            html_file = comp_dir / f"{patient_id}_comprehensive_report.html"
            html_content = self._generate_html_report(profile, gene_results)
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            outputs["HTML"] = str(html_file)
            
            # 4. Summary JSON (simplified for dashboards)
            summary_file = comp_dir / f"{patient_id}_summary.json"
            summary = self._generate_summary_json(profile, gene_results)
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2)
            outputs["Summary JSON"] = str(summary_file)
            
            # 5. Drug Interaction Matrix JSON
            drug_matrix_file = comp_dir / f"{patient_id}_drug_matrix.json"
            drug_matrix = self._create_drug_matrix(profile["variants"])
            with open(drug_matrix_file, 'w', encoding='utf-8') as f:
                json.dump(drug_matrix, f, indent=2)
            outputs["Drug Matrix JSON"] = str(drug_matrix_file)
            
            # 6. Clinical Conflict Report JSON
            if "variant_linking" in profile:
                conflict_file = comp_dir / f"{patient_id}_conflicts.json"
                conflict_data = {
                    "conflicts": profile["variant_linking"].get("conflicts", []),
                    "links": profile["variant_linking"].get("links", {}),
                    "summary": profile["variant_linking"].get("summary", {})
                }
                with open(conflict_file, 'w', encoding='utf-8') as f:
                    json.dump(conflict_data, f, indent=2)
                outputs["Conflict Report JSON"] = str(conflict_file)
            
            # 7. Add gene-specific knowledge graphs from output/json directory
            json_output_dir = Path("output/json")
            if json_output_dir.exists():
                for gene in gene_results.keys():
                    gene_jsonld = json_output_dir / f"{gene}_knowledge_graph.jsonld"
                    if gene_jsonld.exists():
                        outputs[f"{gene} Knowledge Graph"] = str(gene_jsonld)
            
            # 8. Add gene-specific RDF graphs from output/rdf directory
            rdf_output_dir = Path("output/rdf")
            if rdf_output_dir.exists():
                for gene in gene_results.keys():
                    gene_ttl = rdf_output_dir / f"{gene}_knowledge_graph.ttl"
                    if gene_ttl.exists():
                        outputs[f"{gene} RDF Graph"] = str(gene_ttl)
            
        except Exception as e:
            print(f"Error generating outputs: {e}")
            outputs["error"] = str(e)
        
        return outputs
    
    def _generate_summary_json(self, profile: dict, gene_results: dict) -> dict:
        """Generate simplified summary JSON for dashboard display."""
        return {
            "patient_id": profile.get("patient_id"),
            "analysis_date": profile.get("dateCreated"),
            "summary": {
                "genes_analyzed": len(gene_results),
                "total_variants": sum(len(r.get("variants", [])) for r in gene_results.values()),
                "high_impact_findings": len(profile.get("pharmacogenomics_profile", {}).get("clinical_summary", {}).get("high_impact_genes", [])),
                "drug_interactions": len(profile.get("pharmacogenomics_profile", {}).get("affected_drugs", []))
            },
            "gene_summary": {
                gene: {
                    "success": result.get("success", False),
                    "variants_processed": result.get("variants_processed", 0),
                    "duration": result.get("duration", 0)
                }
                for gene, result in gene_results.items()
            },
            "clinical_recommendations": self._generate_clinical_recommendations_summary(profile, gene_results)
        }
    
    def _generate_clinical_recommendations_summary(self, profile: dict, gene_results: dict) -> list:
        """Generate clinical recommendations summary"""
        recommendations = []
        
        # Analyze variants for high-impact findings
        for variant in profile.get("variants", []):
            clinical_sig = variant.get("clinical_significance", "")
            gene = variant.get("gene")
            
            if "pathogenic" in clinical_sig.lower():
                recommendations.append({
                    "type": "genetic_risk",
                    "priority": "high",
                    "gene": gene,
                    "variant": variant.get("variant_id"),
                    "recommendation": f"Monitor for {gene}-related adverse effects"
                })
            
            # Drug-specific recommendations
            for drug in variant.get("drugs", []):
                if drug.get("recommendation"):
                    recommendations.append({
                        "type": "drug_response",
                        "priority": "medium",
                        "gene": gene,
                        "drug": drug.get("name"),
                        "recommendation": drug.get("recommendation")[:100]
                    })
        
        return recommendations[:10]  # Limit to top 10
    
    def _create_drug_matrix(self, variants: list) -> dict:
        """Create drug-gene interaction matrix"""
        matrix = {}
        
        for variant in variants:
            gene = variant.get("gene")
            for drug_info in variant.get("drugs", []):
                drug_name = drug_info.get("name")
                if drug_name and gene:
                    if drug_name not in matrix:
                        matrix[drug_name] = {}
                    
                    matrix[drug_name][gene] = {
                        "variant": variant.get("variant_id"),
                        "recommendation": drug_info.get("recommendation"),
                        "evidence_level": drug_info.get("evidence_level"),
                        "clinical_significance": variant.get("clinical_significance")
                    }
        
        return matrix
    
    def _generate_ttl_from_profile(self, profile: dict) -> str:
        """Generate TTL (Turtle) content from comprehensive profile"""
        try:
            from rdflib import Graph, URIRef, Literal, Namespace
            from rdflib.namespace import RDF, RDFS, XSD
            
            # Create graph
            g = Graph()
            
            # Define namespaces
            FOAF = Namespace("http://xmlns.com/foaf/0.1/")
            SCHEMA = Namespace("http://schema.org/")
            PGX = Namespace("http://pgx-kg.org/")
            SNOMED = Namespace("http://snomed.info/id/")
            
            # Bind namespaces
            g.bind("foaf", FOAF)
            g.bind("schema", SCHEMA)
            g.bind("pgx", PGX)
            g.bind("snomed", SNOMED)
            
            # Add patient
            patient_uri = URIRef(profile["@id"])
            g.add((patient_uri, RDF.type, FOAF.Person))
            g.add((patient_uri, RDF.type, SCHEMA.Person))
            g.add((patient_uri, SCHEMA.identifier, Literal(profile["identifier"])))
            g.add((patient_uri, SCHEMA.name, Literal(profile["name"])))
            g.add((patient_uri, SCHEMA.description, Literal(profile["description"])))
            
            # Add pharmacogenomics profile
            pgx_profile = profile.get("pharmacogenomics_profile", {})
            if "genes_analyzed" in pgx_profile:
                for gene in pgx_profile["genes_analyzed"]:
                    gene_uri = URIRef(f"http://identifiers.org/ncbigene/{gene}")
                    g.add((patient_uri, PGX.hasGene, gene_uri))
                    g.add((gene_uri, RDF.type, PGX.Gene))
                    g.add((gene_uri, SCHEMA.name, Literal(gene)))
            
            # Add variants
            def _extract_rsid(v: dict) -> str:
                """Return canonical rsID from any known fields/xrefs; empty string if not found."""
                try:
                    # direct fields
                    for key in ["rsid", "dbsnp_id", "dbsnp", "variant_id"]:
                        val = str(v.get(key, "")).strip()
                        if val.lower().startswith("rs"):
                            return val
                    # xrefs list
                    for xr in (v.get("xrefs", []) or []):
                        name = str(xr.get("name", "")).lower()
                        vid = str(xr.get("id", "")).strip()
                        if name in ("dbsnp", "rsid") and vid:
                            return vid if vid.lower().startswith("rs") else f"rs{vid}"
                    # nested clinvar
                    cv = v.get("clinvar", {}) or {}
                    for k in ["rsid", "dbsnp", "dbsnp_id"]:
                        val = str(cv.get(k, "")).strip()
                        if val.lower().startswith("rs"):
                            return val
                    # generic identifiers dict
                    ids = v.get("identifiers", {}) or {}
                    for _, val in (ids.items() if isinstance(ids, dict) else []):
                        sval = str(val).strip()
                        if sval.lower().startswith("rs"):
                            return sval
                except Exception:
                    return ""
                return ""

            for variant in profile.get("variants", []):
                rsid = _extract_rsid(variant)
                if not rsid:
                    # Skip non-rs variants to avoid inventing identifiers; upstream should supply rsIDs
                    continue
                variant_uri = URIRef(f"http://identifiers.org/dbsnp/{rsid}")
                g.add((variant_uri, RDF.type, PGX.Variant))
                g.add((variant_uri, SCHEMA.identifier, Literal(variant.get("variant_id", ""))))
                g.add((variant_uri, PGX.affectsGene, URIRef(f"http://identifiers.org/ncbigene/{variant.get('gene', '')}")))
                g.add((patient_uri, PGX.hasVariant, variant_uri))
            
            return g.serialize(format="turtle")
            
        except ImportError:
            return f"# TTL export requires rdflib library\n# Patient: {profile.get('identifier')}\n# Genes: {', '.join(profile.get('pharmacogenomics_profile', {}).get('genes_analyzed', []))}\n"
    
    def _generate_html_report(self, profile: dict, gene_results: dict) -> str:
        """Generate HTML report from comprehensive profile"""
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Comprehensive Pharmacogenomics Report - {profile.get('identifier', 'Unknown')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
        .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }}
        .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        .gene-result {{ background: #f8f9fa; margin: 10px 0; padding: 10px; border-radius: 3px; }}
        .variant {{ background: #e9ecef; margin: 5px 0; padding: 8px; border-radius: 3px; }}
        .conflict {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; margin: 5px 0; border-radius: 3px; }}
        .critical {{ background: #f8d7da; border: 1px solid #f5c6cb; }}
        .warning {{ background: #fff3cd; border: 1px solid #ffeaa7; }}
        .info {{ background: #d1ecf1; border: 1px solid #bee5eb; }}
        table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🧬 Comprehensive Pharmacogenomics Report</h1>
        <p><strong>Patient ID:</strong> {profile.get('identifier', 'Unknown')}</p>
        <p><strong>Generated:</strong> {profile.get('dateCreated', 'Unknown')}</p>
        <p><strong>Description:</strong> {profile.get('description', 'No description')}</p>
    </div>
    
    <div class="section">
        <h2>📊 Analysis Summary</h2>
        <p><strong>Genes Analyzed:</strong> {', '.join(profile.get('pharmacogenomics_profile', {}).get('genes_analyzed', []))}</p>
        <p><strong>Total Variants:</strong> {profile.get('pharmacogenomics_profile', {}).get('total_variants', 0)}</p>
        <p><strong>Affected Drugs:</strong> {len(profile.get('pharmacogenomics_profile', {}).get('affected_drugs', []))}</p>
        <p><strong>Associated Diseases:</strong> {len(profile.get('pharmacogenomics_profile', {}).get('associated_diseases', []))}</p>
    </div>
    
    <div class="section">
        <h2>🧪 Gene Analysis Results</h2>
"""
        
        # Add gene results
        for gene, result in gene_results.items():
            status = "✅ Success" if result.get("success", False) else "❌ Failed"
            html += f"""
        <div class="gene-result">
            <h3>{gene} {status}</h3>
            <p><strong>Variants Processed:</strong> {result.get('variants_processed', 0)}</p>
            {f"<p><strong>Error:</strong> {result.get('error', '')}</p>" if not result.get('success', False) else ""}
        </div>
"""
        
        html += """
    </div>
    
    <div class="section">
        <h2>🧬 Variants</h2>
"""
        
        # Add variants
        for variant in profile.get("variants", []):
            html += f"""
        <div class="variant">
            <h4>{variant.get('variant_id', 'Unknown')}</h4>
            <p><strong>Gene:</strong> {variant.get('gene', 'Unknown')}</p>
            <p><strong>Clinical Significance:</strong> {variant.get('clinical_significance', 'Unknown')}</p>
            <p><strong>Drugs Affected:</strong> {len(variant.get('drugs', []))}</p>
"""
            # Ethnicity-aware population frequencies (if available)
            freqs = variant.get('population_frequencies') or {}
            patient_pf = variant.get('patient_population_frequency')
            pop_sig = variant.get('population_significance')
            context = variant.get('ethnicity_context')
            if freqs or patient_pf is not None:
                def fmt_pct(x):
                    return f"{round(x*100, 1)}%" if isinstance(x, (int, float)) else "N/A"
                html += """
            <p><strong>Population Frequencies:</strong></p>
            <ul>
"""
                for k in ["African", "Asian", "Caucasian/European", "Hispanic/Latino"]:
                    v = freqs.get(k)
                    html += f"<li>{k}: {fmt_pct(v)}</li>"
                html += """
            </ul>
"""
                if patient_pf is not None:
                    html += f"<p><strong>Patient Ethnicity Frequency:</strong> {fmt_pct(patient_pf)} ({pop_sig or 'unknown'})</p>"
                if context:
                    html += f"<p><em>{context}</em></p>"
            html += """
        </div>
"""
        
        # Ethnicity-aware medication adjustment hints (if available)
        adjustments = profile.get("ethnicity_medication_adjustments", [])
        if adjustments:
            html += """
    </div>
    
    <div class="section">
        <h2>🌍 Ethnicity-aware Medication Considerations</h2>
"""
            for adj in adjustments:
                html += f"""
        <div class="variant">
            <h4>{adj.get('drug', 'Medication')}</h4>
            <p><strong>Gene:</strong> {adj.get('gene', 'Unknown')}</p>
            <p><strong>Adjustment:</strong> {adj.get('adjustment', 'N/A')} ({adj.get('strength', 'info')})</p>
            <p>{adj.get('rationale', '')}</p>
        </div>
"""
        
        # Add variant linking and conflicts if available
        if "variant_linking" in profile:
            linking = profile["variant_linking"]
            html += """
    </div>
    
    <div class="section">
        <h2>⚠️ Variant Linking & Conflicts</h2>
"""
            
            # Add conflicts
            conflicts = linking.get("conflicts", [])
            if conflicts:
                html += f"<p><strong>Total Conflicts:</strong> {len(conflicts)}</p>"
                for conflict in conflicts:
                    severity_class = conflict.get("severity", "info").lower()
                    html += f"""
        <div class="conflict {severity_class}">
            <h4>{conflict.get('title', 'Unknown Conflict')}</h4>
            <p><strong>Severity:</strong> {conflict.get('severity', 'Unknown')}</p>
            <p><strong>Description:</strong> {conflict.get('description', 'No description')}</p>
        </div>
"""
            else:
                html += "<p>No conflicts detected.</p>"
        
        html += f"""
    </div>
    
    <div class="section">
        <h2>📋 Data Sources</h2>
        <p>{profile.get('dataSource', 'Unknown data sources')}</p>
    </div>
    
</body>
</html>
"""
        
        return html

    def _assign_exact_rsid(self, variants: list) -> list:
        """Assign exact dbSNP rsID for each variant using allele tuple when available.

        Expected variant keys (best-effort): 'chrom', 'position' or 'pos', 'ref', 'alt'.
        If 'rsid' already present, keep it. Else, prefer xrefs rsid only if allele matches.
        """
        def pick_rsid(v: dict) -> str:
            rs = str(v.get('rsid', '')).strip()
            if rs.lower().startswith('rs'):
                return rs
            # try exact match from xrefs with allele
            alt = str(v.get('alt') or v.get('alternate') or '').upper()
            xrefs = v.get('xrefs', []) or []
            for xr in xrefs:
                name = str(xr.get('name', '')).lower()
                vid = str(xr.get('id', '')).strip()
                xr_alt = str(xr.get('allele', '')).upper()
                if name in ('dbsnp', 'rsid') and vid and (not alt or not xr_alt or xr_alt == alt):
                    return vid if vid.lower().startswith('rs') else f"rs{vid}"
            # try clinvar section
            cv = v.get('clinvar', {}) or {}
            for k in ('rsid', 'dbsnp', 'dbsnp_id'):
                val = str(cv.get(k, '')).strip()
                if val.lower().startswith('rs'):
                    return val
            return ''

        for v in variants:
            rsid = pick_rsid(v)
            if rsid:
                v['rsid'] = rsid
        return variants


# Legacy class for backward compatibility
class PGxKGPipeline(PGxPipeline):
    """Legacy class name for backward compatibility"""
    pass


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="PGx-KG: Build pharmacogenomics knowledge graphs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single gene analysis
  python src/main.py --gene CYP2D6
  python src/main.py --gene CYP2C19 --protein P33261
  
  # Multi-gene comprehensive analysis
  python src/main.py --genes CYP2D6 CYP2C19 CYP3A4
  python src/main.py --genes CYP2D6 CYP2C19 CYP3A4 DPYD TPMT
  
  # Custom configuration
  python src/main.py --gene CYP3A4 --config custom_config.yaml

For more information, see README.md
        """
    )
    
    parser.add_argument(
        "--gene",
        help="Single gene symbol (e.g., CYP2D6, CYP2C19)"
    )
    
    parser.add_argument(
        "--genes",
        nargs="+",
        help="Multiple gene symbols (e.g., --genes CYP2D6 CYP2C19 CYP3A4)"
    )
    
    parser.add_argument(
        "--protein",
        help="UniProt protein ID (optional, will be fetched if not provided)"
    )
    
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.gene and not args.genes:
        parser.error("Must specify either --gene or --genes")
    
    if args.gene and args.genes:
        parser.error("Cannot specify both --gene and --genes")
    
    # Run pipeline
    pipeline = PGxPipeline(config_path=args.config)
    
    if args.genes:
        # Multi-gene mode
        result = pipeline.run_multi_gene(args.genes)
    else:
        # Single-gene mode
        result = pipeline.run(args.gene, args.protein)
    
    # Exit with appropriate code
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
