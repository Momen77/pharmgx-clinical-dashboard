"""
PDF exporter using ReportLab
Creates professional medical reports with patient photos
"""
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from PIL import Image as PILImage
import io
import os
from pathlib import Path
from datetime import datetime


class PDFExporter:
    """Export clinical reports to PDF using ReportLab"""
    
    # Ghent University colors
    UGENT_BLUE = colors.HexColor('#1E64C8')
    UGENT_YELLOW = colors.HexColor('#FFD200')
    ALERT_RED = colors.HexColor('#DC3545')
    ALERT_GREEN = colors.HexColor('#28A745')
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='UGentTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=self.UGENT_BLUE,
            spaceAfter=12,
            alignment=TA_CENTER
        ))
        
        # Patient name style
        self.styles.add(ParagraphStyle(
            name='PatientName',
            parent=self.styles['Heading1'],
            fontSize=20,
            textColor=self.UGENT_BLUE,
            spaceAfter=6
        ))
        
        # Alert styles
        self.styles.add(ParagraphStyle(
            name='AlertCritical',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.white,
            backColor=self.ALERT_RED,
            spaceAfter=6
        ))
    
    def create_pdf(self, patient_profile: dict, test_results: dict, output_path: str):
        """
        Create PDF report
        
        Args:
            patient_profile: Patient demographics and information
            test_results: Test results from pipeline
            output_path: Path to save PDF file
        """
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        story = []
        
        # Cover page
        story.extend(self._create_cover_page(patient_profile, test_results))
        story.append(PageBreak())
        
        # Summary page
        story.extend(self._create_summary_page(test_results))
        story.append(PageBreak())
        
        # Gene results
        story.extend(self._create_gene_results(test_results))
        
        # Build PDF
        doc.build(story)
        return output_path
    
    def _create_cover_page(self, patient_profile: dict, test_results: dict):
        """Create cover page with patient photo and UGent logo"""
        elements = []

        # Add UGent logo at the top
        try:
            # Get project root (go up from src/dashboard to project root)
            dashboard_dir = Path(__file__).parent
            project_root = dashboard_dir.parent.parent
            logo_path = project_root / "assets" / "ugent_faculty_logo.png"

            if logo_path.exists():
                logo_img = Image(str(logo_path), width=2.5*inch, height=2.5*inch, kind='proportional')
                elements.append(logo_img)
                elements.append(Spacer(1, 0.2*inch))

                # Add institution text
                institution = Paragraph(
                    "<para align='center'><b>Ghent University</b><br/>Faculty of Pharmaceutical Sciences<br/>Pharmacogenomics Laboratory</para>",
                    self.styles['Normal']
                )
                elements.append(institution)
                elements.append(Spacer(1, 0.3*inch))
        except Exception as e:
            # If logo loading fails, continue without it
            pass

        # Title
        title = Paragraph("Pharmacogenomics Test Report", self.styles['UGentTitle'])
        elements.append(title)
        elements.append(Spacer(1, 0.5*inch))
        
        # Patient photo
        if patient_profile.get('photo'):
            try:
                img = PILImage.open(io.BytesIO(patient_profile['photo']))
                img.thumbnail((200, 200))
                img_buffer = io.BytesIO()
                img.save(img_buffer, format='PNG')
                img_buffer.seek(0)
                patient_img = Image(img_buffer, width=2*inch, height=2*inch)
                elements.append(patient_img)
                elements.append(Spacer(1, 0.3*inch))
            except:
                pass
        
        # Patient information
        demo = patient_profile.get('demographics', {})
        patient_name = f"{demo.get('first_name', '')} {demo.get('last_name', '')}"
        name_para = Paragraph(patient_name, self.styles['PatientName'])
        elements.append(name_para)
        
        # Demographics table
        data = [
            ['MRN:', demo.get('mrn', 'N/A')],
            ['Date of Birth:', demo.get('date_of_birth', 'N/A')],
            ['Age:', f"{demo.get('age', 'N/A')} years"],
            ['Test Date:', datetime.now().strftime('%Y-%m-%d')]
        ]
        
        table = Table(data, colWidths=[2*inch, 4*inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(table)
        
        return elements
    
    def _create_summary_page(self, test_results: dict):
        """Create summary page"""
        elements = []
        
        title = Paragraph("Executive Summary", self.styles['Heading1'])
        elements.append(title)
        elements.append(Spacer(1, 0.3*inch))
        
        # Summary metrics
        genes = test_results.get('genes', [])
        variants = test_results.get('total_variants', 0)
        
        summary_data = [
            ['Genes Analyzed:', str(len(genes))],
            ['Total Variants:', str(variants)],
            ['Critical Alerts:', str(test_results.get('comprehensive_outputs', {}).get('critical_conflicts', 0))]
        ]
        
        table = Table(summary_data, colWidths=[3*inch, 3*inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(table)
        
        return elements
    
    def _create_gene_results(self, test_results: dict):
        """Create gene results section"""
        elements = []
        
        title = Paragraph("Gene Results", self.styles['Heading1'])
        elements.append(title)
        elements.append(Spacer(1, 0.3*inch))
        
        genes = test_results.get('genes', [])
        for gene in genes:
            gene_title = Paragraph(f"**{gene}**", self.styles['Heading2'])
            elements.append(gene_title)
            elements.append(Spacer(1, 0.2*inch))
            
            # Placeholder for gene results
            para = Paragraph(f"Detailed results for {gene} will be displayed here.", self.styles['Normal'])
            elements.append(para)
            elements.append(Spacer(1, 0.3*inch))
        
        return elements

