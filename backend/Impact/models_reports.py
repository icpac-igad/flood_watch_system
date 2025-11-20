"""
Django models for Flood Report Approval Workflow
Replaces Node.js api-server functionality for station reports, assessments, and saved reports.
"""

from django.db import models
from django.contrib.auth.models import User


class StationReportApproval(models.Model):
    """
    Two-stage approval workflow for station flood reports:
    Stage 1: Member State Approval
    Stage 2: ICPAC/RTMWA Final Approval
    """

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('changes_requested', 'Changes Requested'),
        ('rejected', 'Rejected'),
    ]

    # Station identification
    station_id = models.CharField(max_length=255, unique=True, db_index=True)

    # STAGE 1: Member State Approval
    member_state_poc_name = models.CharField(max_length=255, blank=True, null=True)
    member_state_poc_title = models.CharField(max_length=255, blank=True, null=True)
    member_state_poc_organization = models.CharField(max_length=255, blank=True, null=True)
    member_state_poc_email = models.EmailField(blank=True, null=True)
    member_state_status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Member State approval status"
    )
    member_state_comments = models.TextField(blank=True, null=True)
    member_state_approved_at = models.DateTimeField(blank=True, null=True)

    # STAGE 2: ICPAC/RTMWA Final Approval
    icpac_reviewer_name = models.CharField(max_length=255, blank=True, null=True)
    icpac_reviewer_title = models.CharField(max_length=255, blank=True, null=True)
    icpac_status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="ICPAC/RTMWA final approval status"
    )
    icpac_comments = models.TextField(blank=True, null=True)
    icpac_approved_at = models.DateTimeField(blank=True, null=True)

    # Overall Status (computed from both stages)
    final_status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Final computed status from both approval stages"
    )

    # Report Summary
    summary_text = models.TextField(blank=True, null=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'station_report_approvals'
        verbose_name = 'Station Report Approval'
        verbose_name_plural = 'Station Report Approvals'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['station_id']),
            models.Index(fields=['final_status']),
            models.Index(fields=['member_state_status']),
            models.Index(fields=['icpac_status']),
        ]

    def __str__(self):
        return f"Report Approval for {self.station_id} - {self.final_status}"

    def save(self, *args, **kwargs):
        """Auto-compute final status and create SavedReport when approved"""
        # Track if this is a new approval
        is_newly_approved = False
        old_final_status = None

        if self.pk:
            try:
                old_instance = StationReportApproval.objects.get(pk=self.pk)
                old_final_status = old_instance.final_status
            except StationReportApproval.DoesNotExist:
                pass

        # Compute final status
        if self.member_state_status == 'approved' and self.icpac_status == 'approved':
            self.final_status = 'approved'
            # Check if this is a new approval
            if old_final_status != 'approved':
                is_newly_approved = True
        elif self.member_state_status == 'rejected' or self.icpac_status == 'rejected':
            self.final_status = 'rejected'
        elif self.member_state_status == 'changes_requested':
            self.final_status = 'changes_requested'
        else:
            self.final_status = 'pending'

        super().save(*args, **kwargs)

        # Create SavedReport when newly approved
        if is_newly_approved:
            self.create_saved_report()

    def create_saved_report(self):
        """Create a SavedReport entry for this approved station report"""
        from datetime import datetime

        # Get station data from forecast database to populate the report
        try:
            from Impact.models import MergedDeterministicGeoJSON

            # Get latest forecast data
            latest_forecast = MergedDeterministicGeoJSON.objects.order_by('-data_date').first()
            if not latest_forecast:
                return

            # Find the station in the forecast data
            geojson_data = latest_forecast.geojson_data
            station_feature = None

            for feature in geojson_data.get('features', []):
                props = feature.get('properties', {})
                # Check multiple possible station ID fields
                station_ids = [
                    str(props.get('ID', '')),
                    str(props.get('SEC_CODE', '')),
                    str(props.get('station_id', '')),
                    str(props.get('section_id', ''))  # Add section_id used by MapViewer
                ]
                if str(self.station_id) in station_ids:
                    station_feature = feature
                    break

            # Get properties from station or create minimal ones
            if station_feature:
                properties = station_feature.get('properties', {})
                country = properties.get('ADMIN_B_L1', '').split(' - ')[0] if ' - ' in properties.get('ADMIN_B_L1', '') else ''
                basin = properties.get('BASIN', '')
                station_name = properties.get('SEC_NAME', f'Station {self.station_id}')
            else:
                # Station not found - create report with minimal data
                properties = {}
                country = ''
                basin = ''
                station_name = f'Station {self.station_id}'

            # Create SavedReport with data from the station
            SavedReport.objects.create(
                report_title=f"Flood Analysis Report for {station_name}",
                country=country,
                basin=basin,
                station_id=self.station_id,
                report_data={
                    'station_properties': properties,
                    'forecast_date': latest_forecast.date_string,
                    'summary': self.summary_text,
                    'member_state_approval': {
                        'approver': self.member_state_poc_name,
                        'organization': self.member_state_poc_organization,
                        'approved_at': self.member_state_approved_at.isoformat() if self.member_state_approved_at else None,
                        'comments': self.member_state_comments
                    },
                    'icpac_approval': {
                        'reviewer': self.icpac_reviewer_name,
                        'approved_at': self.icpac_approved_at.isoformat() if self.icpac_approved_at else None,
                        'comments': self.icpac_comments
                    }
                },
                total_stations='1',
                emergency_count='0',
                alarm_count='0',
                warning_count='0',
                normal_count='1',
                member_state_approver=self.member_state_poc_name,
                member_state_organization=self.member_state_poc_organization,
                member_state_status='approved',
                member_state_comments=self.member_state_comments,
                member_state_approved_at=self.member_state_approved_at,
                icpac_approver=self.icpac_reviewer_name,
                icpac_status='approved',
                icpac_comments=self.icpac_comments,
                icpac_approved_at=self.icpac_approved_at,
                final_status='approved',
                generated_by=f"{self.member_state_poc_name} ({self.member_state_poc_organization})"
            )
        except Exception as e:
            # Log the error but don't fail the save operation
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to create SavedReport for station {self.station_id}: {str(e)}")


class StationAssessment(models.Model):
    """
    Station-level field assessments by member state personnel.
    Allows ground truth validation of model predictions.
    """

    RISK_LEVEL_CHOICES = [
        ('critical', 'Critical'),
        ('high_risk', 'High Risk'),
        ('moderate', 'Moderate'),
        ('low_risk', 'Low Risk'),
    ]

    MEMBER_STATUS_CHOICES = [
        ('confirmed', 'Confirmed'),
        ('under_observation', 'Under Observation'),
        ('false_alarm', 'False Alarm'),
    ]

    MODEL_TYPE_CHOICES = [
        ('gfs', 'GFS'),
        ('icon', 'ICON'),
        ('ensemble', 'Ensemble'),
        ('deterministic', 'Deterministic'),
    ]

    # Station identification
    station_id = models.CharField(max_length=255, db_index=True)
    country = models.CharField(max_length=255, blank=True, null=True)
    basin = models.CharField(max_length=255, blank=True, null=True)

    # Station data snapshot at time of assessment
    station_name = models.CharField(max_length=255, blank=True, null=True)
    discharge = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="River discharge at time of assessment (m³/s)"
    )
    model_type = models.CharField(
        max_length=50,
        choices=MODEL_TYPE_CHOICES,
        blank=True,
        null=True
    )

    # Member State field assessment
    assessed_risk_level = models.CharField(
        max_length=50,
        choices=RISK_LEVEL_CHOICES,
        blank=True,
        null=True,
        help_text="Risk level assessed by member state in field"
    )
    member_state_status = models.CharField(
        max_length=50,
        choices=MEMBER_STATUS_CHOICES,
        blank=True,
        null=True,
        help_text="Member state validation of model prediction"
    )

    # Field observations
    observations = models.TextField(
        blank=True,
        null=True,
        help_text="Field observations and current situation"
    )
    field_comments = models.TextField(
        blank=True,
        null=True,
        help_text="Additional comments from field assessor"
    )

    # Assessor information
    assessor_name = models.CharField(max_length=255, blank=True, null=True)
    assessor_organization = models.CharField(max_length=255, blank=True, null=True)

    # Metadata
    assessment_date = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'station_assessments'
        verbose_name = 'Station Assessment'
        verbose_name_plural = 'Station Assessments'
        ordering = ['-assessment_date']
        indexes = [
            models.Index(fields=['station_id', '-assessment_date']),
            models.Index(fields=['country']),
            models.Index(fields=['basin']),
            models.Index(fields=['assessed_risk_level']),
        ]

    def __str__(self):
        return f"Assessment for {self.station_name or self.station_id} on {self.assessment_date.date()}"


class SavedReport(models.Model):
    """
    Saved flood analysis reports with full approval workflow tracking.
    Stores report snapshots, metadata, and two-stage approval status.
    """

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('changes_requested', 'Changes Requested'),
    ]

    # Report identification
    report_title = models.CharField(max_length=500)
    country = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    basin = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    station_id = models.CharField(max_length=255, blank=True, null=True)

    # Report data (JSON snapshot of full report content)
    report_data = models.JSONField(
        help_text="Complete report data including charts, tables, analysis"
    )

    # Statistics summary (for quick filtering/display)
    total_stations = models.CharField(max_length=50, blank=True, null=True)
    emergency_count = models.CharField(max_length=50, blank=True, null=True)
    alarm_count = models.CharField(max_length=50, blank=True, null=True)
    warning_count = models.CharField(max_length=50, blank=True, null=True)
    normal_count = models.CharField(max_length=50, blank=True, null=True)

    # Report file paths (for generated PDF, CSV, PNG exports)
    pdf_path = models.CharField(max_length=500, blank=True, null=True)
    csv_path = models.CharField(max_length=500, blank=True, null=True)
    png_path = models.CharField(max_length=500, blank=True, null=True)

    # STAGE 1: Member State Approval
    member_state_approver = models.CharField(max_length=255, blank=True, null=True)
    member_state_organization = models.CharField(max_length=255, blank=True, null=True)
    member_state_status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='pending'
    )
    member_state_comments = models.TextField(blank=True, null=True)
    member_state_approved_at = models.DateTimeField(blank=True, null=True)

    # STAGE 2: ICPAC/RTMWA Approval
    icpac_approver = models.CharField(max_length=255, blank=True, null=True)
    icpac_status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='pending'
    )
    icpac_comments = models.TextField(blank=True, null=True)
    icpac_approved_at = models.DateTimeField(blank=True, null=True)

    # Final Status
    final_status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Final computed status"
    )

    # Metadata
    generated_by = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'saved_reports'
        verbose_name = 'Saved Report'
        verbose_name_plural = 'Saved Reports'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['country', '-created_at']),
            models.Index(fields=['basin', '-created_at']),
            models.Index(fields=['final_status']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.report_title} - {self.final_status}"

    def save(self, *args, **kwargs):
        """Auto-compute final status based on both approval stages"""
        if self.member_state_status == 'approved' and self.icpac_status == 'approved':
            self.final_status = 'approved'
        elif self.member_state_status == 'rejected' or self.icpac_status == 'rejected':
            self.final_status = 'rejected'
        elif self.member_state_status == 'changes_requested':
            self.final_status = 'changes_requested'
        else:
            self.final_status = 'pending'

        super().save(*args, **kwargs)
