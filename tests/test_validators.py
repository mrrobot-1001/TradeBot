"""
Unit tests for bot/validators.py — pure validation functions.

Run with::

    pytest tests/ -v
"""

from __future__ import annotations

import pytest

from bot.validators import (
    validate_symbol,
    validate_side,
    validate_order_type,
    validate_quantity,
    validate_price,
    validate_stop_price,
    validate_time_in_force,
)


# =====================================================================
# validate_symbol
# =====================================================================

class TestValidateSymbol:
    def test_valid_uppercase(self):
        assert validate_symbol("BTCUSDT") == "BTCUSDT"

    def test_valid_lowercase_normalized(self):
        assert validate_symbol("ethusdt") == "ETHUSDT"

    def test_valid_mixed_case(self):
        assert validate_symbol("BtcUsdt") == "BTCUSDT"

    def test_with_whitespace(self):
        assert validate_symbol("  BTCUSDT  ") == "BTCUSDT"

    def test_alphanumeric_with_digits(self):
        assert validate_symbol("1INCHUSDT") == "1INCHUSDT"

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            validate_symbol("")

    def test_none_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            validate_symbol(None)

    def test_special_chars_raises(self):
        with pytest.raises(ValueError, match="alphanumeric"):
            validate_symbol("BTC-USDT")

    def test_spaces_inside_raises(self):
        with pytest.raises(ValueError, match="alphanumeric"):
            validate_symbol("BTC USDT")


# =====================================================================
# validate_side
# =====================================================================

class TestValidateSide:
    def test_buy_uppercase(self):
        assert validate_side("BUY") == "BUY"

    def test_sell_lowercase(self):
        assert validate_side("sell") == "SELL"

    def test_buy_mixed_case(self):
        assert validate_side("Buy") == "BUY"

    def test_invalid_side(self):
        with pytest.raises(ValueError, match="BUY or SELL"):
            validate_side("HOLD")

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="must be specified"):
            validate_side("")

    def test_none_raises(self):
        with pytest.raises(ValueError, match="must be specified"):
            validate_side(None)


# =====================================================================
# validate_order_type
# =====================================================================

class TestValidateOrderType:
    def test_market(self):
        assert validate_order_type("MARKET") == "MARKET"

    def test_limit_lowercase(self):
        assert validate_order_type("limit") == "LIMIT"

    def test_stop_limit_underscore(self):
        assert validate_order_type("STOP_LIMIT") == "STOP_LIMIT"

    def test_stop_limit_hyphen(self):
        assert validate_order_type("stop-limit") == "STOP_LIMIT"

    def test_invalid_type(self):
        with pytest.raises(ValueError, match="MARKET, LIMIT, or STOP_LIMIT"):
            validate_order_type("TRAILING_STOP")

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="must be specified"):
            validate_order_type("")


# =====================================================================
# validate_quantity
# =====================================================================

class TestValidateQuantity:
    def test_positive_float(self):
        assert validate_quantity(0.01) == 0.01

    def test_positive_int(self):
        assert validate_quantity(1) == 1.0

    def test_zero_raises(self):
        with pytest.raises(ValueError, match="positive"):
            validate_quantity(0)

    def test_negative_raises(self):
        with pytest.raises(ValueError, match="positive"):
            validate_quantity(-1.5)

    def test_none_raises(self):
        with pytest.raises(ValueError, match="required"):
            validate_quantity(None)


# =====================================================================
# validate_price
# =====================================================================

class TestValidatePrice:
    def test_limit_with_price(self):
        assert validate_price(95000.0, "LIMIT") == 95000.0

    def test_limit_missing_price_raises(self):
        with pytest.raises(ValueError, match="required for LIMIT"):
            validate_price(None, "LIMIT")

    def test_limit_zero_price_raises(self):
        with pytest.raises(ValueError, match="positive"):
            validate_price(0, "LIMIT")

    def test_limit_negative_price_raises(self):
        with pytest.raises(ValueError, match="positive"):
            validate_price(-100, "LIMIT")

    def test_market_no_price(self):
        assert validate_price(None, "MARKET") is None

    def test_market_with_price_raises(self):
        with pytest.raises(ValueError, match="must not be specified"):
            validate_price(95000.0, "MARKET")

    def test_stop_limit_with_price(self):
        assert validate_price(3200.0, "STOP_LIMIT") == 3200.0

    def test_stop_limit_missing_price_raises(self):
        with pytest.raises(ValueError, match="required for STOP_LIMIT"):
            validate_price(None, "STOP_LIMIT")


# =====================================================================
# validate_stop_price
# =====================================================================

class TestValidateStopPrice:
    def test_stop_limit_with_stop_price(self):
        assert validate_stop_price(3150.0, "STOP_LIMIT") == 3150.0

    def test_stop_limit_missing_raises(self):
        with pytest.raises(ValueError, match="required for STOP_LIMIT"):
            validate_stop_price(None, "STOP_LIMIT")

    def test_stop_limit_zero_raises(self):
        with pytest.raises(ValueError, match="positive"):
            validate_stop_price(0, "STOP_LIMIT")

    def test_market_with_stop_price_raises(self):
        with pytest.raises(ValueError, match="must not be specified"):
            validate_stop_price(3150.0, "MARKET")

    def test_limit_with_stop_price_raises(self):
        with pytest.raises(ValueError, match="must not be specified"):
            validate_stop_price(3150.0, "LIMIT")

    def test_market_no_stop_price(self):
        assert validate_stop_price(None, "MARKET") is None


# =====================================================================
# validate_time_in_force
# =====================================================================

class TestValidateTimeInForce:
    def test_market_returns_none(self):
        assert validate_time_in_force(None, "MARKET") is None

    def test_limit_defaults_to_gtc(self):
        assert validate_time_in_force(None, "LIMIT") == "GTC"

    def test_limit_explicit_ioc(self):
        assert validate_time_in_force("IOC", "LIMIT") == "IOC"

    def test_limit_explicit_fok(self):
        assert validate_time_in_force("fok", "LIMIT") == "FOK"

    def test_invalid_tif_raises(self):
        with pytest.raises(ValueError, match="GTC, IOC, or FOK"):
            validate_time_in_force("DAY", "LIMIT")
