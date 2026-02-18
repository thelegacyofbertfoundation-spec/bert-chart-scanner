"""
Dr. Inker LABS - Gemini Chart Analyzer
Handles image analysis via Google Gemini Vision API.
"""
import json
import re
import google.generativeai as genai
from config import GEMINI_API_KEY, GEMINI_MODEL, CHART_ANALYSIS_PROMPT


# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)


def analyze_chart(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    """
    Analyze a chart screenshot using Gemini Vision.
    
    Args:
        image_bytes: Raw image bytes
        mime_type: Image MIME type
    
    Returns:
        dict with analysis results
    """
    model = genai.GenerativeModel(GEMINI_MODEL)
    
    image_part = {
        "mime_type": mime_type,
        "data": image_bytes
    }
    
    try:
        response = model.generate_content(
            [CHART_ANALYSIS_PROMPT, image_part],
            generation_config=genai.GenerationConfig(
                temperature=0.3,  # Low temp for more consistent analysis
                max_output_tokens=2000,
            )
        )
        
        # Extract JSON from response
        text = response.text.strip()
        
        # Try to parse JSON (handle markdown code blocks)
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if json_match:
            text = json_match.group(1)
        
        # Clean up any trailing commas or issues
        text = re.sub(r',\s*}', '}', text)
        text = re.sub(r',\s*]', ']', text)
        
        analysis = json.loads(text)
        
        # Validate required fields
        required = ["token", "trend", "action", "confidence", "risk_level", "verdict"]
        for field in required:
            if field not in analysis:
                analysis[field] = "Unknown"
        
        # Ensure confidence is int
        try:
            analysis["confidence"] = int(analysis["confidence"])
        except (ValueError, TypeError):
            analysis["confidence"] = 5
        
        analysis["success"] = True
        return analysis
        
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": "Failed to parse analysis. Please try with a clearer chart screenshot.",
            "raw_response": text if 'text' in dir() else str(e)
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Analysis failed: {str(e)}"
        }


def format_analysis_text(analysis: dict) -> str:
    """Format analysis into a readable Telegram message."""
    if not analysis.get("success"):
        return f"❌ {analysis.get('error', 'Analysis failed. Try a clearer screenshot.')}"
    
    # Trend emoji
    trend_emoji = {
        "Bullish": "🟢",
        "Bearish": "🔴",
        "Sideways": "🟡"
    }.get(analysis.get("trend"), "⚪")
    
    # Action emoji
    action_emoji = {
        "BUY": "🟢",
        "SELL": "🔴",
        "HOLD": "🟡",
        "WAIT": "⏳"
    }.get(analysis.get("action"), "⚪")
    
    # Risk emoji
    risk_emoji = {
        "LOW": "🟢",
        "MEDIUM": "🟡",
        "HIGH": "🟠",
        "EXTREME": "🔴"
    }.get(analysis.get("risk_level"), "⚪")
    
    # Confidence bar
    conf = analysis.get("confidence", 5)
    conf_bar = "█" * conf + "░" * (10 - conf)
    
    # Support/Resistance levels
    supports = analysis.get("support_levels", [])
    resistances = analysis.get("resistance_levels", [])
    support_text = " / ".join(str(s) for s in supports[:3]) if supports else "Not visible"
    resistance_text = " / ".join(str(r) for r in resistances[:3]) if resistances else "Not visible"
    
    # Patterns
    chart_patterns = analysis.get("chart_patterns", [])
    patterns_text = ", ".join(chart_patterns) if chart_patterns else "None detected"
    
    # Build message
    msg = f"""
🔬 <b>DR. INKER CHART SCAN</b> 🔬
━━━━━━━━━━━━━━━━━━━━

📊 <b>{analysis.get('token', 'Unknown')} ({analysis.get('ticker', '???')})</b>
⏱ Timeframe: {analysis.get('timeframe', 'N/A')}
📍 Platform: {analysis.get('platform', 'N/A')}
💰 Price: {analysis.get('current_price', 'N/A')}

━━━ TREND ━━━
{trend_emoji} Direction: <b>{analysis.get('trend', 'Unknown')}</b>
💪 Strength: {analysis.get('trend_strength', 'N/A')}

━━━ KEY LEVELS ━━━
🟢 Support: {support_text}
🔴 Resistance: {resistance_text}

━━━ PATTERNS ━━━
📐 Chart: {patterns_text}
📊 Volume: {analysis.get('volume_trend', 'N/A')}

━━━ VERDICT ━━━
{action_emoji} Action: <b>{analysis.get('action', 'N/A')}</b>
{risk_emoji} Risk: <b>{analysis.get('risk_level', 'N/A')}</b>
🎯 Confidence: [{conf_bar}] {conf}/10

💬 <b>{analysis.get('verdict', 'No verdict available')}</b>

━━━━━━━━━━━━━━━━━━━━
⚠️ <i>Not financial advice. Always DYOR.</i>
🔬 <i>Powered by Dr. Inker LABS</i>
"""
    return msg.strip()


def format_detailed_analysis(analysis: dict) -> str:
    """Format the detailed analysis section."""
    if not analysis.get("success"):
        return ""
    
    detail = analysis.get("detailed_analysis", "No detailed analysis available.")
    risk = analysis.get("risk_notes", "")
    
    msg = f"""
📝 <b>DETAILED ANALYSIS</b>
━━━━━━━━━━━━━━━━━━━━

{detail}

⚠️ <b>Risk Notes:</b> {risk}

━━━━━━━━━━━━━━━━━━━━
🔬 <i>Dr. Inker LABS</i>
"""
    return msg.strip()
