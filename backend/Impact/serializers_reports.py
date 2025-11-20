"""
Django REST Framework serializers for flood report approval workflow.
Replaces Node.js api-server serialization.
"""

from rest_framework import serializers
from .models_reports import StationReportApproval, StationAssessment, SavedReport


class StationReportApprovalSerializer(serializers.ModelSerializer):
    """Serializer for station report approval workflow"""

    class Meta:
        model = StationReportApproval
        fields = [
            'id',
            'station_id',
            # Member State fields
            'member_state_poc_name',
            'member_state_poc_title',
            'member_state_poc_organization',
            'member_state_poc_email',
            'member_state_status',
            'member_state_comments',
            'member_state_approved_at',
            # ICPAC fields
            'icpac_reviewer_name',
            'icpac_reviewer_title',
            'icpac_status',
            'icpac_comments',
            'icpac_approved_at',
            # Overall
            'final_status',
            'summary_text',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'final_status']

    def to_representation(self, instance):
        """
        Convert field names to match Node.js API format for backwards compatibility
        """
        representation = super().to_representation(instance)

        # Add camelCase aliases for Node.js API compatibility
        camel_case = {
            'stationId': representation['station_id'],
            'pocName': representation['member_state_poc_name'],
            'pocTitle': representation['member_state_poc_title'],
            'pocOrganization': representation['member_state_poc_organization'],
            'pocEmail': representation['member_state_poc_email'],
            'status': representation['member_state_status'],
            'pocComments': representation['member_state_comments'],
            'summaryText': representation['summary_text'],
            'createdAt': representation['created_at'],
            'updatedAt': representation['updated_at'],
        }

        representation.update(camel_case)
        return representation


class StationAssessmentSerializer(serializers.ModelSerializer):
    """Serializer for station field assessments"""

    class Meta:
        model = StationAssessment
        fields = [
            'id',
            'station_id',
            'country',
            'basin',
            'station_name',
            'discharge',
            'model_type',
            'assessed_risk_level',
            'member_state_status',
            'observations',
            'field_comments',
            'assessor_name',
            'assessor_organization',
            'assessment_date',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'assessment_date', 'created_at', 'updated_at']

    def to_representation(self, instance):
        """
        Convert field names to match Node.js API format for backwards compatibility
        """
        representation = super().to_representation(instance)

        # Add camelCase aliases for Node.js API compatibility
        camel_case = {
            'stationId': representation['station_id'],
            'stationName': representation['station_name'],
            'modelType': representation['model_type'],
            'assessedRiskLevel': representation['assessed_risk_level'],
            'memberStateStatus': representation['member_state_status'],
            'fieldComments': representation['field_comments'],
            'assessorName': representation['assessor_name'],
            'assessorOrganization': representation['assessor_organization'],
            'assessmentDate': representation['assessment_date'],
            'createdAt': representation['created_at'],
            'updatedAt': representation['updated_at'],
        }

        representation.update(camel_case)
        return representation


class SavedReportSerializer(serializers.ModelSerializer):
    """Serializer for saved reports with approval workflow"""

    class Meta:
        model = SavedReport
        fields = [
            'id',
            'report_title',
            'country',
            'basin',
            'station_id',
            'report_data',
            'total_stations',
            'emergency_count',
            'alarm_count',
            'warning_count',
            'normal_count',
            'pdf_path',
            'csv_path',
            'png_path',
            # Member State Approval
            'member_state_approver',
            'member_state_organization',
            'member_state_status',
            'member_state_comments',
            'member_state_approved_at',
            # ICPAC Approval
            'icpac_approver',
            'icpac_status',
            'icpac_comments',
            'icpac_approved_at',
            # Final
            'final_status',
            'generated_by',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'final_status']

    def to_representation(self, instance):
        """
        Convert field names to match Node.js API format for backwards compatibility
        """
        representation = super().to_representation(instance)

        # Add camelCase aliases for Node.js API compatibility
        camel_case = {
            'reportTitle': representation['report_title'],
            'stationId': representation['station_id'],
            'reportData': representation['report_data'],
            'totalStations': representation['total_stations'],
            'emergencyCount': representation['emergency_count'],
            'alarmCount': representation['alarm_count'],
            'warningCount': representation['warning_count'],
            'normalCount': representation['normal_count'],
            'pdfPath': representation['pdf_path'],
            'csvPath': representation['csv_path'],
            'pngPath': representation['png_path'],
            'memberStateApprover': representation['member_state_approver'],
            'memberStateOrganization': representation['member_state_organization'],
            'memberStateStatus': representation['member_state_status'],
            'memberStateComments': representation['member_state_comments'],
            'memberStateApprovedAt': representation['member_state_approved_at'],
            'icpacApprover': representation['icpac_approver'],
            'icpacStatus': representation['icpac_status'],
            'icpacComments': representation['icpac_comments'],
            'icpacApprovedAt': representation['icpac_approved_at'],
            'finalStatus': representation['final_status'],
            'generatedBy': representation['generated_by'],
            'createdAt': representation['created_at'],
            'updatedAt': representation['updated_at'],
        }

        representation.update(camel_case)
        return representation


class SavedReportListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for list views (excludes heavy report_data field)
    """

    class Meta:
        model = SavedReport
        fields = [
            'id',
            'report_title',
            'country',
            'basin',
            'station_id',
            'total_stations',
            'emergency_count',
            'alarm_count',
            'warning_count',
            'normal_count',
            'member_state_approver',
            'member_state_organization',
            'member_state_status',
            'icpac_approver',
            'icpac_status',
            'final_status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'final_status']
