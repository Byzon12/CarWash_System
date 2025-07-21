import io
from django.db.models import Q, Sum,Count
import pandas as pd
from django.http import HttpResponse
from django.template.loader import render_to_string
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from decimal import Decimal
import xlsxwriter
from datetime import datetime

class ReportGenerator:
    """Generate various types of reports"""
    
    def __init__(self, tenant):
        self.tenant = tenant
    
    def generate_financial_summary(self, start_date, end_date, locations=None):
        """Generate financial summary report"""
        from booking.models import booking
        
        # Base query
        query = booking.objects.filter(
            location__tenant=self.tenant,
            created_at__date__range=[start_date, end_date]
        )
        
        if locations:
            query = query.filter(location__id__in=locations)
        
        # Revenue calculations
        paid_bookings = query.filter(payment_status='paid')
        
        summary = {
            'period': f"{start_date} to {end_date}",
            'total_bookings': query.count(),
            'paid_bookings': paid_bookings.count(),
            'total_revenue': paid_bookings.aggregate(
                total=Sum('total_amount')
            )['total'] or Decimal('0.00'),
            'payment_breakdown': paid_bookings.values('payment_method').annotate(
                count=Count('id'),
                revenue=Sum('total_amount')
            ),
            'location_breakdown': paid_bookings.values(
                'location__name'
            ).annotate(
                count=Count('id'),
                revenue=Sum('total_amount')
            ).order_by('-revenue')
        }
        
        return summary
    
    def generate_operational_summary(self, start_date, end_date):
        """Generate operational performance summary"""
        from Tenant.models import Task
        from Staff.models import StaffProfile
        
        tasks_query = Task.objects.filter(
            tenant=self.tenant,
            created_at__date__range=[start_date, end_date]
        )
        
        summary = {
            'period': f"{start_date} to {end_date}",
            'total_tasks': tasks_query.count(),
            'completed_tasks': tasks_query.filter(status='completed').count(),
            'overdue_tasks': tasks_query.filter(status='overdue').count(),
            'staff_performance': StaffProfile.objects.filter(
                tenant=self.tenant
            ).annotate(
                assigned_tasks=Count('tasks', filter=Q(
                    tasks__created_at__date__range=[start_date, end_date]
                )),
                completed_tasks=Count('tasks', filter=Q(
                    tasks__status='completed',
                    tasks__created_at__date__range=[start_date, end_date]
                ))
            ).values('username', 'assigned_tasks', 'completed_tasks')
        }
        
        return summary

class ReportExporter:
    """Export reports in various formats"""
    
    def export_to_pdf(self, data, report_type, tenant_name):
        """Export report data to PDF"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        
        title = Paragraph(f"{report_type.title()} Report - {tenant_name}", title_style)
        story.append(title)
        story.append(Spacer(1, 20))
        
        # Period info
        if 'period' in data:
            period_para = Paragraph(f"<b>Period:</b> {data['period']}", styles['Normal'])
            story.append(period_para)
            story.append(Spacer(1, 12))
        
        # Summary table
        if report_type == 'financial':
            self._add_financial_tables(story, data, styles)
        elif report_type == 'operational':
            self._add_operational_tables(story, data, styles)
        
        doc.build(story)
        buffer.seek(0)
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{report_type}_report.pdf"'
        response.write(buffer.getvalue())
        buffer.close()
        
        return response
    
    def _add_financial_tables(self, story, data, styles):
        """Add financial data tables to PDF"""
        # Summary table
        summary_data = [
            ['Metric', 'Value'],
            ['Total Bookings', str(data.get('total_bookings', 0))],
            ['Paid Bookings', str(data.get('paid_bookings', 0))],
            ['Total Revenue', f"KES {data.get('total_revenue', 0)}"],
        ]
        
        summary_table = Table(summary_data)
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(Paragraph("<b>Financial Summary</b>", styles['Heading2']))
        story.append(summary_table)
        story.append(Spacer(1, 20))
        
        # Payment breakdown
        if 'payment_breakdown' in data and data['payment_breakdown']:
            payment_data = [['Payment Method', 'Count', 'Revenue']]
            for item in data['payment_breakdown']:
                payment_data.append([
                    item['payment_method'].title(),
                    str(item['count']),
                    f"KES {item['revenue']}"
                ])
            
            payment_table = Table(payment_data)
            payment_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(Paragraph("<b>Payment Method Breakdown</b>", styles['Heading2']))
            story.append(payment_table)
    
    def export_to_excel(self, data, report_type, tenant_name):
        """Export report data to Excel"""
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        
        # Create worksheet
        worksheet = workbook.add_worksheet(f"{report_type.title()} Report")
        
        # Add formats
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'align': 'center'
        })
        
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D7E4BC',
            'border': 1
        })
        
        # Add title
        worksheet.merge_range('A1:D1', f"{report_type.title()} Report - {tenant_name}", title_format)
        worksheet.write('A2', f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        if report_type == 'financial':
            self._add_financial_excel_data(worksheet, data, header_format)
        elif report_type == 'operational':
            self._add_operational_excel_data(worksheet, data, header_format)
        
        workbook.close()
        output.seek(0)
        
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{report_type}_report.xlsx"'
        
        return response
    
    def _add_financial_excel_data(self, worksheet, data, header_format):
        """Add financial data to Excel worksheet"""
        row = 4
        
        # Summary section
        worksheet.write(row, 0, "Financial Summary", header_format)
        row += 1
        
        summary_items = [
            ('Total Bookings', data.get('total_bookings', 0)),
            ('Paid Bookings', data.get('paid_bookings', 0)),
            ('Total Revenue', f"KES {data.get('total_revenue', 0)}"),
        ]
        
        for item, value in summary_items:
            worksheet.write(row, 0, item)
            worksheet.write(row, 1, value)
            row += 1
        
        row += 2
        
        # Payment breakdown
        if 'payment_breakdown' in data and data['payment_breakdown']:
            worksheet.write(row, 0, "Payment Method Breakdown", header_format)
            row += 1
            
            headers = ['Payment Method', 'Count', 'Revenue']
            for col, header in enumerate(headers):
                worksheet.write(row, col, header, header_format)
            row += 1
            
            for item in data['payment_breakdown']:
                worksheet.write(row, 0, item['payment_method'].title())
                worksheet.write(row, 1, item['count'])
                worksheet.write(row, 2, f"KES {item['revenue']}")
                row += 1
    
    def export_to_csv(self, data, report_type):
        """Export report data to CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{report_type}_report.csv"'
        
        if report_type == 'financial':
            df = pd.DataFrame(data.get('payment_breakdown', []))
        elif report_type == 'operational':
            df = pd.DataFrame(data.get('staff_performance', []))
        else:
            df = pd.DataFrame([data])
        
        df.to_csv(path_or_buf=response, index=False)
        return response