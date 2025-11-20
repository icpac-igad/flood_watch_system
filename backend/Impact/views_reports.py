"""
Django REST Framework views for flood report approval workflow.
Replaces Node.js api-server/server.js endpoints.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models_reports import StationReportApproval, StationAssessment, SavedReport
from .serializers_reports import (
    StationReportApprovalSerializer,
    StationAssessmentSerializer,
    SavedReportSerializer,
    SavedReportListSerializer
)


@method_decorator(csrf_exempt, name='dispatch')
class StationReportApprovalViewSet(viewsets.ModelViewSet):
    """
    API endpoint for station report approvals.
    Replaces Node.js /api/station-reports/ endpoints.
    CSRF exempt for API usage (protected by CORS instead).
    """
    queryset = StationReportApproval.objects.all()
    serializer_class = StationReportApprovalSerializer

    def get_queryset(self):
        """Allow filtering by status"""
        queryset = StationReportApproval.objects.all().order_by('-updated_at')

        # Filter by status if provided
        status_param = self.request.query_params.get('status', None)
        if status_param:
            queryset = queryset.filter(final_status=status_param)

        return queryset

    @extend_schema(
        summary="Get or create/update station report approval",
        parameters=[
            OpenApiParameter('station_id', OpenApiTypes.STR, OpenApiParameter.PATH)
        ]
    )
    @action(detail=False, methods=['get', 'post'], url_path='by-station/(?P<station_id>[^/.]+)')
    def by_station(self, request, station_id=None):
        """
        GET: Get approval status for a specific station.
        POST: Create or update station report approval.
        Matches Node.js: GET/POST /api/station-reports/:stationId
        """
        if request.method == 'GET':
            try:
                approval = StationReportApproval.objects.get(station_id=station_id)
                serializer = self.get_serializer(approval)
                return Response(serializer.data)
            except StationReportApproval.DoesNotExist:
                return Response(
                    {'error': 'Station report not found', 'stationId': station_id},
                    status=status.HTTP_404_NOT_FOUND
                )

        elif request.method == 'POST':
            try:
                approval = StationReportApproval.objects.get(station_id=station_id)
                serializer = self.get_serializer(approval, data=request.data, partial=True)
            except StationReportApproval.DoesNotExist:
                data = request.data.copy()
                data['station_id'] = station_id
                serializer = self.get_serializer(data=data)

            if serializer.is_valid():
                # Handle status-based timestamp updates
                if 'member_state_status' in request.data and request.data['member_state_status'] == 'approved':
                    serializer.validated_data['member_state_approved_at'] = timezone.now()
                if 'icpac_status' in request.data and request.data['icpac_status'] == 'approved':
                    serializer.validated_data['icpac_approved_at'] = timezone.now()

                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StationAssessmentViewSet(viewsets.ModelViewSet):
    """
    API endpoint for station field assessments.
    Replaces Node.js /api/station-assessments/ endpoints.
    """
    queryset = StationAssessment.objects.all()
    serializer_class = StationAssessmentSerializer

    def get_queryset(self):
        """Allow filtering by country"""
        queryset = StationAssessment.objects.all().order_by('-assessment_date')

        # Filter by country if provided
        country = self.request.query_params.get('country', None)
        if country:
            queryset = queryset.filter(country=country)

        return queryset

    @extend_schema(
        summary="Get assessments for a specific country",
        parameters=[
            OpenApiParameter('country', OpenApiTypes.STR, OpenApiParameter.PATH)
        ]
    )
    @action(detail=False, methods=['get'], url_path='country/(?P<country>[^/.]+)')
    def by_country(self, request, country=None):
        """
        Get all station assessments for a country.
        Matches Node.js: GET /api/station-assessments/country/:country
        """
        assessments = StationAssessment.objects.filter(country=country).order_by('-assessment_date')
        serializer = self.get_serializer(assessments, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Get latest assessment for a specific station",
        parameters=[
            OpenApiParameter('station_id', OpenApiTypes.STR, OpenApiParameter.PATH)
        ]
    )
    @action(detail=False, methods=['get'], url_path='station/(?P<station_id>[^/.]+)')
    def by_station(self, request, station_id=None):
        """
        Get latest assessment for a specific station.
        Matches Node.js: GET /api/station-assessments/:stationId
        """
        try:
            assessment = StationAssessment.objects.filter(
                station_id=station_id
            ).order_by('-assessment_date').first()

            if assessment:
                serializer = self.get_serializer(assessment)
                return Response(serializer.data)
            else:
                # Return empty structure like Node.js does
                return Response({
                    'stationId': station_id,
                    'assessedRiskLevel': None,
                    'memberStateStatus': None,
                    'observations': None
                })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SavedReportViewSet(viewsets.ModelViewSet):
    """
    API endpoint for saved flood reports with approval workflow.
    Replaces Node.js /api/saved-reports/ endpoints.
    """
    queryset = SavedReport.objects.all()

    def get_serializer_class(self):
        """Use lightweight serializer for list view"""
        if self.action == 'list':
            return SavedReportListSerializer
        return SavedReportSerializer

    def get_queryset(self):
        """Allow filtering by country, basin, status"""
        queryset = SavedReport.objects.all().order_by('-created_at')

        # Filter by country if provided
        country = self.request.query_params.get('country', None)
        if country:
            queryset = queryset.filter(country=country)

        # Filter by basin if provided
        basin = self.request.query_params.get('basin', None)
        if basin:
            queryset = queryset.filter(basin=basin)

        # Filter by status if provided
        final_status = self.request.query_params.get('status', None)
        if final_status:
            queryset = queryset.filter(final_status=final_status)

        return queryset

    @extend_schema(
        summary="Update member state approval",
        parameters=[
            OpenApiParameter('id', OpenApiTypes.INT, OpenApiParameter.PATH)
        ]
    )
    @action(detail=True, methods=['put'], url_path='member-approval')
    def member_approval(self, request, pk=None):
        """
        Update member state approval status.
        Matches Node.js: PUT /api/saved-reports/:id/member-approval
        """
        report = get_object_or_404(SavedReport, pk=pk)

        # Update member state fields
        report.member_state_approver = request.data.get('approver', report.member_state_approver)
        report.member_state_organization = request.data.get('organization', report.member_state_organization)
        report.member_state_status = request.data.get('status', report.member_state_status)
        report.member_state_comments = request.data.get('comments', report.member_state_comments)

        if request.data.get('status') == 'approved':
            report.member_state_approved_at = timezone.now()

        report.save()

        serializer = self.get_serializer(report)
        return Response(serializer.data)

    @extend_schema(
        summary="Update ICPAC approval",
        parameters=[
            OpenApiParameter('id', OpenApiTypes.INT, OpenApiParameter.PATH)
        ]
    )
    @action(detail=True, methods=['put'], url_path='icpac-approval')
    def icpac_approval(self, request, pk=None):
        """
        Update ICPAC approval status.
        Matches Node.js: PUT /api/saved-reports/:id/icpac-approval
        """
        report = get_object_or_404(SavedReport, pk=pk)

        # Update ICPAC fields
        report.icpac_approver = request.data.get('approver', report.icpac_approver)
        report.icpac_status = request.data.get('status', report.icpac_status)
        report.icpac_comments = request.data.get('comments', report.icpac_comments)

        if request.data.get('status') == 'approved':
            report.icpac_approved_at = timezone.now()

        report.save()

        serializer = self.get_serializer(report)
        return Response(serializer.data)

    @extend_schema(
        summary="Generate PDF for a saved report",
        parameters=[
            OpenApiParameter('id', OpenApiTypes.INT, OpenApiParameter.PATH)
        ]
    )
    @action(detail=True, methods=['get'], url_path='pdf')
    def generate_pdf(self, request, pk=None):
        """
        Generate and download PDF for a saved report.
        Endpoint: GET /api/saved-reports/:id/pdf/
        """
        report = get_object_or_404(SavedReport, pk=pk)

        try:
            from .utils_pdf import generate_report_pdf

            # Generate PDF
            pdf_content = generate_report_pdf(report)

            # Create HTTP response with PDF - inline to display in browser
            response = HttpResponse(pdf_content, content_type='application/pdf')
            filename = f"FloodWatch_Report_{report.station_id}_{report.id}.pdf"
            response['Content-Disposition'] = f'inline; filename="{filename}"'

            return response

        except Exception as e:
            return Response(
                {'error': f'Failed to generate PDF: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
