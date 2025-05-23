from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from django.http import HttpResponse

def generate_operations_pdf(operations_queryset, field_name):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="operations_report_{field_name.replace(" ", "_")}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=landscape(letter))
    elements = []
    styles = getSampleStyleSheet()

    title = f"Agrotechnical Operations Report for Field: {field_name}"
    elements.append(Paragraph(title, styles['h1']))
    elements.append(Spacer(1, 0.25*72)) # 0.25 inch space

    data = [
        ["Date", "Operation Type", "Crop", "Description", "Equipment", "Cost", "User"]
    ]

    for op in operations_queryset:
        data.append([
            op.operation_date.strftime('%Y-%m-%d'),
            op.operation_type.name,
            op.crop.name if op.crop else "N/A",
            Paragraph(op.description, styles['Normal']), # Wrap text in description
            op.equipment_used or "N/A",
            f"{op.materials_cost:.2f}" if op.materials_cost is not None else "N/A",
            op.user.username if op.user else "N/A"
        ])

    table = Table(data, colWidths=[doc.width/7.0]*7) # Adjust colWidths as needed
    
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('WORDWRAP', (3, 1), (3, -1), 'CJK'), # Allow word wrap for description
    ])
    table.setStyle(style)
    elements.append(table)

    doc.build(elements)
    return response
