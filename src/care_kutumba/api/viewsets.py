import logging

from care.security.authorization.base import AuthorizationController
from pydantic import ValidationError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care_kutumba.api.specs import BeneficiaryLookupRequest
from care_kutumba.models import KutumbaRequestLog
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
                {
                    "success": False,
                    "errors": e.errors(include_context=False, include_url=False, include_input=False),
                },
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

        if result.upstream_error:
            # Don't echo upstream's diagnostic verbatim \u2014 it can leak
            # integration details (auth scheme, client codes, etc.) and is
            # not actionable by the end user. Surface a generic message and
            # the log id so support can correlate.
            safe_payload = {
                "success": False,
                "request_log_external_id": str(request_log.external_id),
                "error": ("Kutumba lookup is currently unavailable. Please try again later or contact support."),
            }
            return Response(safe_payload, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(response_data, status=status.HTTP_200_OK)
