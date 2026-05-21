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

# Kutumba `StatusCode` values we recognise.
# 0  = success
# -3 = invalid HMAC (admin-actionable: wrong client_code / hmac_key / clock skew)
# -19 = no data found for the given criteria (user-visible empty result)
NO_DATA_STATUS_CODE = -19
INVALID_HMAC_STATUS_CODE = -3

# Non-zero status codes that represent a *valid* upstream response that the
# end user can act on (typically by trying different input). Anything not in
# this set is treated as an integration / upstream failure the user can't fix.
USER_VISIBLE_EMPTY_CODES = {NO_DATA_STATUS_CODE}


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
                upstream_error = status_code not in USER_VISIBLE_EMPTY_CODES
                if status_code == INVALID_HMAC_STATUS_CODE:
                    # Admin-actionable: log loudly so it surfaces in monitoring.
                    logger.error(
                        "Kutumba rejected our HMAC \u2014 check KUTUMBA_HMAC_KEY / "
                        "KUTUMBA_CLIENT_CODE. request_id=%s response_id=%s",
                        request_id,
                        response_data.get("Response_ID"),
                    )
                else:
                    logger.warning("Kutumba API returned error: %s - %s", status_code, status_text)
                return BeneficiaryLookupResponse(
                    success=False,
                    status_code=status_code,
                    status_text=status_text,
                    response_id=response_data.get("Response_ID"),
                    request_id=request_id,
                    members=[],
                    error=f"Kutumba API error: {status_text}",
                    upstream_error=upstream_error,
                )

            # Decrypt the encrypted result payload
            logger.debug("Decrypting response...")
            decrypted_data = decrypt_response(
                response_data["EncResultData"],
                self.aes_key,
                self.aes_iv,
            )
            result_list = decrypted_data.get("ResultDataList", [])

            # Parse members using Pydantic specs
            members = [BeneficiaryMember.from_api_response(member_data) for member_data in result_list]

            return BeneficiaryLookupResponse(
                success=True,
                status_code=status_code,
                status_text=status_text,
                response_id=decrypted_data.get("Response_ID"),
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
                upstream_error=True,
            )
