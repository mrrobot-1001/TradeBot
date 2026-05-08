"""
Pure input-validation functions — zero I/O, zero side-effects.

Each function either returns a normalized value or raises ``ValueError``
with a user-friendly message.
"""

from __future__ import annotations

import re
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_LIMIT"}
VALID_TIF_VALUES = {"GTC", "IOC", "FOK"}

# ---------------------------------------------------------------------------
# Public validators
# ---------------------------------------------------------------------------


def validate_symbol(symbol: Optional[str]) -> str:
    """Validate and normalize a trading symbol.

    Rules:
        - Non-empty
        - Alphanumeric only (no special characters)
        - Returned as uppercase

    Raises:
        ValueError: If *symbol* is empty, ``None``, or contains
            non-alphanumeric characters.
    """
    if not symbol or not symbol.strip():
        raise ValueError("Symbol must be a non-empty string.")

    cleaned = symbol.strip().upper()

    if not re.fullmatch(r"[A-Z0-9]+", cleaned):
        raise ValueError(
            f"Symbol '{symbol}' is invalid — only alphanumeric characters are allowed."
        )

    return cleaned


def validate_side(side: Optional[str]) -> str:
    """Validate and normalize order side.

    Accepts case-insensitive input; returns ``BUY`` or ``SELL``.

    Raises:
        ValueError: If *side* is not ``BUY`` or ``SELL``.
    """
    if not side or not side.strip():
        raise ValueError("Side must be specified (BUY or SELL).")

    normalized = side.strip().upper()

    if normalized not in VALID_SIDES:
        raise ValueError(
            f"Side '{side}' is invalid — must be BUY or SELL."
        )

    return normalized


def validate_order_type(order_type: Optional[str]) -> str:
    """Validate and normalize order type.

    Accepts case-insensitive input; returns one of
    ``MARKET``, ``LIMIT``, or ``STOP_LIMIT``.

    Raises:
        ValueError: If *order_type* is not recognized.
    """
    if not order_type or not order_type.strip():
        raise ValueError("Order type must be specified (MARKET, LIMIT, or STOP_LIMIT).")

    normalized = order_type.strip().upper().replace("-", "_")

    if normalized not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Order type '{order_type}' is invalid — must be MARKET, LIMIT, or STOP_LIMIT."
        )

    return normalized


def validate_quantity(quantity: Optional[float]) -> float:
    """Validate order quantity.

    Rules:
        - Must be a positive number
        - Zero and negative values are rejected

    Raises:
        ValueError: If *quantity* is ``None``, zero, or negative.
    """
    if quantity is None:
        raise ValueError("Quantity is required.")

    try:
        qty = float(quantity)
    except (TypeError, ValueError):
        raise ValueError(f"Quantity '{quantity}' is not a valid number.")

    if qty <= 0:
        raise ValueError(
            f"Quantity must be a positive number, got {qty}."
        )

    return qty


def validate_price(
    price: Optional[float],
    order_type: str,
) -> Optional[float]:
    """Validate order price relative to the order type.

    Rules:
        - **LIMIT / STOP_LIMIT**: *price* is required and must be positive.
        - **MARKET**: *price* must **not** be provided.

    Raises:
        ValueError: If price constraints are violated.
    """
    needs_price = order_type in {"LIMIT", "STOP_LIMIT"}

    if needs_price:
        if price is None:
            raise ValueError(
                f"--price is required for {order_type} orders."
            )
        try:
            p = float(price)
        except (TypeError, ValueError):
            raise ValueError(f"Price '{price}' is not a valid number.")

        if p <= 0:
            raise ValueError(
                f"Price must be a positive number, got {p}."
            )
        return p

    # MARKET orders must NOT have a price
    if price is not None:
        raise ValueError(
            "Price must not be specified for MARKET orders."
        )

    return None


def validate_stop_price(
    stop_price: Optional[float],
    order_type: str,
) -> Optional[float]:
    """Validate stop price — required only for STOP_LIMIT orders.

    Raises:
        ValueError: If *stop_price* is missing for STOP_LIMIT or provided
            for other order types.
    """
    if order_type == "STOP_LIMIT":
        if stop_price is None:
            raise ValueError(
                "--stop-price is required for STOP_LIMIT orders."
            )
        try:
            sp = float(stop_price)
        except (TypeError, ValueError):
            raise ValueError(f"Stop price '{stop_price}' is not a valid number.")

        if sp <= 0:
            raise ValueError(
                f"Stop price must be a positive number, got {sp}."
            )
        return sp

    if stop_price is not None:
        raise ValueError(
            f"Stop price must not be specified for {order_type} orders."
        )

    return None


def validate_time_in_force(tif: Optional[str], order_type: str) -> Optional[str]:
    """Validate time-in-force value.

    Defaults to ``GTC`` for LIMIT/STOP_LIMIT if not provided.

    Raises:
        ValueError: If *tif* is not a recognized value.
    """
    if order_type == "MARKET":
        return None  # TIF is irrelevant for market orders

    if tif is None:
        return "GTC"  # default per PRD

    normalized = tif.strip().upper()
    if normalized not in VALID_TIF_VALUES:
        raise ValueError(
            f"Time-in-force '{tif}' is invalid — must be GTC, IOC, or FOK."
        )
    return normalized
