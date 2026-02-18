"""
Dr. Inker LABS - BERT Chart Scanner
All Telegram bot handlers. No polling — webhook mode via web_server.py
"""
import logging
import io
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    LabeledPrice, WebAppInfo
)
from telegram.ext import ContextTypes
from config import (
    WEBAPP_URL, BOT_NAME, BRAND,
    FREE_DAILY_SCANS, ENERGY_REFILL_STARS, PREMIUM_STARS_MONTHLY,
    REFERRAL_BONUS_SCANS
)
from database import (
    get_or_create_user, get_energy_status, use_scan,
    add_bonus_scans, set_premium, save_scan, get_scan_history,
    process_referral, get_referral_count, get_leaderboard
)
from gemini_analyzer import analyze_chart, format_analysis_text, format_detailed_analysis
from dexscreener import enrich_analysis, format_enrichment_text
from report_card import generate_report_card

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════
# COMMAND HANDLERS
# ═══════════════════════════════════════════

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = get_or_create_user(user.id, user.username, user.first_name)

    if context.args:
        ref_code = context.args[0]
        if process_referral(ref_code, user.id):
            await update.message.reply_text(
                "🎁 Referral bonus! You got <b>3 free scans</b>!", parse_mode="HTML"
            )

    energy = get_energy_status(user.id)

    keyboard = [
        [InlineKeyboardButton("📊 How to Scan", callback_data="help_scan")],
        [
            InlineKeyboardButton("⚡ My Energy", callback_data="energy"),
            InlineKeyboardButton("📈 History", web_app=WebAppInfo(url=f"{WEBAPP_URL}/app?user_id={user.id}"))
        ],
        [
            InlineKeyboardButton("🔗 Refer Friends", callback_data="referral"),
            InlineKeyboardButton("👑 Go Premium", callback_data="premium")
        ],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard")],
    ]

    await update.message.reply_text(
        f"""
🔬 <b>Welcome to {BOT_NAME}!</b>

📸 Send me any chart screenshot and I'll instantly analyze it using AI:

✅ Trend direction & strength
✅ Support & resistance levels
✅ Chart patterns detected
✅ Risk assessment
✅ Buy/Sell/Hold verdict

⚡ You have <b>{energy['total_remaining']}</b> scans remaining today.

Just send a screenshot to get started! 👇
""",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"""
🔬 <b>{BOT_NAME} - Help</b>

<b>How to use:</b>
1️⃣ Take a screenshot of any chart (DexScreener, TradingView, Birdeye, etc.)
2️⃣ Send it to this bot
3️⃣ Get instant AI-powered technical analysis!

<b>Commands:</b>
/start - Main menu
/scan - Check your scan energy
/history - View past scans
/refer - Get your referral link
/premium - Upgrade to unlimited scans
/leaderboard - Top scanners

<b>Tips for best results:</b>
• Use clear, full-screen chart screenshots
• Include candlestick charts (not just line charts)
• Make sure price levels and volume are visible
• Higher timeframes give better pattern detection

⚡ Free users get <b>{FREE_DAILY_SCANS} scans/day</b>
👑 Premium gets <b>unlimited scans</b>

<i>Powered by {BRAND}</i>
""",
        parse_mode="HTML"
    )


async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_or_create_user(user.id, user.username, user.first_name)
    energy = get_energy_status(user.id)

    if energy["is_premium"]:
        status = "👑 <b>PREMIUM</b> - Unlimited scans!"
    else:
        bar_free = "🟢" * energy["free_remaining"] + "⚫" * (FREE_DAILY_SCANS - energy["free_remaining"])
        status = f"""
⚡ Daily Scans: {bar_free} ({energy['free_remaining']}/{FREE_DAILY_SCANS})
🎁 Bonus Scans: {energy['bonus_scans']}
📊 Total Available: <b>{energy['total_remaining']}</b>
"""

    keyboard = [
        [InlineKeyboardButton(f"⚡ Buy {ENERGY_REFILL_STARS} Scans ({ENERGY_REFILL_STARS} ⭐)", callback_data="buy_scans")],
        [InlineKeyboardButton("👑 Go Premium (Unlimited)", callback_data="premium")],
        [InlineKeyboardButton("🔗 Refer for Free Scans", callback_data="referral")],
    ]

    await update.message.reply_text(
        f"""
🔬 <b>Scan Energy Status</b>
━━━━━━━━━━━━━━━━
{status}
📈 Total scans ever: {energy['total_scans_ever']}
━━━━━━━━━━━━━━━━
""",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_or_create_user(user.id, user.username, user.first_name)
    scans = get_scan_history(user.id, limit=5)

    if not scans:
        await update.message.reply_text("📭 No scans yet! Send me a chart screenshot to get started.")
        return

    msg = "📜 <b>Recent Scans</b>\n━━━━━━━━━━━━━━━━\n\n"
    for i, scan in enumerate(scans, 1):
        trend_emoji = {"Bullish": "🟢", "Bearish": "🔴", "Sideways": "🟡"}.get(scan["trend"], "⚪")
        action_emoji = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡", "WAIT": "⏳"}.get(scan["action"], "⚪")
        msg += f"{i}. {trend_emoji} <b>{scan['token'] or 'Unknown'}</b> ({scan['ticker'] or '?'})\n"
        msg += f"   {action_emoji} {scan['action']} | Risk: {scan['risk_level']} | Conf: {scan['confidence']}/10\n"
        msg += f"   📅 {scan['created_at'][:16]}\n\n"

    keyboard = [[
        InlineKeyboardButton(
            "📊 Full History (Dashboard)",
            web_app=WebAppInfo(url=f"{WEBAPP_URL}/app?user_id={user.id}")
        )
    ]]

    await update.message.reply_text(
        msg + "<i>Open the dashboard for full history & analytics</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def refer_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = get_or_create_user(user.id, user.username, user.first_name)
    ref_count = get_referral_count(user.id)

    bot_info = await context.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={db_user['referral_code']}"

    await update.message.reply_text(
        f"""
🔗 <b>Your Referral Link</b>
━━━━━━━━━━━━━━━━

Share this link with friends:
<code>{ref_link}</code>

✅ You get <b>{REFERRAL_BONUS_SCANS} free scans</b> per referral
✅ They get <b>3 bonus scans</b> to start

👥 Friends referred: <b>{ref_count}</b>
🎁 Total bonus earned: <b>{ref_count * REFERRAL_BONUS_SCANS} scans</b>
━━━━━━━━━━━━━━━━
""",
        parse_mode="HTML"
    )


async def premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        InlineKeyboardButton(
            f"👑 Subscribe ({PREMIUM_STARS_MONTHLY} ⭐/month)",
            callback_data="pay_premium"
        )
    ]]
    await update.message.reply_text(
        f"👑 <b>Premium Plan</b>\n\n"
        f"✅ <b>Unlimited</b> chart scans\n"
        f"✅ Detailed analysis on every scan\n"
        f"✅ Priority AI processing\n"
        f"✅ Full scan history & analytics\n"
        f"✅ Shareable report cards\n\n"
        f"💰 Only <b>{PREMIUM_STARS_MONTHLY} Telegram Stars/month</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    leaders = get_leaderboard(10)
    if not leaders:
        await update.message.reply_text("🏆 No scans yet! Be the first!")
        return
    msg = "🏆 <b>Top Chart Scanners</b>\n━━━━━━━━━━━━━━━━\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, user in enumerate(leaders):
        medal = medals[i] if i < 3 else f"{i+1}."
        name = user["first_name"] or user["username"] or "Anonymous"
        msg += f"{medal} <b>{name}</b> — {user['total_scans']} scans\n"
    await update.message.reply_text(
        msg + f"\n<i>Scan more charts to climb the ranks!</i>\n🔬 <i>{BRAND}</i>",
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════
# IMAGE HANDLER (Core Feature)
# ═══════════════════════════════════════════

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_or_create_user(user.id, user.username, user.first_name)

    energy = get_energy_status(user.id)
    if energy["total_remaining"] <= 0:
        keyboard = [
            [InlineKeyboardButton(f"⚡ Buy {ENERGY_REFILL_STARS} Scans ({ENERGY_REFILL_STARS} ⭐)", callback_data="buy_scans")],
            [InlineKeyboardButton("👑 Go Premium", callback_data="premium")],
            [InlineKeyboardButton("🔗 Refer for Free Scans", callback_data="referral")],
        ]
        await update.message.reply_text(
            "⚡ <b>Out of scans!</b>\n\nRefill your energy to keep scanning charts.",
            parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    analyzing_msg = await update.message.reply_text(
        "🔬 <b>Analyzing your chart...</b>\n\n"
        "🧠 AI is reading the chart...\n"
        "📊 Detecting patterns...\n"
        "⏳ This usually takes 5-10 seconds...",
        parse_mode="HTML"
    )

    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        image_data = await file.download_as_bytearray()

        analysis = analyze_chart(bytes(image_data), "image/jpeg")

        if analysis.get("success"):
            use_scan(user.id)

            await analyzing_msg.edit_text(
                "🔬 <b>Analyzing your chart...</b>\n\n"
                "✅ AI analysis complete!\n"
                "📡 Fetching live data from DexScreener...\n"
                "🎨 Generating report card...",
                parse_mode="HTML"
            )

            dex_data = await enrich_analysis(analysis)
            save_scan(user.id, analysis, photo.file_id)
            new_energy = get_energy_status(user.id)
            main_text = format_analysis_text(analysis)

            await analyzing_msg.delete()

            keyboard = [
                [InlineKeyboardButton("📝 Detailed Analysis", callback_data=f"detail_{user.id}")],
                [
                    InlineKeyboardButton("📤 Share Report Card", callback_data=f"sharecard_{user.id}"),
                    InlineKeyboardButton(f"⚡ {new_energy['total_remaining']} left", callback_data="energy")
                ],
            ]

            await update.message.reply_text(
                main_text, parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

            if dex_data:
                dex_text = format_enrichment_text(dex_data)
                if dex_text:
                    await update.message.reply_text(dex_text, parse_mode="HTML", disable_web_page_preview=True)

            try:
                card_bytes = generate_report_card(analysis, dex_data)
                await update.message.reply_photo(
                    photo=io.BytesIO(card_bytes),
                    caption=f"🔬 <b>BERT Chart Scan</b> — {analysis.get('token', 'Unknown')} ({analysis.get('ticker', '?')})\n"
                            f"{analysis.get('verdict', '')}\n\n"
                            f"📤 Share this with your community!\n"
                            f"🔗 Scan your own charts: @BertCS_bot",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Report card generation failed: {e}")

            context.user_data["last_analysis"] = analysis
            context.user_data["last_dex_data"] = dex_data

        else:
            await analyzing_msg.edit_text(
                f"❌ <b>Analysis Failed</b>\n\n{analysis.get('error', 'Unknown error')}\n\n"
                "💡 <b>Tips:</b>\n"
                "• Use a clear, full-screen screenshot\n"
                "• Make sure the chart has candlesticks visible\n"
                "• Try a different angle or zoom level\n\n"
                "Your scan energy was <b>not consumed</b>.",
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"Error analyzing chart: {e}")
        await analyzing_msg.edit_text(
            "❌ <b>Something went wrong!</b>\n\n"
            "Please try again. If the issue persists, the AI service may be temporarily unavailable.\n\n"
            "Your scan energy was <b>not consumed</b>.",
            parse_mode="HTML"
        )


async def handle_document_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not (doc and doc.mime_type and doc.mime_type.startswith("image/")):
        return

    user = update.effective_user
    get_or_create_user(user.id, user.username, user.first_name)

    energy = get_energy_status(user.id)
    if energy["total_remaining"] <= 0:
        keyboard = [
            [InlineKeyboardButton("⚡ Buy Scans", callback_data="buy_scans")],
            [InlineKeyboardButton("👑 Go Premium", callback_data="premium")],
        ]
        await update.message.reply_text("⚡ <b>Out of scans!</b>", parse_mode="HTML",
                                         reply_markup=InlineKeyboardMarkup(keyboard))
        return

    analyzing_msg = await update.message.reply_text(
        "🔬 <b>Analyzing your chart...</b>\n⏳ Please wait...", parse_mode="HTML"
    )

    try:
        file = await context.bot.get_file(doc.file_id)
        image_data = await file.download_as_bytearray()
        analysis = analyze_chart(bytes(image_data), doc.mime_type)

        if analysis.get("success"):
            use_scan(user.id)
            save_scan(user.id, analysis, doc.file_id)
            dex_data = await enrich_analysis(analysis)
            new_energy = get_energy_status(user.id)
            main_text = format_analysis_text(analysis)

            keyboard = [
                [InlineKeyboardButton("📝 Detailed Analysis", callback_data=f"detail_{user.id}")],
                [
                    InlineKeyboardButton("📤 Share Report Card", callback_data=f"sharecard_{user.id}"),
                    InlineKeyboardButton(f"⚡ {new_energy['total_remaining']} left", callback_data="energy")
                ],
            ]

            await analyzing_msg.delete()
            await update.message.reply_text(main_text, parse_mode="HTML",
                                             reply_markup=InlineKeyboardMarkup(keyboard))

            if dex_data:
                dex_text = format_enrichment_text(dex_data)
                if dex_text:
                    await update.message.reply_text(dex_text, parse_mode="HTML", disable_web_page_preview=True)

            try:
                card_bytes = generate_report_card(analysis, dex_data)
                await update.message.reply_photo(
                    photo=io.BytesIO(card_bytes),
                    caption=f"🔬 <b>BERT Chart Scan</b> — {analysis.get('token', 'Unknown')}\n"
                            f"📤 Share this with your community!\n🔗 @BertCS_bot",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Report card failed: {e}")

            context.user_data["last_analysis"] = analysis
            context.user_data["last_dex_data"] = dex_data
        else:
            await analyzing_msg.edit_text(
                f"❌ {analysis.get('error', 'Analysis failed.')}", parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"Error: {e}")
        await analyzing_msg.edit_text("❌ Something went wrong. Try again.", parse_mode="HTML")


# ═══════════════════════════════════════════
# CALLBACK HANDLERS
# ═══════════════════════════════════════════

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user

    if data == "help_scan":
        await query.message.reply_text(
            "📸 <b>Just send me a chart screenshot!</b>\n\n"
            "I support charts from:\n"
            "• DexScreener\n• TradingView\n• Birdeye\n• CoinGecko\n• Any other charting platform\n\n"
            "📱 Screenshot → Send → Get Analysis!",
            parse_mode="HTML"
        )

    elif data == "energy":
        energy = get_energy_status(user.id)
        if energy["is_premium"]:
            await query.message.reply_text("👑 Premium — Unlimited scans!")
        else:
            await query.message.reply_text(
                f"⚡ <b>Energy Status</b>\n\n"
                f"Daily: {energy['free_remaining']}/{FREE_DAILY_SCANS}\n"
                f"Bonus: {energy['bonus_scans']}\n"
                f"Total: <b>{energy['total_remaining']}</b>",
                parse_mode="HTML"
            )

    elif data.startswith("detail_"):
        analysis = context.user_data.get("last_analysis")
        if analysis:
            detail_text = format_detailed_analysis(analysis)
            await query.message.reply_text(detail_text, parse_mode="HTML")
        else:
            await query.message.reply_text("❌ No recent analysis found. Send a new screenshot!")

    elif data.startswith("sharecard_"):
        analysis = context.user_data.get("last_analysis")
        dex_data = context.user_data.get("last_dex_data")
        if analysis:
            try:
                card_bytes = generate_report_card(analysis, dex_data)
                await query.message.reply_photo(
                    photo=io.BytesIO(card_bytes),
                    caption=f"🔬 <b>BERT Chart Scan</b> — {analysis.get('token', 'Unknown')}\n"
                            f"📤 Forward this to share!\n🔗 @BertCS_bot",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Share card failed: {e}")
                await query.message.reply_text("❌ Failed to generate report card. Try a new scan!")
        else:
            await query.message.reply_text("❌ No recent analysis found. Send a new screenshot!")

    elif data == "referral":
        db_user = get_or_create_user(user.id, user.username, user.first_name)
        ref_count = get_referral_count(user.id)
        bot_info = await context.bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={db_user['referral_code']}"
        await query.message.reply_text(
            f"🔗 <b>Your Referral Link</b>\n\n<code>{ref_link}</code>\n\n"
            f"✅ {REFERRAL_BONUS_SCANS} free scans per referral\n👥 Referred: {ref_count}",
            parse_mode="HTML"
        )

    elif data == "premium":
        keyboard = [[InlineKeyboardButton(
            f"👑 Subscribe ({PREMIUM_STARS_MONTHLY} ⭐/month)", callback_data="pay_premium"
        )]]
        await query.message.reply_text(
            f"👑 <b>Premium Plan</b>\n\n"
            f"✅ <b>Unlimited</b> chart scans\n✅ Detailed analysis\n"
            f"✅ Priority AI processing\n✅ Full history & analytics\n\n"
            f"💰 Only <b>{PREMIUM_STARS_MONTHLY} Telegram Stars/month</b>",
            parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "buy_scans":
        keyboard = [[InlineKeyboardButton(
            f"⚡ Buy {ENERGY_REFILL_STARS} Scans ({ENERGY_REFILL_STARS} ⭐)", callback_data="pay_scans"
        )]]
        await query.message.reply_text(
            f"⚡ <b>Refill Scans</b>\n\nGet <b>{ENERGY_REFILL_STARS} extra scans</b> "
            f"for {ENERGY_REFILL_STARS} Telegram Stars.\nThese bonus scans don't expire!",
            parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "pay_premium":
        await context.bot.send_invoice(
            chat_id=query.message.chat_id,
            title="👑 Premium Plan - 1 Month",
            description="Unlimited chart scans, detailed analysis, priority processing, and more!",
            payload=f"premium_{user.id}",
            currency="XTR",
            prices=[LabeledPrice(label="Premium (1 Month)", amount=PREMIUM_STARS_MONTHLY)],
        )

    elif data == "pay_scans":
        await context.bot.send_invoice(
            chat_id=query.message.chat_id,
            title=f"⚡ {ENERGY_REFILL_STARS} Scan Refill",
            description=f"{ENERGY_REFILL_STARS} bonus chart scans. Never expire!",
            payload=f"scans_{user.id}_{ENERGY_REFILL_STARS}",
            currency="XTR",
            prices=[LabeledPrice(label=f"{ENERGY_REFILL_STARS} Scans", amount=ENERGY_REFILL_STARS)],
        )

    elif data == "leaderboard":
        leaders = get_leaderboard(10)
        if not leaders:
            await query.message.reply_text("🏆 No scans yet!")
            return
        msg = "🏆 <b>Top Scanners</b>\n\n"
        medals = ["🥇", "🥈", "🥉"]
        for i, u in enumerate(leaders):
            medal = medals[i] if i < 3 else f"{i+1}."
            name = u["first_name"] or u["username"] or "Anon"
            msg += f"{medal} {name} — {u['total_scans']} scans\n"
        await query.message.reply_text(msg, parse_mode="HTML")


# ═══════════════════════════════════════════
# PAYMENT HANDLERS
# ═══════════════════════════════════════════

async def pre_checkout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)


async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment = update.message.successful_payment
    user = update.effective_user
    payload = payment.invoice_payload

    if payload.startswith("premium_"):
        set_premium(user.id, months=1, stars_paid=payment.total_amount)
        await update.message.reply_text(
            "👑 <b>Welcome to Premium!</b>\n\nYou now have <b>unlimited chart scans</b> for 30 days!\n"
            "Send me a screenshot to get started! 📸",
            parse_mode="HTML"
        )
    elif payload.startswith("scans_"):
        parts = payload.split("_")
        amount = int(parts[2]) if len(parts) > 2 else ENERGY_REFILL_STARS
        add_bonus_scans(user.id, amount, stars_paid=payment.total_amount)
        energy = get_energy_status(user.id)
        await update.message.reply_text(
            f"⚡ <b>Scans Refilled!</b>\n\n+{amount} bonus scans added.\n"
            f"Total available: <b>{energy['total_remaining']}</b>\n\nSend me a chart! 📸",
            parse_mode="HTML"
        )


# ═══════════════════════════════════════════
# TEXT HANDLER
# ═══════════════════════════════════════════

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📸 <b>Send me a chart screenshot!</b>\n\n"
        "I analyze images, not text. Take a screenshot of any chart "
        "(DexScreener, TradingView, Birdeye, etc.) and send it here.\n\n"
        "Type /help for more info.",
        parse_mode="HTML"
    )
