"""
Binance Futures Testnet REST API client.

Responsibilities:
    - HMAC-SHA256 request signing
    - ``X-MBX-APIKEY`` header injection
    - Request timeout and basic retry logic
    - Typed exception raising on API / network errors
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv

from bot.logging_config import get_logger

# ---------------------------------------------------------------------------
# Load .env early so every module gets the keys
# ---------------------------------------------------------------------------
load_dotenv()

logger = get_logger("client")

# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class BinanceAPIError(Exception):
    """Raised when the Binance API returns an error response (4xx / 5xx)."""

    def __init__(self, status_code: int, code: int, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(f"API Error [code {code}]: {message}")


class BinanceNetworkError(Exception):
    """Raised on connectivity / timeout failures."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Network error: {reason}")


class BinanceResponseError(Exception):
    """Raised when the response body is not valid JSON."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Invalid response: {reason}")


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

DEFAULT_BASE_URL = "https://demo-fapi.binance.com"
REQUEST_TIMEOUT = 10  # seconds
MAX_RETRIES = 2
RETRY_DELAY = 1  # seconds


class BinanceClient:
    """Low-level HTTP client for Binance Futures Testnet.

    Handles authentication, signing, and request execution.
    All public methods raise one of the typed exceptions above on failure.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        self.api_key: str = api_key or os.getenv("BINANCE_API_KEY", "")
        self.api_secret: str = api_secret or os.getenv("BINANCE_API_SECRET", "")
        self.base_url: str = (
            base_url or os.getenv("BINANCE_BASE_URL", DEFAULT_BASE_URL)
        ).rstrip("/")

        if not self.api_key:
            raise ValueError(
                "BINANCE_API_KEY is not set. "
                "Add it to your .env file or pass it explicitly."
            )
        if not self.api_secret:
            raise ValueError(
                "BINANCE_API_SECRET is not set. "
                "Add it to your .env file or pass it explicitly."
            )

        self._session = requests.Session()
        self._session.headers.update({
            "X-MBX-APIKEY": self.api_key,
        })

        logger.info(
            "BinanceClient initialized — base_url=%s, api_key=%s…",
            self.base_url,
            self.api_key[:8],
        )

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def place_order(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Submit a new order via ``POST /fapi/v1/order``.

        Args:
            params: Order parameters (symbol, side, type, quantity, etc.).

        Returns:
            Parsed JSON response from Binance.

        Raises:
            BinanceAPIError: On 4xx/5xx with a Binance error body.
            BinanceNetworkError: On connectivity / timeout failures.
            BinanceResponseError: On non-JSON response body.
        """
        endpoint = "/fapi/v1/order"
        return self._signed_request("POST", endpoint, params)

    def get_exchange_info(self) -> Dict[str, Any]:
        """Fetch exchange metadata via ``GET /fapi/v1/exchangeInfo``."""
        endpoint = "/fapi/v1/exchangeInfo"
        return self._public_request("GET", endpoint)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _sign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Add ``timestamp`` and ``signature`` to *params*."""
        params["timestamp"] = int(time.time() * 1000)
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    def _signed_request(
        self,
        method: str,
        endpoint: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a signed (authenticated) request with retry logic."""
        signed_params = self._sign(dict(params))  # copy to avoid mutation
        return self._execute(method, endpoint, signed_params)

    def _public_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute an unsigned (public) request."""
        return self._execute(method, endpoint, params or {})

    def _execute(
        self,
        method: str,
        endpoint: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Send the HTTP request with retries and error handling."""
        url = f"{self.base_url}{endpoint}"

        # Log outgoing request (secret is redacted by the logging filter)
        logger.debug(
            ">>> %s %s params=%s",
            method,
            url,
            params,
        )

        last_exception: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self._session.request(
                    method=method,
                    url=url,
                    params=params if method == "GET" else None,
                    data=params if method != "GET" else None,
                    timeout=REQUEST_TIMEOUT,
                )

                # Log raw response
                logger.debug(
                    "<<< %s %s status=%d body=%s",
                    method,
                    endpoint,
                    response.status_code,
                    response.text,
                )

                # Parse JSON
                try:
                    data = response.json()
                except ValueError as exc:
                    raise BinanceResponseError(
                        f"Could not parse response as JSON: {response.text[:200]}"
                    ) from exc

                # Check for API-level errors
                if response.status_code >= 400:
                    error_code = data.get("code", response.status_code)
                    error_msg = data.get("msg", "Unknown error")
                    raise BinanceAPIError(
                        status_code=response.status_code,
                        code=error_code,
                        message=error_msg,
                    )

                logger.info(
                    "API call succeeded — %s %s (attempt %d)",
                    method,
                    endpoint,
                    attempt,
                )
                return data

            except (requests.ConnectionError, requests.Timeout) as exc:
                last_exception = exc
                logger.warning(
                    "Network error on attempt %d/%d: %s",
                    attempt,
                    MAX_RETRIES,
                    exc,
                )
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY)

            except (BinanceAPIError, BinanceResponseError):
                # Don't retry on API-level or parse errors
                raise

        # Exhausted retries
        raise BinanceNetworkError(
            f"Failed after {MAX_RETRIES} attempts: {last_exception}"
        )
