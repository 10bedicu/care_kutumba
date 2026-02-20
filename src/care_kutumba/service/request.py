"""HTTP client for Kutumba API requests."""

import json
import logging

import requests

from care_kutumba.settings import plugin_settings as settings

logger = logging.getLogger(__name__)


class KutumbaRequest:
    """HTTP client for making requests to the Kutumba API."""

    def __init__(self, base_url: str = None):
        self.url = base_url or settings.KUTUMBA_API_URL
        self.timeout = settings.KUTUMBA_REQUEST_TIMEOUT
        logger.info(f"Initialized KutumbaRequest with base_url: {self.url}")

    def headers(self, additional_headers: dict = None) -> dict:
        """Build request headers."""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            **(additional_headers or {}),
        }

    def post(self, data: dict = None, headers: dict = None) -> requests.Response:
        """
        Make a POST request to the Kutumba API.

        Args:
            data: Request payload dictionary
            headers: Additional headers to include

        Returns:
            requests.Response object with custom json() method
        """
        payload = json.dumps(data)
        request_headers = self.headers(headers)

        logger.info(f"Making POST request to: {self.url}")
        logger.debug(f"Request payload keys: {list(data.keys()) if data else []}")

        try:
            response = requests.post(
                self.url,
                data=payload,
                headers=request_headers,
                timeout=self.timeout,
            )
            logger.debug(f"Response status: {response.status_code}")
            return self._handle_response(response)

        except requests.Timeout:
            logger.error(f"Request timeout after {self.timeout} seconds")
            raise
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise

    def _handle_response(self, response: requests.Response) -> requests.Response:
        """
        Process the response and attach a safe json() method.

        Args:
            response: The raw requests.Response object

        Returns:
            Response with custom json() method for safe parsing
        """

        def custom_json():
            try:
                parsed_json = json.loads(response.text)
                logger.debug("Successfully parsed JSON response")
                return parsed_json
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}, response text: {response.text}")
                return {"error": response.text}
            except Exception as e:
                logger.error(f"Unknown error parsing JSON: {e}")
                return {}

        if response.status_code >= 400:
            logger.warning(f"Request failed with status {response.status_code}: {response.text}")
        else:
            logger.debug(f"Request successful with status {response.status_code}")

        response.json = custom_json
        return response


def generate_request_id() -> str:
    """Generate a unique numeric request ID (10 digits) for Kutumba API."""
    import random
    import time

    # 7 digits from timestamp (zero-padded) + 3 random digits = 10 digits total
    return f"{int(time.time()) % 10**7:07d}{random.randint(100, 999)}"
