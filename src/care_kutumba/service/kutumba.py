"""High-level Kutumba API service.

This module provides a clean interface for interacting with the
Karnataka Kutumba beneficiary data API.
"""

import logging

from care_kutumba.api.specs import BeneficiaryLookupResponse, BeneficiaryMember
from care_kutumba.service.crypto import decrypt_response, generate_hmac
from care_kutumba.service.request import KutumbaRequest, generate_request_id
from care_kutumba.settings import plugin_settings as settings

logger = logging.getLogger(__name__)


class KutumbaService:
    """Service for interacting with Kutumba API."""

    def __init__(self):
        # Validate required settings on service instantiation
        settings.validate()

        self.client = KutumbaRequest()
        self.client_code = settings.KUTUMBA_CLIENT_CODE
        self.hmac_key = settings.KUTUMBA_HMAC_KEY
        self.aes_key = settings.KUTUMBA_AES_KEY
        self.aes_iv = settings.KUTUMBA_AES_IV
        self.api_version = settings.KUTUMBA_API_VERSION

    def get_beneficiary_data(self, rc_number: str) -> BeneficiaryLookupResponse:
        """
        Fetch beneficiary data for a given Ration Card number.

        Args:
            rc_number: The ration card number to lookup

        Returns:
            BeneficiaryLookupResponse containing family member data or error info
        """
        logger.info("Looking up beneficiary data for RC")

        # Generate HMAC for authentication
        hashed_mac = generate_hmac(self.client_code, rc_number, self.hmac_key)
        request_id = generate_request_id()

        # Build request payload
        payload = {
            "DeptID": "",
            "BenID": "",
            "RC_Number": rc_number,
            "Aadhar_no": "",
            "ClientCode": self.client_code,
            "HashedMac": hashed_mac,
            "APIVersion": self.api_version,
            "IsPhotoRequired": "",
            "Member_ID": "",
            "Mobile_No": "",
            "Request_ID": request_id,
            "UIDType": "0",
        }

        try:
            # Make API request
            response = self.client.post(data=payload)
            response_data = response.json()

            # Check for API-level errors
            status_code = response_data.get("StatusCode", -1)
            status_text = response_data.get("StatusText", "Unknown")

            if status_code != 0:
                logger.warning(f"Kutumba API returned error: {status_code} - {status_text}")
                return BeneficiaryLookupResponse(
                    success=False,
                    status_code=status_code,
                    status_text=status_text,
                    response_id=response_data.get("Response_ID"),
                    request_id=request_id,
                    members=[],
                    error=f"Kutumba API error: {status_text}",
                )

            # Check if response is encrypted
            if "EncResultData" in response_data:
                logger.debug("Response is encrypted, decrypting...")
                decrypted_data = decrypt_response(
                    response_data["EncResultData"],
                    self.aes_key,
                    self.aes_iv,
                )
                # The decrypted data should have ResultDataList
                result_list = decrypted_data.get("ResultDataList", [])
            else:
                # Response might be unencrypted (for testing environments)
                result_list = response_data.get("ResultDataList", [])

            # Parse members using Pydantic specs
            members = [BeneficiaryMember.from_api_response(member_data) for member_data in result_list]

            return BeneficiaryLookupResponse(
                success=True,
                status_code=status_code,
                status_text=status_text,
                response_id=response_data.get("Response_ID"),
                request_id=request_id,
                members=members,
            )

        except Exception as e:
            logger.error(f"Failed to fetch beneficiary data: {e}")
            return BeneficiaryLookupResponse(
                success=False,
                status_code=-1,
                status_text="Error",
                response_id=None,
                request_id=request_id,
                members=[],
                error=str(e),
            )
