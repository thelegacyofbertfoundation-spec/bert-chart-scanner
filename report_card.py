"""
Dr. Inker LABS - Premium Report Card Generator
Creates high-quality branded visual analysis cards for social sharing.
"""
import io
import os
import logging
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

logger = logging.getLogger(__name__)

LOGO_PATH = os.path.join(os.path.dirname(__file__), "static", "bert_logo.png")

CARD_WIDTH = 800
PADDING = 30

# Colors
BG_TOP = (8, 12, 21)
BG_BOT = (12, 18, 32)
ACCENT = (0, 245, 160)
ACCENT2 = (0, 217, 245)
RED = (255, 71, 87)
GREEN = (0, 230, 118)
YELLOW = (255, 215, 0)
ORANGE = (255, 152, 0)
WHITE = (240, 242, 245)
LIGHT_GRAY = (180, 190, 200)
GRAY = (100, 115, 130)
DARK_CARD = (16, 24, 40)
CARD_BORDER = (30, 45, 65)


def get_font(size, bold=False):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def color_for(category, value):
    maps = {
        "trend": {"Bullish": GREEN, "Bearish": RED, "Sideways": YELLOW},
        "action": {"BUY": GREEN, "SELL": RED, "HOLD": YELLOW, "WAIT": LIGHT_GRAY},
        "risk": {"LOW": GREEN, "MEDIUM": YELLOW, "HIGH": ORANGE, "EXTREME": RED},
    }
    return maps.get(category, {}).get(value, GRAY)


def draw_gradient_bg(img):
    draw = ImageDraw.Draw(img)
    for y_pos in range(img.height):
        ratio = y_pos / img.height
        r = int(BG_TOP[0] + (BG_BOT[0] - BG_TOP[0]) * ratio)
        g = int(BG_TOP[1] + (BG_BOT[1] - BG_TOP[1]) * ratio)
        b = int(BG_TOP[2] + (BG_BOT[2] - BG_TOP[2]) * ratio)
        draw.line([(0, y_pos), (CARD_WIDTH, y_pos)], fill=(r, g, b))


def draw_accent_line(draw, y, x0, x1, thickness=2):
    w = x1 - x0
    for i in range(w):
        ratio = i / w
        r = int(ACCENT[0] + (ACCENT2[0] - ACCENT[0]) * ratio)
        g = int(ACCENT[1] + (ACCENT2[1] - ACCENT[1]) * ratio)
        b = int(ACCENT[2] + (ACCENT2[2] - ACCENT[2]) * ratio)
        for t in range(thickness):
            draw.point((x0 + i, y + t), fill=(r, g, b))


def rr(draw, xy, radius, fill, outline=None):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline)


def generate_report_card(analysis: dict, dex_data: dict = None) -> bytes:
    has_dex = dex_data and dex_data.get("found")
    height = 680 if not has_dex else 870

    img = Image.new("RGB", (CARD_WIDTH, height), BG_TOP)
    draw_gradient_bg(img)
    draw = ImageDraw.Draw(img)

    f32b = get_font(32, True)
    f24b = get_font(24, True)
    f18b = get_font(18, True)
    f15b = get_font(15, True)
    f13 = get_font(13)
    f13b = get_font(13, True)
    f11 = get_font(11)
    f10 = get_font(10)

    y = 0

    # ══ HEADER ══
    hh = 60
    rr(draw, (0, 0, CARD_WIDTH, hh), 0, fill=(12, 16, 28))
    draw_accent_line(draw, hh - 2, 0, CARD_WIDTH, 2)

    lx = PADDING
    try:
        if os.path.exists(LOGO_PATH):
            logo = Image.open(LOGO_PATH).convert("RGBA")
            lh = 48
            lw = int(logo.width * (lh / logo.height))
            logo = logo.resize((lw, lh), Image.LANCZOS)
            img.paste(logo, (PADDING, 6), logo)
            lx = PADDING + lw + 10
    except:
        pass

    draw.text((lx, 10), "CHART SCANNER", font=f24b, fill=ACCENT)
    draw.text((lx, 36), "Dr. Inker LABS", font=f10, fill=GRAY)
    ts = datetime.utcnow().strftime("%b %d, %Y  %H:%M UTC")
    draw.text((CARD_WIDTH - PADDING - draw.textlength(ts, f11), 24), ts, font=f11, fill=GRAY)

    y = hh + 16

    # ══ TOKEN + PRICE ══
    token = analysis.get("token", "Unknown")
    ticker = analysis.get("ticker", "???")
    price = analysis.get("current_price", "")

    draw.text((PADDING, y), token, font=f32b, fill=WHITE)
    tx = PADDING + draw.textlength(token, f32b) + 10
    draw.text((tx, y + 8), f"${ticker}", font=f18b, fill=GRAY)

    if price and price not in ("N/A", "null", "None"):
        pw = draw.textlength(price, f24b)
        draw.text((CARD_WIDTH - PADDING - pw, y + 4), price, font=f24b, fill=WHITE)
    y += 44

    meta = []
    if analysis.get("platform") and analysis["platform"] not in ("N/A", "null"):
        meta.append(analysis["platform"])
    if analysis.get("timeframe") and analysis["timeframe"] not in ("N/A", "null"):
        meta.append(analysis["timeframe"])
    draw.text((PADDING, y), "  •  ".join(meta), font=f13, fill=GRAY)
    y += 24

    # ══ TREND / ACTION / RISK BADGES ══
    draw_accent_line(draw, y, PADDING, CARD_WIDTH - PADDING, 1)
    y += 12

    bw = (CARD_WIDTH - PADDING * 2 - 20) // 3
    badges = [
        ("trend", analysis.get("trend", "?"), analysis.get("trend_strength", "")),
        ("action", analysis.get("action", "?"), "Signal"),
        ("risk", analysis.get("risk_level", "?"), "Risk Level"),
    ]

    for i, (cat, val, sub) in enumerate(badges):
        bx = PADDING + i * (bw + 10)
        c = color_for(cat, val)
        rr(draw, (bx, y, bx + bw, y + 64), 10, fill=DARK_CARD, outline=CARD_BORDER)
        # Colored left accent bar
        rr(draw, (bx, y, bx + 4, y + 64), 2, fill=c)
        draw.text((bx + 14, y + 10), val.upper(), font=f18b, fill=c)
        draw.text((bx + 14, y + 38), sub, font=f11, fill=GRAY)
    y += 80

    # ══ CONFIDENCE ══
    conf = min(max(analysis.get("confidence", 5), 0), 10)
    cc = GREEN if conf >= 7 else YELLOW if conf >= 4 else RED

    draw.text((PADDING, y), "Confidence", font=f15b, fill=LIGHT_GRAY)
    ct = f"{conf}/10"
    draw.text((CARD_WIDTH - PADDING - draw.textlength(ct, f15b), y), ct, font=f15b, fill=cc)
    y += 22

    bw2 = CARD_WIDTH - PADDING * 2
    rr(draw, (PADDING, y, PADDING + bw2, y + 8), 4, fill=(25, 35, 50))
    fw = max(4, int(bw2 * conf / 10))
    rr(draw, (PADDING, y, PADDING + fw, y + 8), 4, fill=cc)
    y += 20

    # ══ KEY LEVELS + PATTERNS (two columns) ══
    draw_accent_line(draw, y, PADDING, CARD_WIDTH - PADDING, 1)
    y += 10

    half = (CARD_WIDTH - PADDING * 2 - 16) // 2
    rx2 = PADDING + half + 16

    # Left column
    draw.text((PADDING, y), "SUPPORT", font=f10, fill=GREEN)
    sups = analysis.get("support_levels", [])
    draw.text((PADDING, y + 14), " / ".join(str(s) for s in sups[:3]) if sups else "—", font=f13, fill=WHITE)

    draw.text((PADDING, y + 34), "RESISTANCE", font=f10, fill=RED)
    ress = analysis.get("resistance_levels", [])
    draw.text((PADDING, y + 48), " / ".join(str(r) for r in ress[:3]) if ress else "—", font=f13, fill=WHITE)

    # Right column
    draw.text((rx2, y), "PATTERNS", font=f10, fill=ACCENT2)
    pats = analysis.get("chart_patterns", [])
    draw.text((rx2, y + 14), ", ".join(pats[:3])[:40] if pats else "None", font=f13, fill=WHITE)

    draw.text((rx2, y + 34), "VOLUME", font=f10, fill=ACCENT2)
    draw.text((rx2, y + 48), analysis.get("volume_trend", "N/A"), font=f13, fill=WHITE)
    y += 72

    # ══ VERDICT ══
    verdict = analysis.get("verdict", "No verdict available")
    rr(draw, (PADDING, y, CARD_WIDTH - PADDING, y + 50), 8, fill=DARK_CARD, outline=CARD_BORDER)

    max_w = CARD_WIDTH - PADDING * 2 - 24
    words = verdict.split()
    lines, line = [], ""
    for w in words:
        test = f"{line} {w}".strip()
        if draw.textlength(test, f13) < max_w:
            line = test
        else:
            lines.append(line)
            line = w
    if line:
        lines.append(line)

    vy = y + 8
    for l in lines[:2]:
        draw.text((PADDING + 12, vy), l, font=f13, fill=LIGHT_GRAY)
        vy += 17
    y += 62

    # ══ DEXSCREENER DATA ══
    if has_dex:
        draw_accent_line(draw, y, PADDING, CARD_WIDTH - PADDING, 1)
        y += 10
        draw.text((PADDING, y), "LIVE MARKET DATA", font=f15b, fill=ACCENT2)
        y += 22

        rr(draw, (PADDING, y, CARD_WIDTH - PADDING, y + 130), 10, fill=DARK_CARD, outline=CARD_BORDER)

        cx = PADDING + 16
        cx2 = CARD_WIDTH // 2 + 8

        def fmt(val):
            try:
                v = float(val)
                if v >= 1e9: return f"${v/1e9:.2f}B"
                elif v >= 1e6: return f"${v/1e6:.2f}M"
                elif v >= 1e3: return f"${v/1e3:.1f}K"
                elif v >= 1: return f"${v:.2f}"
                else: return f"${v:.6f}"
            except:
                return "$0"

        def pct(val):
            try:
                v = float(val)
                return f"{v:+.1f}%", GREEN if v >= 0 else RED
            except:
                return "N/A", GRAY

        ry = y + 12

        draw.text((cx, ry), "Price", font=f10, fill=GRAY)
        draw.text((cx, ry + 13), fmt(dex_data.get("price_usd", 0)), font=f18b, fill=WHITE)
        draw.text((cx2, ry), "Market Cap", font=f10, fill=GRAY)
        draw.text((cx2, ry + 13), fmt(dex_data.get("market_cap", 0)), font=f18b, fill=WHITE)
        ry += 38

        draw.text((cx, ry), "Liquidity", font=f10, fill=GRAY)
        draw.text((cx, ry + 13), fmt(dex_data.get("liquidity_usd", 0)), font=f18b, fill=WHITE)
        draw.text((cx2, ry), "24h Volume", font=f10, fill=GRAY)
        draw.text((cx2, ry + 13), fmt(dex_data.get("volume_24h", 0)), font=f18b, fill=WHITE)
        ry += 38

        pcx = cx
        for label, val in [("1h", dex_data.get("price_change_1h", 0)),
                           ("6h", dex_data.get("price_change_6h", 0)),
                           ("24h", dex_data.get("price_change_24h", 0))]:
            draw.text((pcx, ry), label, font=f10, fill=GRAY)
            txt, clr = pct(val)
            draw.text((pcx + 26, ry), txt, font=f15b, fill=clr)
            pcx += 120

        br = dex_data.get("buy_ratio", 50)
        brc = GREEN if br >= 50 else RED
        draw.text((cx2 + 160, ry), "Buys", font=f10, fill=GRAY)
        draw.text((cx2 + 160, ry + 13), f"{br}%", font=f15b, fill=brc)

        ry += 28
        chain = dex_data.get("chain", "").title()
        dex_name = dex_data.get("dex", "").title()
        draw.text((cx, ry), f"{chain}  •  {dex_name}", font=f11, fill=GRAY)

        y += 145

    # ══ FOOTER ══
    fy = height - 40
    draw_accent_line(draw, fy, 0, CARD_WIDTH, 2)

    draw.text((PADDING, fy + 10), "Dr. Inker LABS", font=f15b, fill=ACCENT)
    draw.text((PADDING + 130, fy + 12), "•  Not financial advice  •  DYOR", font=f10, fill=GRAY)

    handle = "@BertCS_bot"
    hw = draw.textlength(handle, f15b)

    try:
        if os.path.exists(LOGO_PATH):
            logo = Image.open(LOGO_PATH).convert("RGBA")
            fh = 30
            flw = int(logo.width * (fh / logo.height))
            logo = logo.resize((flw, fh), Image.LANCZOS)
            img.paste(logo, (CARD_WIDTH - PADDING - flw, fy + 5), logo)
            draw.text((CARD_WIDTH - PADDING - flw - hw - 10, fy + 12), handle, font=f15b, fill=ACCENT2)
    except:
        draw.text((CARD_WIDTH - PADDING - hw, fy + 12), handle, font=f15b, fill=ACCENT2)

    buf = io.BytesIO()
    img.save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf.getvalue()
