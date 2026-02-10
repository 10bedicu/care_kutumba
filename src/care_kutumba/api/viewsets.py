import logging

from pydantic import ValidationError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care_kutumba.api.specs import BeneficiaryLookupRequest
from care_kutumba.service.kutumba import KutumbaService

logger = logging.getLogger(__name__)


class BeneficiaryViewSet(GenericViewSet):
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
        try:
            lookup_request = BeneficiaryLookupRequest(**request.data)
        except ValidationError as e:
            return Response(
                {"success": False, "errors": e.errors()},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = KutumbaService()
        result = service.get_beneficiary_data(lookup_request.rc_number)

        # Serialize response using Pydantic model_dump
        response_data = result.model_dump()

        if result.success:
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            return Response(response_data, status=status.HTTP_502_BAD_GATEWAY)
