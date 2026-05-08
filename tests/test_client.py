"""
Unit tests for bot/client.py — Binance API client.

Tests use monkeypatching to avoid real network calls.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from bot.client import BinanceClient, BinanceAPIError, BinanceNetworkError, BinanceResponseError


# =====================================================================
# Fixtures
# =====================================================================

@pytest.fixture
def client():
    """Return a BinanceClient with dummy credentials."""
    return BinanceClient(
        api_key="test_api_key_12345",
        api_secret="test_api_secret_67890",
        base_url="https://testnet.binancefuture.com",
    )


def _mock_response(status_code: int, json_data: dict) -> MagicMock:
    """Create a mock requests.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.text = json.dumps(json_data)
    return resp


# =====================================================================
# Tests
# =====================================================================

class TestBinanceClientInit:
    def test_missing_api_key_raises(self, monkeypatch):
        monkeypatch.delenv("BINANCE_API_KEY", raising=False)
        monkeypatch.delenv("BINANCE_API_SECRET", raising=False)
        with pytest.raises(ValueError, match="BINANCE_API_KEY"):
            BinanceClient(api_key="", api_secret="secret")

    def test_missing_api_secret_raises(self, monkeypatch):
        monkeypatch.delenv("BINANCE_API_KEY", raising=False)
        monkeypatch.delenv("BINANCE_API_SECRET", raising=False)
        with pytest.raises(ValueError, match="BINANCE_API_SECRET"):
            BinanceClient(api_key="key", api_secret="")


class TestPlaceOrder:
    def test_successful_order(self, client):
        mock_resp = _mock_response(200, {
            "orderId": 12345,
            "status": "FILLED",
            "symbol": "BTCUSDT",
        })

        with patch.object(client._session, "request", return_value=mock_resp):
            result = client.place_order({"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quantity": 0.01})

        assert result["orderId"] == 12345
        assert result["status"] == "FILLED"

    def test_api_error_raises(self, client):
        mock_resp = _mock_response(400, {
            "code": -1121,
            "msg": "Invalid symbol.",
        })

        with patch.object(client._session, "request", return_value=mock_resp):
            with pytest.raises(BinanceAPIError) as exc_info:
                client.place_order({"symbol": "INVALID", "side": "BUY", "type": "MARKET", "quantity": 0.01})

        assert exc_info.value.code == -1121
        assert "Invalid symbol" in exc_info.value.message

    def test_invalid_json_raises(self, client):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = ValueError("No JSON")
        mock_resp.text = "not json"

        with patch.object(client._session, "request", return_value=mock_resp):
            with pytest.raises(BinanceResponseError, match="Could not parse"):
                client.place_order({"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quantity": 0.01})

    def test_network_error_retries_and_raises(self, client):
        with patch.object(
            client._session,
            "request",
            side_effect=requests.ConnectionError("Connection refused"),
        ):
            with pytest.raises(BinanceNetworkError, match="Failed after"):
                client.place_order({"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quantity": 0.01})

    def test_timeout_error_retries_and_raises(self, client):
        with patch.object(
            client._session,
            "request",
            side_effect=requests.Timeout("Request timed out"),
        ):
            with pytest.raises(BinanceNetworkError, match="Failed after"):
                client.place_order({"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quantity": 0.01})


class TestSigning:
    def test_sign_adds_timestamp_and_signature(self, client):
        params = {"symbol": "BTCUSDT"}
        signed = client._sign(params)

        assert "timestamp" in signed
        assert "signature" in signed
        assert isinstance(signed["timestamp"], int)
        assert len(signed["signature"]) == 64  # SHA256 hex digest length
