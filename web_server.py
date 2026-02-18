"""
Dr. Inker LABS - Web Server + Telegram Bot (Webhook Mode)
Lazy-initializes bot on first request — works with gunicorn.
"""
import os
import json
import asyncio
import logging
import threading
import time
from flask import Flask, render_template, jsonify, request, Response
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    PreCheckoutQueryHandler, filters
)
from config import TELEGRAM_BOT_TOKEN, WEBAPP_URL
from database import (
    init_db, get_scan_history, get_energy_status, get_leaderboard, get_or_create_user
)
from bot import (
    start_command, help_command, scan_command, history_command,
    refer_command, premium_command, leaderboard_command,
    handle_photo, handle_document_image, handle_text,
    callback_handler, pre_checkout_handler, successful_payment_handler
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder="templates", static_folder="static")

# Bot state — lazy initialized
_bot_app = None
_bot_loop = None
_initialized = False
_init_lock = threading.Lock()


# ═══════════════════════════════════════════
# LAZY BOT INITIALIZATION
# ═══════════════════════════════════════════

def _build_application():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("scan", scan_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("refer", refer_command))
    application.add_handler(CommandHandler("premium", premium_command))
    application.add_handler(CommandHandler("leaderboard", leaderboard_command))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.Document.IMAGE, handle_document_image))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(CallbackQueryHandler(callback_handler))
    application.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    return application


async def _async_init():
    """Async init: build app, start it, set webhook."""
    global _bot_app
    _bot_app = _build_application()
    await _bot_app.initialize()
    await _bot_app.start()
    logger.info("✅ Bot application initialized")


def _run_event_loop():
    """Run asyncio event loop in background thread."""
    global _bot_loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    _bot_loop = loop
    loop.run_forever()


def _ensure_bot():
    """Lazy-init bot on first request. Thread-safe."""
    global _initialized
    if _initialized:
        return
    with _init_lock:
        if _initialized:
            return
        logger.info("🤖 Initializing bot (first request)...")

        # Start event loop thread
        thread = threading.Thread(target=_run_event_loop, daemon=True)
        thread.start()

        # Wait for loop to be ready
        for _ in range(50):
            if _bot_loop is not None:
                break
            time.sleep(0.1)

        # Initialize bot in the event loop
        future = asyncio.run_coroutine_threadsafe(_async_init(), _bot_loop)
        future.result(timeout=30)

        _initialized = True
        logger.info("🔬 BERT Chart Scanner is live!")


# ═══════════════════════════════════════════
# WEB ROUTES
# ═══════════════════════════════════════════

@app.route("/")
def index():
    return jsonify({"status": "ok", "app": "BERT Chart Scanner", "mode": "webhook"})


@app.route("/app")
def mini_app():
    user_id = request.args.get("user_id", "0")
    return render_template("mini_app.html", user_id=user_id)


@app.route("/api/history/<int:user_id>")
def api_history(user_id):
    limit = request.args.get("limit", 50, type=int)
    scans = get_scan_history(user_id, limit=limit)
    for scan in scans:
        if scan.get("full_analysis"):
            try:
                scan["full_analysis"] = json.loads(scan["full_analysis"])
            except:
                pass
    return jsonify({"scans": scans})


@app.route("/api/energy/<int:user_id>")
def api_energy(user_id):
    return jsonify(get_energy_status(user_id))


@app.route("/api/leaderboard")
def api_leaderboard():
    return jsonify({"leaderboard": get_leaderboard(20)})


@app.route("/api/stats/<int:user_id>")
def api_stats(user_id):
    scans = get_scan_history(user_id, limit=200)
    if not scans:
        return jsonify({
            "total_scans": 0, "top_tokens": [],
            "trend_distribution": {}, "action_distribution": {}, "risk_distribution": {}
        })
    trends, actions, risks, tokens = {}, {}, {}, {}
    for scan in scans:
        trends[scan.get("trend", "?")] = trends.get(scan.get("trend", "?"), 0) + 1
        actions[scan.get("action", "?")] = actions.get(scan.get("action", "?"), 0) + 1
        risks[scan.get("risk_level", "?")] = risks.get(scan.get("risk_level", "?"), 0) + 1
        tk = scan.get("token", "Unknown")
        if tk and tk != "Unknown":
            tokens[tk] = tokens.get(tk, 0) + 1
    top_tokens = sorted(tokens.items(), key=lambda x: x[1], reverse=True)[:10]
    return jsonify({
        "total_scans": len(scans),
        "top_tokens": [{"token": t, "count": c} for t, c in top_tokens],
        "trend_distribution": trends, "action_distribution": actions,
        "risk_distribution": risks,
        "avg_confidence": sum(s.get("confidence", 0) or 0 for s in scans) / len(scans) if scans else 0
    })


# ═══════════════════════════════════════════
# TELEGRAM WEBHOOK ENDPOINT
# ═══════════════════════════════════════════

@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    """Receive Telegram updates via webhook."""
    _ensure_bot()

    if _bot_app is None or _bot_loop is None:
        logger.error("❌ Bot not ready after init!")
        return Response("Bot not ready", status=503)

    try:
        data = request.get_json(force=True)
        logger.info(f"📨 Webhook update: {data.get('update_id', '?')}")
        update = Update.de_json(data, _bot_app.bot)
        future = asyncio.run_coroutine_threadsafe(
            _bot_app.process_update(update), _bot_loop
        )
        future.result(timeout=60)
        return Response("ok", status=200)
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return Response("ok", status=200)


# ═══════════════════════════════════════════
# STARTUP — only init DB at module level
# ═══════════════════════════════════════════

logger.info("🔬 Dr. Inker Chart Scanner starting...")
init_db()

# Set webhook at startup (raw API, no bot app needed)
if TELEGRAM_BOT_TOKEN and WEBAPP_URL:
    try:
        import urllib.request as _urlreq
        webhook_url = f"{WEBAPP_URL}/webhook"

        _data = json.dumps({"drop_pending_updates": True}).encode("utf-8")
        _req = _urlreq.Request(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteWebhook",
            data=_data, headers={"Content-Type": "application/json"})
        _urlreq.urlopen(_req, timeout=10)

        _data = json.dumps({"url": webhook_url}).encode("utf-8")
        _req = _urlreq.Request(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook",
            data=_data, headers={"Content-Type": "application/json"})
        _resp = _urlreq.urlopen(_req, timeout=10)
        _result = json.loads(_resp.read().decode())
        logger.info(f"✅ Webhook set: {webhook_url} — {_result}")
    except Exception as e:
        logger.error(f"❌ Failed to set webhook: {e}")
# Bot app init happens lazily on first webhook request


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
