"""
Dr. Inker LABS - Web Server + Telegram Bot (Webhook Mode)
Single process: Flask serves Mini App + receives Telegram updates via webhook.
"""
import os
import json
import asyncio
import logging
import threading
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

# Global bot application + event loop
_bot_app = None
_bot_loop = None


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
    """Receive Telegram updates via webhook — no polling needed."""
    global _bot_app, _bot_loop
    logger.info(f"📨 Webhook hit! bot_app={_bot_app is not None}, bot_loop={_bot_loop is not None}")
    if _bot_app is None or _bot_loop is None:
        logger.error("Bot not ready!")
        return Response("Bot not ready", status=503)
    try:
        data = request.get_json(force=True)
        logger.info(f"📨 Update received: {data.get('update_id', '?')}")
        update = Update.de_json(data, _bot_app.bot)
        future = asyncio.run_coroutine_threadsafe(
            _bot_app.process_update(update), _bot_loop
        )
        future.result(timeout=60)
        return Response("ok", status=200)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return Response("ok", status=200)


# ═══════════════════════════════════════════
# BOT INITIALIZATION (background thread)
# ═══════════════════════════════════════════

def _build_application():
    """Create the Telegram Application with all handlers."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("scan", scan_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("refer", refer_command))
    application.add_handler(CommandHandler("premium", premium_command))
    application.add_handler(CommandHandler("leaderboard", leaderboard_command))

    # Photos
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.Document.IMAGE, handle_document_image))

    # Text
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Callbacks
    application.add_handler(CallbackQueryHandler(callback_handler))

    # Payments
    application.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))

    return application


def _run_bot():
    """Run the bot's async loop in a background thread."""
    global _bot_app, _bot_loop

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    _bot_loop = loop

    async def _start():
        global _bot_app
        _bot_app = _build_application()
        await _bot_app.initialize()
        await _bot_app.start()

        # Set webhook using raw API call (more reliable)
        import urllib.request
        import json as _json
        webhook_url = f"{WEBAPP_URL}/webhook"
        
        # First delete any existing webhook
        req_data = _json.dumps({"drop_pending_updates": True}).encode("utf-8")
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteWebhook",
            data=req_data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
        
        # Now set the new webhook
        req_data = _json.dumps({"url": webhook_url}).encode("utf-8")
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook",
            data=req_data, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=10)
        result = _json.loads(resp.read().decode())
        logger.info(f"✅ Webhook set: {webhook_url} — {result}")
        logger.info(f"🔬 BERT Chart Scanner is live!")

        # Keep the loop alive
        while True:
            await asyncio.sleep(3600)

    loop.run_until_complete(_start())


# ═══════════════════════════════════════════
# STARTUP
# ═══════════════════════════════════════════

logger.info("🔬 Dr. Inker Chart Scanner starting...")
init_db()

if TELEGRAM_BOT_TOKEN:
    bot_thread = threading.Thread(target=_run_bot, daemon=True)
    bot_thread.start()
    logger.info("🤖 Bot thread started (webhook mode)")
else:
    logger.warning("⚠️ No TELEGRAM_BOT_TOKEN — bot not started")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
