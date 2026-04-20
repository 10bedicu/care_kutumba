import logging

from care.emr.models.patient import Patient
from care.security.authorization.base import AuthorizationController
from pydantic import ValidationError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care_kutumba.api.specs import BeneficiaryLookupRequest, PatientLinkRequest
from care_kutumba.models import KutumbaPatientLink, KutumbaRequestLog
from care_kutumba.service.kutumba import KutumbaService

logger = logging.getLogger(__name__)


class BeneficiaryViewSet(GenericViewSet):
    permission_classes = (IsAuthenticated,)
    """ViewSet for Kutumba beneficiary operations."""

    @action(detail=False, methods=["post"])
    def lookup(self, request, *args, **kwargs):
        """
        Lookup beneficiary data by Ration Card number.

        Request body:
        {
            "rc_number": "110399147990"
        }

        Returns family member data from Karnataka Kutumba system.
        """
        if not AuthorizationController.call("can_create_patient", self.request.user):
            raise PermissionDenied("You do not have permission to look up Kutumba beneficiaries")

        try:
            lookup_request = BeneficiaryLookupRequest(**request.data)
        except ValidationError as e:
            return Response(
                {"success": False, "errors": e.errors()},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = KutumbaService()
        result = service.get_beneficiary_data(lookup_request.rc_number)

        request_log = KutumbaRequestLog.objects.create(
            request_id=result.request_id or "",
            response_id=result.response_id,
            rc_number=lookup_request.rc_number,
            success=result.success,
            status_code=result.status_code,
            status_text=result.status_text,
            members=[m.model_dump() for m in result.members],
            member_count=len(result.members),
            requested_by=request.user,
            error=result.error,
        )

        # Serialize response using Pydantic model_dump
        response_data = result.model_dump()
        response_data["request_log_external_id"] = str(request_log.external_id)

        if result.success:
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            return Response(response_data, status=status.HTTP_502_BAD_GATEWAY)


class PatientLinkViewSet(GenericViewSet):
    """ViewSet for recording links between Kutumba lookups and patient actions."""

    permission_classes = (IsAuthenticated,)
    queryset = KutumbaPatientLink.objects.all()

    def create(self, request, *args, **kwargs):
        """
        Record that a Kutumba lookup result was used to create or update a patient.

        Request body:
        {
            "request_log_external_id": "<uuid>",
            "selected_member_index": 0,
            "patient_external_id": "<uuid>" | null,
            "action": "create" | "update"
        }
        """
        if not AuthorizationController.call("can_create_patient", request.user):
            raise PermissionDenied("You do not have permission to record Kutumba patient links")

        try:
            link_request = PatientLinkRequest(**request.data)
        except ValidationError as e:
            return Response(
                {"success": False, "errors": e.errors()},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            request_log = KutumbaRequestLog.objects.get(external_id=link_request.request_log_external_id)
        except KutumbaRequestLog.DoesNotExist:
            return Response(
                {"success": False, "error": "Kutumba request log not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if link_request.selected_member_index >= len(request_log.members):
            return Response(
                {
                    "success": False,
                    "error": "selected_member_index is out of range for this request log",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        patient = None
        if link_request.patient_external_id is not None:
            try:
                patient = Patient.objects.get(external_id=link_request.patient_external_id)
            except Patient.DoesNotExist:
                return Response(
                    {"success": False, "error": "Patient not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        selected_member = request_log.members[link_request.selected_member_index]

        link = KutumbaPatientLink.objects.create(
            request_log=request_log,
            selected_member_index=link_request.selected_member_index,
            selected_member_data=selected_member,
            rc_number=request_log.rc_number,
            patient=patient,
            action=link_request.action,
            performed_by=request.user,
        )

        return Response(
            {
                "success": True,
                "external_id": str(link.external_id),
                "request_log_external_id": str(request_log.external_id),
                "selected_member_index": link.selected_member_index,
                "patient_external_id": (str(patient.external_id) if patient is not None else None),
                "action": link.action,
            },
            status=status.HTTP_201_CREATED,
        )
