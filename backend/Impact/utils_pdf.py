"""
PDF generation utilities for FloodWatch reports using ReportLab.
"""
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def generate_discharge_chart(station_id, station_feature):
    """
    Generate a time series chart for discharge data.

    Args:
        station_id: The station ID
        station_feature: The GeoJSON feature containing station data

    Returns:
        BytesIO: Chart image as bytes, or None if no data
    """
    try:
        props = station_feature.get('properties', {})

        # Get time series data
        time_period_str = props.get('time_period', '')
        discharge_gfs = props.get('time_series_discharge_simulated-gfs', '')
        discharge_icon = props.get('time_series_discharge_simulated-icon', '')

        # Get threshold values
        alert_thr = float(props.get('section_discharge_thr_alert', 0))
        alarm_thr = float(props.get('section_discharge_thr_alarm', 0))
        emergency_thr = float(props.get('section_discharge_thr_emergency', 0))

        if not time_period_str or not discharge_gfs:
            return None

        # Parse time series
        time_periods = time_period_str.split(',')
        discharge_gfs_values = [float(v) for v in discharge_gfs.split(',') if v and v != '-9998.0']

        # Parse discharge_icon if available
        discharge_icon_values = []
        if discharge_icon:
            discharge_icon_values = [float(v) if v and v != '-9998.0' else None
                                    for v in discharge_icon.split(',')]

        # Convert time periods to datetime
        from datetime import datetime
        dates = [datetime.strptime(tp.strip(), '%Y-%m-%d %H:%M') for tp in time_periods[:len(discharge_gfs_values)]]

        # Create figure with clean design
        fig, ax = plt.subplots(figsize=(10, 5))

        # Plot only forecast lines (GFS and ICON)
        ax.plot(dates, discharge_gfs_values, label='GFS Forecast', linewidth=2.5, color='#034930')

        if discharge_icon_values and len(discharge_icon_values) == len(dates):
            # Filter out None values
            valid_icon = [(d, v) for d, v in zip(dates, discharge_icon_values) if v is not None]
            if valid_icon:
                icon_dates, icon_values = zip(*valid_icon)
                ax.plot(icon_dates, icon_values, label='ICON Forecast',
                       linewidth=2.5, color='#0066cc', linestyle='--', alpha=0.8)

        # Formatting
        ax.set_xlabel('Date', fontsize=11, fontweight='bold', color='#2c3e50')
        ax.set_ylabel('Discharge (m³/s)', fontsize=11, fontweight='bold', color='#2c3e50')
        ax.set_title(f'Station {station_id} - Discharge Forecast Time Series',
                    fontsize=13, fontweight='bold', color='#034930', pad=15)
        ax.legend(loc='upper left', fontsize=10, framealpha=0.9)
        ax.grid(True, alpha=0.2, linestyle='--', linewidth=0.5)

        # Format x-axis dates
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
        plt.xticks(rotation=45, ha='right', fontsize=9)
        plt.yticks(fontsize=9)

        # Add threshold labels on the right side of the chart
        ax2 = ax.twinx()
        ax2.set_ylim(ax.get_ylim())
        ax2.set_ylabel('')
        ax2.set_yticks([])

        # Add threshold text annotations on the right
        y_max = max(discharge_gfs_values) if discharge_gfs_values else 100
        threshold_labels = []

        if alert_thr > 0:
            threshold_labels.append((alert_thr, 'Alert', '#FFC107'))
        if alarm_thr > 0:
            threshold_labels.append((alarm_thr, 'Alarm', '#FF9800'))
        if emergency_thr > 0:
            threshold_labels.append((emergency_thr, 'Emergency', '#F44336'))

        # Position threshold labels on the right side
        for thr_value, thr_name, thr_color in threshold_labels:
            if thr_value <= y_max * 1.5:  # Only show if within reasonable range
                ax.text(1.02, thr_value, f'{thr_name}: {thr_value:.1f}',
                       transform=ax.get_yaxis_transform(),
                       fontsize=9, color=thr_color, fontweight='bold',
                       verticalalignment='center', bbox=dict(boxstyle='round,pad=0.3',
                       facecolor='white', edgecolor=thr_color, alpha=0.8))

        # Tight layout with extra space for right-side labels
        plt.tight_layout()
        fig.subplots_adjust(right=0.85)

        # Save to BytesIO
        img_buffer = BytesIO()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        plt.close(fig)

        return img_buffer

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error generating discharge chart: {str(e)}")
        return None


def generate_report_pdf(saved_report):
    """
    Generate a PDF document for a SavedReport.

    Args:
        saved_report: SavedReport model instance

    Returns:
        BytesIO: PDF file content as bytes
    """
    # Fetch fresh station data from forecast if SavedReport fields are empty
    country = saved_report.country
    basin = saved_report.basin
    station_name = None
    station_feature = None
    chart_image = None

    try:
        from Impact.models import MergedDeterministicGeoJSON
        import logging
        logger = logging.getLogger(__name__)

        latest_forecast = MergedDeterministicGeoJSON.objects.order_by('-data_date').first()
        logger.info(f"PDF Gen: Looking for station_id={saved_report.station_id}, forecast date={latest_forecast.data_date if latest_forecast else 'None'}")

        if latest_forecast and saved_report.station_id:
            geojson_data = latest_forecast.geojson_data

            # Find station in forecast data
            for feature in geojson_data.get('features', []):
                props = feature.get('properties', {})
                station_ids = [
                    str(props.get('ID', '')),
                    str(props.get('SEC_CODE', '')),
                    str(props.get('station_id', '')),
                    str(props.get('section_id', ''))  # Add section_id used by MapViewer
                ]

                if str(saved_report.station_id) in station_ids:
                    station_feature = feature

                    # Extract country from ADMIN_B_L1 (format: "Country - Region")
                    admin = props.get('ADMIN_B_L1', '')
                    logger.info(f"PDF Gen: Found station! ADMIN_B_L1='{admin}', BASIN='{props.get('BASIN', '')}'")
                    if ' - ' in admin:
                        country = admin.split(' - ')[0]

                    basin = props.get('BASIN', '')
                    station_name = props.get('SEC_NAME', '')
                    break

            if not station_feature:
                logger.warning(f"PDF Gen: Station {saved_report.station_id} not found in forecast data")
            else:
                # Generate discharge chart
                logger.info(f"PDF Gen: Generating discharge chart for station {saved_report.station_id}")
                chart_image = generate_discharge_chart(saved_report.station_id, station_feature)
                if chart_image:
                    logger.info("PDF Gen: Chart generated successfully")
                else:
                    logger.warning("PDF Gen: Failed to generate chart")

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"PDF Gen: Error fetching station data: {str(e)}")
        pass  # Use empty values if fetch fails

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                           rightMargin=0.75*inch, leftMargin=0.75*inch,
                           topMargin=0.75*inch, bottomMargin=0.75*inch)

    # Container for 'Flowable' objects
    elements = []

    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#034930'),
        spaceAfter=30,
        alignment=TA_CENTER
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#034930'),
        spaceAfter=12,
        spaceBefore=12
    )

    # Title
    elements.append(Paragraph("East Africa FloodWatch", title_style))
    title_text = station_name if station_name else saved_report.report_title
    elements.append(Paragraph(title_text, heading_style))
    elements.append(Spacer(1, 0.2*inch))

    # Report Metadata Table
    metadata_data = [
        ['Report Information', ''],
        ['Generated:', datetime.now().strftime('%B %d, %Y at %H:%M')],
        ['Station ID:', saved_report.station_id or 'N/A'],
        ['Country:', country or 'N/A'],
        ['Basin:', basin or 'N/A'],
        ['Report Status:', saved_report.final_status.upper()],
    ]

    metadata_table = Table(metadata_data, colWidths=[2.5*inch, 4*inch])
    metadata_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#034930')),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
    ]))
    elements.append(metadata_table)
    elements.append(Spacer(1, 0.3*inch))

    # Station Statistics
    elements.append(Paragraph("Flood Risk Statistics", heading_style))

    stats_data = [
        ['Risk Level', 'Station Count', 'Status'],
        ['Emergency', saved_report.emergency_count or '0', '🚨 CRITICAL'],
        ['Alarm', saved_report.alarm_count or '0', '⚠️ HIGH RISK'],
        ['Warning', saved_report.warning_count or '0', '⚡ MODERATE'],
        ['Normal', saved_report.normal_count or '0', '✓ LOW RISK'],
        ['TOTAL', saved_report.total_stations or '1', ''],
    ]

    stats_table = Table(stats_data, colWidths=[2*inch, 2*inch, 2.5*inch])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#034930')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 1), (-1, 1), colors.Color(1, 0.9, 0.9)),  # Red tint for emergency
        ('BACKGROUND', (0, 2), (-1, 2), colors.Color(1, 0.95, 0.9)),  # Orange tint for alarm
        ('BACKGROUND', (0, 3), (-1, 3), colors.Color(1, 1, 0.9)),  # Yellow tint for warning
        ('BACKGROUND', (0, 4), (-1, 4), colors.Color(0.9, 1, 0.9)),  # Green tint for normal
        ('BACKGROUND', (0, 5), (-1, 5), colors.lightgrey),
        ('FONTNAME', (0, 5), (-1, 5), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(stats_table)
    elements.append(Spacer(1, 0.3*inch))

    # Add discharge time series chart if available
    if chart_image:
        elements.append(Paragraph("Discharge Forecast Time Series", heading_style))
        img = Image(chart_image, width=6.5*inch, height=3.25*inch)
        elements.append(img)
        elements.append(Spacer(1, 0.3*inch))

    # Approval Status
    elements.append(Paragraph("Approval Workflow", heading_style))

    approval_data = [
        ['Approval Stage', 'Reviewer', 'Status', 'Date'],
        [
            'Member State',
            saved_report.member_state_approver or 'Pending',
            saved_report.member_state_status.upper() if saved_report.member_state_status else 'PENDING',
            saved_report.member_state_approved_at.strftime('%Y-%m-%d') if saved_report.member_state_approved_at else 'N/A'
        ],
        [
            'ICPAC/RTMWA',
            saved_report.icpac_approver or 'Pending',
            saved_report.icpac_status.upper() if saved_report.icpac_status else 'PENDING',
            saved_report.icpac_approved_at.strftime('%Y-%m-%d') if saved_report.icpac_approved_at else 'N/A'
        ],
    ]

    approval_table = Table(approval_data, colWidths=[1.5*inch, 2*inch, 1.5*inch, 1.5*inch])
    approval_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#034930')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
    ]))
    elements.append(approval_table)
    elements.append(Spacer(1, 0.3*inch))

    # Comments Section
    if saved_report.member_state_comments or saved_report.icpac_comments:
        elements.append(Paragraph("Review Comments", heading_style))

        if saved_report.member_state_comments:
            elements.append(Paragraph("<b>Member State Comments:</b>", styles['Normal']))
            elements.append(Paragraph(saved_report.member_state_comments, styles['Normal']))
            elements.append(Spacer(1, 0.1*inch))

        if saved_report.icpac_comments:
            elements.append(Paragraph("<b>ICPAC/RTMWA Comments:</b>", styles['Normal']))
            elements.append(Paragraph(saved_report.icpac_comments, styles['Normal']))
            elements.append(Spacer(1, 0.1*inch))

    # Footer
    elements.append(Spacer(1, 0.5*inch))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    elements.append(Paragraph(
        "Generated by East Africa FloodWatch System | ICPAC<br/>"
        "IGAD Climate Prediction and Applications Centre<br/>"
        f"Report ID: {saved_report.id} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        footer_style
    ))

    # Build PDF
    doc.build(elements)

    # Get the value of the BytesIO buffer
    pdf = buffer.getvalue()
    buffer.close()

    return pdf
