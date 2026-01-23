"""PDF Generation Utility for Immunization Reports"""
from io import BytesIO
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from app.models.beneficiary import Beneficiary


async def generate_immunization_report_pdf(
    beneficiary: Beneficiary,
    timeline_data: dict,
    administered_vaccines: list
) -> bytes:
    """
    Generate a PDF immunization report showing only administered vaccines
    
    Args:
        beneficiary: Beneficiary model instance
        timeline_data: Timeline data dictionary
        administered_vaccines: List of administered vaccination items
    
    Returns:
        PDF file as bytes
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20*mm, bottomMargin=20*mm)
    
    # Container for PDF elements
    elements = []
    styles = getSampleStyleSheet()
    
    # Title Style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#3B82F6'),
        alignment=TA_CENTER,
        spaceAfter=10
    )
    
    # Header
    title = Paragraph("Immunization Report", title_style)
    elements.append(title)
    elements.append(Spacer(1, 10*mm))
    
    # Beneficiary Information
    beneficiary_name = f"{beneficiary.first_name} {beneficiary.last_name}"
    dob_str = beneficiary.date_of_birth.strftime("%B %d, %Y") if beneficiary.date_of_birth else "N/A"
    
    info_data = [
        ["Name:", beneficiary_name],
        ["Date of Birth:", dob_str],
        ["Gender:", beneficiary.gender or "N/A"],
    ]
    
    info_table = Table(info_data, colWidths=[60*mm, 120*mm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(Paragraph("<b>Beneficiary Information</b>", styles['Heading2']))
    elements.append(Spacer(1, 5*mm))
    elements.append(info_table)
    elements.append(Spacer(1, 10*mm))
    
    # Administered Vaccines Table
    if administered_vaccines:
        elements.append(Paragraph(
            f"<b>Administered Vaccinations ({len(administered_vaccines)} total)</b>",
            styles['Heading2']
        ))
        elements.append(Spacer(1, 5*mm))
        
        # Table headers
        table_data = [["Vaccine Name", "Dose", "Date Administered", "Batch Number", "Manufacturer"]]
        
        # Add vaccine data
        for vaccine in administered_vaccines:
            vaccine_name = vaccine.get("vaccine_name", "N/A")
            dose = vaccine.get("dose", "N/A")
            vaccinated_on = vaccine.get("vaccinated_on")
            vaccinated_date = vaccinated_on.strftime("%B %d, %Y") if vaccinated_on else "N/A"
            batch_number = vaccine.get("batch_number", "N/A")
            manufacturer = vaccine.get("manufacturer", "N/A")
            
            table_data.append([
                vaccine_name,
                dose,
                vaccinated_date,
                batch_number,
                manufacturer
            ])
        
        # Create table
        vaccine_table = Table(table_data, colWidths=[60*mm, 30*mm, 40*mm, 30*mm, 40*mm])
        vaccine_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3B82F6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            # Data rows
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
        ]))
        
        elements.append(vaccine_table)
    else:
        elements.append(Paragraph(
            "<i>No administered vaccinations recorded yet.</i>",
            styles['Normal']
        ))
    
    elements.append(Spacer(1, 15*mm))
    
    # Footer
    footer_text = f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
    footer = Paragraph(footer_text, ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER
    ))
    elements.append(footer)
    
    # Build PDF
    doc.build(elements)
    
    # Get PDF bytes
    buffer.seek(0)
    pdf_bytes = buffer.read()
    buffer.close()
    
    return pdf_bytes




