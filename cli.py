#!/usr/bin/env python3
"""
CLI entry point for the Binance Futures Testnet Trading Bot.

Parses command-line arguments, validates inputs, prints a request summary,
submits the order, and prints the response with a clear success/failure
indicator.

Usage examples::

    python cli.py --symbol BTCUSDT --side BUY --order-type MARKET --qty 0.01
    python cli.py --symbol BTCUSDT --side SELL --order-type LIMIT --qty 0.01 --price 95000
    python cli.py --symbol ETHUSDT --side BUY --order-type STOP_LIMIT --qty 0.1 \\
                  --price 3200 --stop-price 3150
"""

from __future__ import annotations

import sys
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Confirm

from bot.client import BinanceClient, BinanceAPIError, BinanceNetworkError, BinanceResponseError
from bot.orders import place_market_order, place_limit_order, place_stop_limit_order
from bot.validators import (
    validate_symbol,
    validate_side,
    validate_order_type,
    validate_quantity,
    validate_price,
    validate_stop_price,
    validate_time_in_force,
)
from bot.logging_config import get_logger

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="trading-bot",
    help="Binance Futures Testnet Trading Bot — place MARKET, LIMIT, and STOP_LIMIT orders.",
    add_completion=False,
    rich_markup_mode="rich",
)

console = Console()
error_console = Console(stderr=True)
logger = get_logger("cli")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _print_request_summary(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: Optional[float] = None,
    stop_price: Optional[float] = None,
    time_in_force: Optional[str] = None,
) -> None:
    """Print a rich panel summarizing the order about to be submitted."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="bold cyan", min_width=14)
    table.add_column("Value", style="white")

    table.add_row("Symbol", symbol)
    table.add_row("Side", f"[green]{side}[/green]" if side == "BUY" else f"[red]{side}[/red]")
    table.add_row("Type", order_type)
    table.add_row("Quantity", str(quantity))

    if price is not None:
        table.add_row("Price", str(price))
    if stop_price is not None:
        table.add_row("Stop Price", str(stop_price))
    if time_in_force is not None:
        table.add_row("Time In Force", time_in_force)

    console.print()
    console.print(Panel(table, title="[bold]📋 Order Request Summary[/bold]", border_style="cyan", expand=False))


def _print_response(result: dict) -> None:
    """Print a rich panel with the order response fields."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="bold green", min_width=14)
    table.add_column("Value", style="white")

    table.add_row("Order ID", str(result.get("orderId", "N/A")))
    table.add_row("Status", str(result.get("status", "N/A")))
    table.add_row("Executed Qty", str(result.get("executedQty", "N/A")))
    table.add_row("Avg Price", str(result.get("avgPrice", "N/A")))

    if result.get("clientOrderId"):
        table.add_row("Client OID", str(result["clientOrderId"]))

    console.print()
    console.print(Panel(table, title="[bold]📦 Order Response[/bold]", border_style="green", expand=False))


def _fail(message: str, exit_code: int = 1) -> None:
    """Print failure message and exit."""
    error_console.print(f"\n[bold red]❌ Error:[/bold red] {message}")
    logger.error("CLI failure: %s", message)
    raise typer.Exit(code=exit_code)


# ---------------------------------------------------------------------------
# Main command
# ---------------------------------------------------------------------------


@app.command()
def place_order(
    symbol: str = typer.Option(..., "--symbol", "-s", help="Trading pair (e.g. BTCUSDT)"),
    side: str = typer.Option(..., "--side", "-S", help="Order side: BUY or SELL"),
    order_type: str = typer.Option(..., "--order-type", "-t", help="Order type: MARKET, LIMIT, or STOP_LIMIT"),
    qty: float = typer.Option(..., "--qty", "-q", help="Order quantity (positive float)"),
    price: Optional[float] = typer.Option(None, "--price", "-p", help="Limit price (required for LIMIT/STOP_LIMIT)"),
    stop_price: Optional[float] = typer.Option(None, "--stop-price", help="Stop trigger price (STOP_LIMIT only)"),
    tif: Optional[str] = typer.Option(None, "--tif", help="Time-in-force: GTC, IOC, or FOK (default GTC)"),
    confirm: bool = typer.Option(True, "--confirm/--no-confirm", help="Prompt for confirmation before placing order"),
) -> None:
    """Place an order on Binance Futures Testnet (USDT-M)."""

    # ------------------------------------------------------------------
    # 1. Validate all inputs
    # ------------------------------------------------------------------
    try:
        v_symbol = validate_symbol(symbol)
        v_side = validate_side(side)
        v_order_type = validate_order_type(order_type)
        v_quantity = validate_quantity(qty)
        v_price = validate_price(price, v_order_type)
        v_stop_price = validate_stop_price(stop_price, v_order_type)
        v_tif = validate_time_in_force(tif, v_order_type)
    except ValueError as exc:
        _fail(str(exc))
        return  # unreachable but keeps type-checkers happy

    # ------------------------------------------------------------------
    # 2. Print request summary
    # ------------------------------------------------------------------
    _print_request_summary(
        symbol=v_symbol,
        side=v_side,
        order_type=v_order_type,
        quantity=v_quantity,
        price=v_price,
        stop_price=v_stop_price,
        time_in_force=v_tif,
    )

    # ------------------------------------------------------------------
    # 3. Confirmation prompt (bonus UX)
    # ------------------------------------------------------------------
    if confirm:
        console.print()
        if not Confirm.ask("[bold yellow]Submit this order?[/bold yellow]", default=True):
            console.print("\n[dim]Order cancelled by user.[/dim]")
            raise typer.Exit(code=0)

    # ------------------------------------------------------------------
    # 4. Initialize client & place order
    # ------------------------------------------------------------------
    try:
        client = BinanceClient()
    except ValueError as exc:
        _fail(str(exc))
        return

    try:
        if v_order_type == "MARKET":
            result = place_market_order(client, v_symbol, v_side, v_quantity)

        elif v_order_type == "LIMIT":
            assert v_price is not None  # guaranteed by validator
            result = place_limit_order(
                client, v_symbol, v_side, v_quantity, v_price, v_tif or "GTC"
            )

        elif v_order_type == "STOP_LIMIT":
            assert v_price is not None and v_stop_price is not None
            result = place_stop_limit_order(
                client, v_symbol, v_side, v_quantity, v_price, v_stop_price, v_tif or "GTC"
            )

        else:
            _fail(f"Unsupported order type: {v_order_type}")
            return

    except BinanceAPIError as exc:
        logger.exception("Binance API error during order placement")
        _fail(f"API Error [code {exc.code}]: {exc.message}")
        return

    except BinanceNetworkError as exc:
        logger.exception("Network error during order placement")
        _fail(f"Network error: {exc.reason}")
        return

    except BinanceResponseError as exc:
        logger.exception("Invalid response from Binance")
        _fail(f"Response error: {exc.reason}")
        return

    except Exception as exc:
        logger.exception("Unexpected error during order placement")
        _fail(f"Unexpected error: {exc}")
        return

    # ------------------------------------------------------------------
    # 5. Print response & success message
    # ------------------------------------------------------------------
    _print_response(result)
    console.print("\n[bold green]✅ Order placed successfully.[/bold green]\n")
    logger.info("Order placed successfully — orderId=%s", result.get("orderId"))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app()
