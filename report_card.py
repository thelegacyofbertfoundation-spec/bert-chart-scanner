"""
Dr. Inker LABS - Shareable Report Card Generator
Creates branded visual analysis cards for sharing on social media.
"""
import io
import os
import logging
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

logger = logging.getLogger(__name__)

# Logo path
LOGO_PATH = os.path.join(os.path.dirname(__file__), "static", "bert_logo.png")

# Card dimensions (optimized for Telegram/Twitter sharing)
CARD_WIDTH = 800
CARD_HEIGHT = 1000
PADDING = 32

# Colors
BG_COLOR = (10, 14, 23)         # #0a0e17
BG2_COLOR = (17, 24, 39)        # #111827
ACCENT = (0, 245, 160)          # #00F5A0
ACCENT2 = (0, 217, 245)         # #00D9F5
RED = (255, 71, 87)             # #FF4757
YELLOW = (255, 217, 61)         # #FFD93D
ORANGE = (255, 165, 2)          # #FFA502
WHITE = (232, 236, 241)         # #E8ECF1
GRAY = (136, 153, 170)          # #8899AA
DARK_GRAY = (30, 45, 61)        # #1e2d3d
CARD_BG = (20, 30, 45)          # card background


def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Get a font, falling back to default if not available."""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def get_trend_color(trend: str) -> tuple:
    """Get color for trend direction."""
    return {"Bullish": ACCENT, "Bearish": RED, "Sideways": YELLOW}.get(trend, GRAY)


def get_action_color(action: str) -> tuple:
    """Get color for action."""
    return {"BUY": (0, 255, 136), "SELL": RED, "HOLD": YELLOW, "WAIT": GRAY}.get(action, GRAY)


def get_risk_color(risk: str) -> tuple:
    """Get color for risk level."""
    return {"LOW": ACCENT, "MEDIUM": YELLOW, "HIGH": ORANGE, "EXTREME": RED}.get(risk, GRAY)


def draw_rounded_rect(draw: ImageDraw, xy, radius, fill):
    """Draw a rounded rectangle."""
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill)


def draw_gradient_line(draw: ImageDraw, y: int, x0: int, x1: int):
    """Draw a horizontal gradient accent line."""
    width = x1 - x0
    for i in range(width):
        ratio = i / width
        r = int(ACCENT[0] + (ACCENT2[0] - ACCENT[0]) * ratio)
        g = int(ACCENT[1] + (ACCENT2[1] - ACCENT[1]) * ratio)
        b = int(ACCENT[2] + (ACCENT2[2] - ACCENT[2]) * ratio)
        draw.line([(x0 + i, y), (x0 + i, y + 2)], fill=(r, g, b))


def generate_report_card(analysis: dict, dex_data: dict = None) -> bytes:
    """
    Generate a shareable report card image.

    Args:
        analysis: Gemini analysis result dict
        dex_data: Optional DexScreener enrichment data

    Returns:
        PNG image as bytes
    """
    # Dynamic height calculation
    has_dex = dex_data and dex_data.get("found")
    height = 920 if not has_dex else 1120

    img = Image.new("RGB", (CARD_WIDTH, height), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Fonts
    font_title = get_font(28, bold=True)
    font_large = get_font(22, bold=True)
    font_medium = get_font(16, bold=True)
    font_body = get_font(14)
    font_small = get_font(12)
    font_tiny = get_font(10)

    y = PADDING

    # ═══ HEADER ═══
    draw_rounded_rect(draw, (0, 0, CARD_WIDTH, 80), 0, fill=(15, 20, 30))
    draw_gradient_line(draw, 78, 0, CARD_WIDTH)

    # Bert logo in header
    try:
        if os.path.exists(LOGO_PATH):
            logo = Image.open(LOGO_PATH).convert("RGBA")
            # Resize logo to fit header (height ~60px)
            logo_h = 60
            logo_w = int(logo.width * (logo_h / logo.height))
            logo = logo.resize((logo_w, logo_h), Image.LANCZOS)
            # Paste with transparency
            img.paste(logo, (PADDING - 4, 10), logo)
            # Text after logo
            text_x = PADDING + logo_w + 8
        else:
            text_x = PADDING
            draw.text((PADDING, 18), "🔬", font=font_title, fill=WHITE)
            text_x = PADDING + 40
    except Exception as e:
        logger.error(f"Logo load failed: {e}")
        draw.text((PADDING, 18), "🔬", font=font_title, fill=WHITE)
        text_x = PADDING + 40

    draw.text((text_x, 12), "CHART SCANNER", font=font_title, fill=ACCENT)
    draw.text((text_x, 46), "Powered by Dr. Inker LABS", font=font_small, fill=GRAY)

    # Timestamp
    now = datetime.utcnow().strftime("%b %d, %Y %H:%M UTC")
    draw.text((CARD_WIDTH - PADDING - 180, 30), now, font=font_small, fill=GRAY)

    y = 100

    # ═══ TOKEN INFO ═══
    token = analysis.get("token", "Unknown")
    ticker = analysis.get("ticker", "???")
    draw.text((PADDING, y), f"{token}", font=font_title, fill=WHITE)
    draw.text((PADDING + draw.textlength(token, font=font_title) + 10, y + 6),
              f"({ticker})", font=font_medium, fill=GRAY)
    y += 40

    # Platform and timeframe
    platform = analysis.get("platform", "N/A")
    timeframe = analysis.get("timeframe", "N/A")
    price = analysis.get("current_price", "N/A")
    draw.text((PADDING, y), f"Platform: {platform}  •  Timeframe: {timeframe}  •  Price: {price}",
              font=font_body, fill=GRAY)
    y += 30

    draw_gradient_line(draw, y, PADDING, CARD_WIDTH - PADDING)
    y += 16

    # ═══ MAIN VERDICT CARDS ═══
    card_w = (CARD_WIDTH - PADDING * 2 - 20) // 3

    # Trend card
    trend = analysis.get("trend", "Unknown")
    trend_color = get_trend_color(trend)
    draw_rounded_rect(draw, (PADDING, y, PADDING + card_w, y + 90), 12, fill=CARD_BG)
    draw.text((PADDING + 16, y + 12), "TREND", font=font_tiny, fill=GRAY)
    draw.text((PADDING + 16, y + 30), trend, font=font_large, fill=trend_color)
    strength = analysis.get("trend_strength", "N/A")
    draw.text((PADDING + 16, y + 60), strength, font=font_small, fill=GRAY)

    # Action card
    action = analysis.get("action", "N/A")
    action_color = get_action_color(action)
    ax = PADDING + card_w + 10
    draw_rounded_rect(draw, (ax, y, ax + card_w, y + 90), 12, fill=CARD_BG)
    draw.text((ax + 16, y + 12), "ACTION", font=font_tiny, fill=GRAY)
    draw.text((ax + 16, y + 30), action, font=font_large, fill=action_color)

    # Risk card
    risk = analysis.get("risk_level", "N/A")
    risk_color = get_risk_color(risk)
    rx = ax + card_w + 10
    draw_rounded_rect(draw, (rx, y, rx + card_w, y + 90), 12, fill=CARD_BG)
    draw.text((rx + 16, y + 12), "RISK", font=font_tiny, fill=GRAY)
    draw.text((rx + 16, y + 30), risk, font=font_large, fill=risk_color)

    y += 108

    # ═══ CONFIDENCE BAR ═══
    draw.text((PADDING, y), "CONFIDENCE", font=font_tiny, fill=GRAY)
    conf = min(max(analysis.get("confidence", 5), 0), 10)
    bar_x = PADDING
    bar_y = y + 18
    bar_w = CARD_WIDTH - PADDING * 2
    bar_h = 12

    # Background
    draw_rounded_rect(draw, (bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), 6, fill=DARK_GRAY)
    # Fill
    fill_w = int(bar_w * conf / 10)
    if fill_w > 0:
        conf_color = ACCENT if conf >= 7 else YELLOW if conf >= 4 else RED
        draw_rounded_rect(draw, (bar_x, bar_y, bar_x + fill_w, bar_y + bar_h), 6, fill=conf_color)

    draw.text((bar_x + bar_w + 8 - 40, bar_y - 2), f"{conf}/10", font=font_medium, fill=WHITE)
    y += 46

    # ═══ KEY LEVELS ═══
    draw_gradient_line(draw, y, PADDING, CARD_WIDTH - PADDING)
    y += 12

    half_w = (CARD_WIDTH - PADDING * 2 - 16) // 2

    # Support levels
    draw_rounded_rect(draw, (PADDING, y, PADDING + half_w, y + 80), 12, fill=CARD_BG)
    draw.text((PADDING + 16, y + 10), "SUPPORT LEVELS", font=font_tiny, fill=ACCENT)
    supports = analysis.get("support_levels", [])
    for i, s in enumerate(supports[:3]):
        draw.text((PADDING + 16, y + 30 + i * 16), f"• {s}", font=font_body, fill=WHITE)

    # Resistance levels
    rx2 = PADDING + half_w + 16
    draw_rounded_rect(draw, (rx2, y, rx2 + half_w, y + 80), 12, fill=CARD_BG)
    draw.text((rx2 + 16, y + 10), "RESISTANCE LEVELS", font=font_tiny, fill=RED)
    resistances = analysis.get("resistance_levels", [])
    for i, r in enumerate(resistances[:3]):
        draw.text((rx2 + 16, y + 30 + i * 16), f"• {r}", font=font_body, fill=WHITE)

    y += 96

    # ═══ PATTERNS & VOLUME ═══
    draw_rounded_rect(draw, (PADDING, y, CARD_WIDTH - PADDING, y + 70), 12, fill=CARD_BG)
    patterns = analysis.get("chart_patterns", [])
    patterns_text = ", ".join(patterns) if patterns else "None detected"
    draw.text((PADDING + 16, y + 10), "PATTERNS", font=font_tiny, fill=ACCENT2)
    draw.text((PADDING + 16, y + 28), patterns_text[:60], font=font_body, fill=WHITE)
    vol = analysis.get("volume_trend", "N/A")
    draw.text((PADDING + 16, y + 48), f"Volume: {vol}", font=font_body, fill=GRAY)
    y += 86

    # ═══ VERDICT ═══
    draw_rounded_rect(draw, (PADDING, y, CARD_WIDTH - PADDING, y + 60), 12, fill=CARD_BG)
    verdict = analysis.get("verdict", "No verdict available")
    draw.text((PADDING + 16, y + 8), "VERDICT", font=font_tiny, fill=ACCENT)
    # Word wrap verdict
    words = verdict.split()
    lines = []
    current_line = ""
    for word in words:
        test = f"{current_line} {word}".strip()
        if draw.textlength(test, font=font_body) < (CARD_WIDTH - PADDING * 2 - 40):
            current_line = test
        else:
            lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)

    for i, line in enumerate(lines[:2]):
        draw.text((PADDING + 16, y + 26 + i * 16), line, font=font_body, fill=WHITE)
    y += 76

    # ═══ DEXSCREENER DATA (if available) ═══
    if has_dex:
        draw_gradient_line(draw, y, PADDING, CARD_WIDTH - PADDING)
        y += 12

        draw.text((PADDING, y), "📡 LIVE DATA (DexScreener)", font=font_medium, fill=ACCENT2)
        y += 26

        draw_rounded_rect(draw, (PADDING, y, CARD_WIDTH - PADDING, y + 150), 12, fill=CARD_BG)

        col1_x = PADDING + 16
        col2_x = CARD_WIDTH // 2 + 16

        def fmt_usd(val):
            try:
                val = float(val)
                if val >= 1e9: return f"${val/1e9:.2f}B"
                elif val >= 1e6: return f"${val/1e6:.2f}M"
                elif val >= 1e3: return f"${val/1e3:.1f}K"
                elif val >= 1: return f"${val:.2f}"
                else: return f"${val:.6f}"
            except: return "$0"

        def change_color(val):
            try:
                return ACCENT if float(val) >= 0 else RED
            except: return GRAY

        def fmt_change(val):
            try: return f"{float(val):+.1f}%"
            except: return "N/A"

        row_y = y + 12
        # Row 1: Price & MCap
        draw.text((col1_x, row_y), "Price", font=font_tiny, fill=GRAY)
        draw.text((col1_x, row_y + 14), fmt_usd(dex_data.get("price_usd", 0)), font=font_medium, fill=WHITE)
        draw.text((col2_x, row_y), "Market Cap", font=font_tiny, fill=GRAY)
        draw.text((col2_x, row_y + 14), fmt_usd(dex_data.get("market_cap", 0)), font=font_medium, fill=WHITE)

        row_y += 38
        # Row 2: Liquidity & Volume
        draw.text((col1_x, row_y), "Liquidity", font=font_tiny, fill=GRAY)
        draw.text((col1_x, row_y + 14), fmt_usd(dex_data.get("liquidity_usd", 0)), font=font_medium, fill=WHITE)
        draw.text((col2_x, row_y), "24h Volume", font=font_tiny, fill=GRAY)
        draw.text((col2_x, row_y + 14), fmt_usd(dex_data.get("volume_24h", 0)), font=font_medium, fill=WHITE)

        row_y += 38
        # Row 3: Price changes
        draw.text((col1_x, row_y), "1h", font=font_tiny, fill=GRAY)
        pc_1h = dex_data.get("price_change_1h", 0)
        draw.text((col1_x + 24, row_y), fmt_change(pc_1h), font=font_medium, fill=change_color(pc_1h))

        draw.text((col1_x + 120, row_y), "6h", font=font_tiny, fill=GRAY)
        pc_6h = dex_data.get("price_change_6h", 0)
        draw.text((col1_x + 144, row_y), fmt_change(pc_6h), font=font_medium, fill=change_color(pc_6h))

        draw.text((col2_x, row_y), "24h", font=font_tiny, fill=GRAY)
        pc_24h = dex_data.get("price_change_24h", 0)
        draw.text((col2_x + 30, row_y), fmt_change(pc_24h), font=font_medium, fill=change_color(pc_24h))

        # Buy/sell ratio
        draw.text((col2_x + 140, row_y), "Buys", font=font_tiny, fill=GRAY)
        draw.text((col2_x + 140, row_y + 14), f"{dex_data.get('buy_ratio', 50)}%",
                  font=font_medium, fill=ACCENT if dex_data.get("buy_ratio", 50) >= 50 else RED)

        row_y += 38
        # Chain info
        chain = dex_data.get("chain", "unknown").title()
        draw.text((col1_x, row_y), f"Chain: {chain}  •  DEX: {dex_data.get('dex', '').title()}",
                  font=font_small, fill=GRAY)

        y += 168

    # ═══ FOOTER ═══
    y = height - 56
    draw_gradient_line(draw, y, 0, CARD_WIDTH)

    # Bert logo in footer
    try:
        if os.path.exists(LOGO_PATH):
            logo_footer = Image.open(LOGO_PATH).convert("RGBA")
            fh = 36
            fw = int(logo_footer.width * (fh / logo_footer.height))
            logo_footer = logo_footer.resize((fw, fh), Image.LANCZOS)
            img.paste(logo_footer, (CARD_WIDTH - PADDING - fw, y + 10), logo_footer)
    except:
        pass

    draw.text((PADDING, y + 12), "Dr. Inker LABS", font=font_medium, fill=ACCENT)
    draw.text((PADDING, y + 34), "Not financial advice  •  Always DYOR", font=font_tiny, fill=GRAY)

    # Export
    buffer = io.BytesIO()
    img.save(buffer, format="PNG", quality=95)
    buffer.seek(0)
    return buffer.getvalue()
