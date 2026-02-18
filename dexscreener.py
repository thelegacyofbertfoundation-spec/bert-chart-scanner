"""
Dr. Inker LABS - DexScreener Enrichment Module
Fetches live token data from DexScreener API to enhance Gemini analysis.
"""
import aiohttp
import asyncio
import re
import logging

logger = logging.getLogger(__name__)

DEXSCREENER_API = "https://api.dexscreener.com/latest/dex"
DEXSCREENER_SEARCH = "https://api.dexscreener.com/latest/dex/search"


async def search_token(query: str) -> dict | None:
    """
    Search DexScreener for a token by name, ticker, or contract address.
    Returns the best matching pair or None.
    """
    if not query or query.lower() in ("unknown", "n/a", "null", "none"):
        return None

    try:
        async with aiohttp.ClientSession() as session:
            # Check if it looks like a contract address
            is_address = len(query) > 30 and re.match(r'^[a-zA-Z0-9]+$', query)

            if is_address:
                url = f"{DEXSCREENER_API}/tokens/{query}"
            else:
                url = f"{DEXSCREENER_SEARCH}?q={query}"

            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    logger.warning(f"DexScreener API returned {resp.status}")
                    return None

                data = await resp.json()
                pairs = data.get("pairs", [])

                if not pairs:
                    return None

                # Sort by liquidity/volume to get the best pair
                pairs.sort(
                    key=lambda p: float(p.get("liquidity", {}).get("usd", 0) or 0),
                    reverse=True
                )

                pair = pairs[0]
                return parse_pair_data(pair)

    except asyncio.TimeoutError:
        logger.warning("DexScreener API timeout")
        return None
    except Exception as e:
        logger.error(f"DexScreener error: {e}")
        return None


def parse_pair_data(pair: dict) -> dict:
    """Parse DexScreener pair data into a clean format."""
    base = pair.get("baseToken", {})
    quote = pair.get("quoteToken", {})
    txns = pair.get("txns", {})
    volume = pair.get("volume", {})
    price_change = pair.get("priceChange", {})
    liquidity = pair.get("liquidity", {})

    # Transaction counts
    h24_txns = txns.get("h24", {})
    buys_24h = h24_txns.get("buys", 0)
    sells_24h = h24_txns.get("sells", 0)

    # Buy/sell ratio
    total_txns = buys_24h + sells_24h
    buy_ratio = (buys_24h / total_txns * 100) if total_txns > 0 else 50

    return {
        "found": True,
        "token_name": base.get("name", "Unknown"),
        "token_symbol": base.get("symbol", "???"),
        "contract_address": base.get("address", ""),
        "chain": pair.get("chainId", "unknown"),
        "dex": pair.get("dexId", "unknown"),
        "pair_address": pair.get("pairAddress", ""),
        "price_usd": pair.get("priceUsd", "0"),
        "price_native": pair.get("priceNative", "0"),
        "market_cap": pair.get("marketCap", 0) or pair.get("fdv", 0),
        "fdv": pair.get("fdv", 0),
        "liquidity_usd": liquidity.get("usd", 0),
        "volume_24h": volume.get("h24", 0),
        "volume_6h": volume.get("h6", 0),
        "volume_1h": volume.get("h1", 0),
        "price_change_5m": price_change.get("m5", 0),
        "price_change_1h": price_change.get("h1", 0),
        "price_change_6h": price_change.get("h6", 0),
        "price_change_24h": price_change.get("h24", 0),
        "buys_24h": buys_24h,
        "sells_24h": sells_24h,
        "buy_ratio": round(buy_ratio, 1),
        "total_txns_24h": total_txns,
        "pair_created": pair.get("pairCreatedAt", None),
        "url": pair.get("url", ""),
        "info_links": pair.get("info", {}).get("websites", []),
        "social_links": pair.get("info", {}).get("socials", []),
    }


def format_enrichment_text(data: dict) -> str:
    """Format DexScreener data into a Telegram message section."""
    if not data or not data.get("found"):
        return ""

    # Format numbers
    def fmt_usd(val):
        try:
            val = float(val)
            if val >= 1_000_000_000:
                return f"${val/1_000_000_000:.2f}B"
            elif val >= 1_000_000:
                return f"${val/1_000_000:.2f}M"
            elif val >= 1_000:
                return f"${val/1_000:.1f}K"
            elif val >= 1:
                return f"${val:.2f}"
            else:
                return f"${val:.6f}"
        except:
            return "$0"

    def fmt_change(val):
        try:
            val = float(val)
            emoji = "🟢" if val >= 0 else "🔴"
            return f"{emoji} {val:+.1f}%"
        except:
            return "⚪ N/A"

    # Buy pressure indicator
    buy_ratio = data.get("buy_ratio", 50)
    if buy_ratio >= 65:
        pressure = "🟢 Strong Buy Pressure"
    elif buy_ratio >= 55:
        pressure = "🟢 Slight Buy Pressure"
    elif buy_ratio >= 45:
        pressure = "🟡 Balanced"
    elif buy_ratio >= 35:
        pressure = "🔴 Slight Sell Pressure"
    else:
        pressure = "🔴 Strong Sell Pressure"

    # Liquidity assessment
    liq = float(data.get("liquidity_usd", 0) or 0)
    if liq >= 500_000:
        liq_status = "🟢 High"
    elif liq >= 100_000:
        liq_status = "🟡 Medium"
    elif liq >= 10_000:
        liq_status = "🟠 Low"
    else:
        liq_status = "🔴 Very Low"

    chain_name = {
        "solana": "Solana", "ethereum": "Ethereum", "bsc": "BSC",
        "base": "Base", "arbitrum": "Arbitrum", "polygon": "Polygon"
    }.get(data.get("chain", ""), data.get("chain", "Unknown").title())

    msg = f"""
📡 <b>LIVE DATA</b> (DexScreener)
━━━━━━━━━━━━━━━━━━━━

💰 <b>Price:</b> {fmt_usd(data['price_usd'])}
📊 <b>Market Cap:</b> {fmt_usd(data.get('market_cap', 0))}
💧 <b>Liquidity:</b> {fmt_usd(data.get('liquidity_usd', 0))} ({liq_status})
📈 <b>24h Volume:</b> {fmt_usd(data.get('volume_24h', 0))}

━━━ PRICE CHANGES ━━━
5m: {fmt_change(data.get('price_change_5m'))}
1h: {fmt_change(data.get('price_change_1h'))}
6h: {fmt_change(data.get('price_change_6h'))}
24h: {fmt_change(data.get('price_change_24h'))}

━━━ ACTIVITY ━━━
🔄 24h Transactions: {data.get('total_txns_24h', 0):,}
🟢 Buys: {data.get('buys_24h', 0):,} | 🔴 Sells: {data.get('sells_24h', 0):,}
📊 Buy Ratio: {buy_ratio}% — {pressure}

⛓ Chain: {chain_name} | DEX: {data.get('dex', 'Unknown').title()}
"""

    # Add contract address (copyable)
    ca = data.get("contract_address", "")
    if ca:
        msg += f"\n📋 CA: <code>{ca}</code>"

    # Add DexScreener link
    url = data.get("url", "")
    if url:
        msg += f'\n🔗 <a href="{url}">View on DexScreener</a>'

    msg += f"\n\n━━━━━━━━━━━━━━━━━━━━"

    return msg.strip()


async def enrich_analysis(analysis: dict) -> dict | None:
    """
    Attempt to enrich analysis with live DexScreener data.
    Tries contract address first, then token name/ticker.
    """
    # Try contract address first
    ca = analysis.get("contract_address")
    if ca and ca != "null" and ca != "None" and len(str(ca)) > 10:
        data = await search_token(str(ca))
        if data:
            return data

    # Try ticker
    ticker = analysis.get("ticker")
    if ticker and ticker not in ("???", "Unknown", "N/A", "null"):
        data = await search_token(str(ticker))
        if data:
            return data

    # Try token name
    token = analysis.get("token")
    if token and token not in ("Unknown", "N/A", "null"):
        data = await search_token(str(token))
        if data:
            return data

    return None
