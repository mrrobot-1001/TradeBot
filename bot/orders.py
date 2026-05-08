"""
Order-type construction and business logic.

Each public function builds the correct parameter payload per the Binance
Futures API specification, delegates execution to :mod:`bot.client`, and
returns a normalized response dictionary.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from bot.client import BinanceClient
from bot.logging_config import get_logger

logger = get_logger("orders")

# ---------------------------------------------------------------------------
# Response normalizer
# ---------------------------------------------------------------------------


def _normalize_response(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Extract the fields callers care about into a clean dict.

    This shields upstream code from changes in the raw API shape.
    """
    return {
        "orderId": raw.get("orderId"),
        "symbol": raw.get("symbol"),
        "side": raw.get("side"),
        "type": raw.get("type"),
        "status": raw.get("status"),
        "origQty": raw.get("origQty"),
        "executedQty": raw.get("executedQty"),
        "avgPrice": raw.get("avgPrice", raw.get("price", "N/A")),
        "timeInForce": raw.get("timeInForce"),
        "clientOrderId": raw.get("clientOrderId"),
        "updateTime": raw.get("updateTime"),
    }


# ---------------------------------------------------------------------------
# Order placement functions
# ---------------------------------------------------------------------------


def place_market_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: float,
) -> Dict[str, Any]:
    """Place a MARKET order on Binance Futures Testnet.

    Args:
        client: An authenticated :class:`BinanceClient` instance.
        symbol: Trading pair (e.g. ``BTCUSDT``).
        side: ``BUY`` or ``SELL``.
        quantity: Order quantity.

    Returns:
        Normalized response dict with order details.
    """
    params: Dict[str, Any] = {
        "symbol": symbol,
        "side": side,
        "type": "MARKET",
        "quantity": quantity,
    }

    logger.info(
        "Placing MARKET %s order — symbol=%s qty=%s",
        side,
        symbol,
        quantity,
    )

    raw = client.place_order(params)
    result = _normalize_response(raw)

    logger.info(
        "MARKET order result — orderId=%s status=%s executedQty=%s",
        result["orderId"],
        result["status"],
        result["executedQty"],
    )

    return result


def place_limit_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: float,
    price: float,
    time_in_force: str = "GTC",
) -> Dict[str, Any]:
    """Place a LIMIT order on Binance Futures Testnet.

    Args:
        client: An authenticated :class:`BinanceClient` instance.
        symbol: Trading pair (e.g. ``BTCUSDT``).
        side: ``BUY`` or ``SELL``.
        quantity: Order quantity.
        price: Limit price.
        time_in_force: Time-in-force policy (default ``GTC``).

    Returns:
        Normalized response dict with order details.
    """
    params: Dict[str, Any] = {
        "symbol": symbol,
        "side": side,
        "type": "LIMIT",
        "quantity": quantity,
        "price": price,
        "timeInForce": time_in_force,
    }

    logger.info(
        "Placing LIMIT %s order — symbol=%s qty=%s price=%s tif=%s",
        side,
        symbol,
        quantity,
        price,
        time_in_force,
    )

    raw = client.place_order(params)
    result = _normalize_response(raw)

    logger.info(
        "LIMIT order result — orderId=%s status=%s executedQty=%s",
        result["orderId"],
        result["status"],
        result["executedQty"],
    )

    return result


def place_stop_limit_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: float,
    price: float,
    stop_price: float,
    time_in_force: str = "GTC",
) -> Dict[str, Any]:
    """Place a STOP_LIMIT (STOP) order on Binance Futures Testnet.

    The order becomes a limit order when *stop_price* is reached.

    Args:
        client: An authenticated :class:`BinanceClient` instance.
        symbol: Trading pair (e.g. ``ETHUSDT``).
        side: ``BUY`` or ``SELL``.
        quantity: Order quantity.
        price: Limit price once triggered.
        stop_price: Trigger price.
        time_in_force: Time-in-force policy (default ``GTC``).

    Returns:
        Normalized response dict with order details.
    """
    params: Dict[str, Any] = {
        "symbol": symbol,
        "side": side,
        "type": "STOP",
        "quantity": quantity,
        "price": price,
        "stopPrice": stop_price,
        "timeInForce": time_in_force,
    }

    logger.info(
        "Placing STOP_LIMIT %s order — symbol=%s qty=%s price=%s stop=%s tif=%s",
        side,
        symbol,
        quantity,
        price,
        stop_price,
        time_in_force,
    )

    raw = client.place_order(params)
    result = _normalize_response(raw)

    logger.info(
        "STOP_LIMIT order result — orderId=%s status=%s executedQty=%s",
        result["orderId"],
        result["status"],
        result["executedQty"],
    )

    return result
