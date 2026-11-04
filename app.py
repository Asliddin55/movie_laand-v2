import os
import sys
import asyncio
import threading
import logging
try:
    import gradio as gr
    _HAS_GRADIO = True
except ImportError:
    _HAS_GRADIO = False
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)

def start_bot_loop():
    import main
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main.main())
    except Exception as e:
        logging.error(f"Bot loop error: {e}")

if __name__ == "__main__":
    if _HAS_GRADIO:
        # Telegram botni alohida fonda uzluksiz ishlatish
        bot_thread = threading.Thread(target=start_bot_loop, daemon=True)
        bot_thread.start()
        with gr.Blocks(title="Movie Land Ultra Bot 🎬") as demo:
            gr.Markdown("# 🎬 Movie Land Ultra Bot (v2.0) 24/7 ishlamoqda!")
            gr.Markdown("Rasmiy bot: [@movieeland_bot](https://t.me/movieeland_bot)")
            gr.Markdown("Holati: **Online (Yashil / Doimiy)** ✅")
        port = int(os.getenv("PORT", 7860))
        demo.launch(server_name="0.0.0.0", server_port=port, ssr=False)
    else:
        # To'g'ridan-to'g'ri bot asosiy kodini yurgazish
        import main
        asyncio.run(main.main())
