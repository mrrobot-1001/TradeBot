import gradio as gr
import os
import json
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

def place_order_gradio(symbol, side, order_type, qty, price, stop_price, tif):
    try:
        v_symbol = validate_symbol(symbol)
        v_side = validate_side(side)
        v_order_type = validate_order_type(order_type)
        v_quantity = validate_quantity(qty)
        # Price is optional for MARKET
        v_price = validate_price(price if price else None, v_order_type)
        v_stop_price = validate_stop_price(stop_price if stop_price else None, v_order_type)
        v_tif = validate_time_in_force(tif if tif else None, v_order_type)

        client = BinanceClient()

        if v_order_type == "MARKET":
            result = place_market_order(client, v_symbol, v_side, v_quantity)
        elif v_order_type == "LIMIT":
            result = place_limit_order(client, v_symbol, v_side, v_quantity, v_price, v_tif or "GTC")
        elif v_order_type == "STOP_LIMIT":
            result = place_stop_limit_order(client, v_symbol, v_side, v_quantity, v_price, v_stop_price, v_tif or "GTC")
        else:
            return "Unsupported order type", None

        return "✅ Order placed successfully", json.dumps(result, indent=2)

    except ValueError as e:
        return f"❌ Validation Error: {str(e)}", None
    except BinanceAPIError as e:
        return f"❌ API Error [code {e.code}]: {e.message}", None
    except BinanceNetworkError as e:
        return f"❌ Network error: {e.reason}", None
    except BinanceResponseError as e:
        return f"❌ Response error: {e.reason}", None
    except Exception as e:
        return f"❌ Unexpected error: {str(e)}", None

with gr.Blocks(title="Binance Futures Testnet Bot") as demo:
    gr.Markdown("# 🤖 Binance Futures Demo Trading Bot")
    gr.Markdown("Place orders on the Binance Futures Demo Trading platform. Ensure you have the required secrets configured in the Space settings.")
    
    with gr.Row():
        with gr.Column():
            symbol = gr.Textbox(label="Symbol", value="BTCUSDT", placeholder="e.g. BTCUSDT")
            side = gr.Dropdown(choices=["BUY", "SELL"], label="Side", value="BUY")
            order_type = gr.Dropdown(choices=["MARKET", "LIMIT", "STOP_LIMIT"], label="Order Type", value="MARKET")
            qty = gr.Number(label="Quantity", value=0.01)
            
            with gr.Accordion("Advanced Parameters (For Limit / Stop-Limit)", open=False):
                price = gr.Number(label="Price", value=0)
                stop_price = gr.Number(label="Stop Price", value=0)
                tif = gr.Dropdown(choices=["GTC", "IOC", "FOK"], label="Time in Force", value="GTC")
                
            submit_btn = gr.Button("Submit Order", variant="primary")
            
        with gr.Column():
            status_text = gr.Textbox(label="Status", interactive=False)
            response_json = gr.Code(label="Order Response", language="json", interactive=False)

    submit_btn.click(
        fn=place_order_gradio,
        inputs=[symbol, side, order_type, qty, price, stop_price, tif],
        outputs=[status_text, response_json]
    )

if __name__ == "__main__":
    demo.launch()
