"""
Dr. Inker LABS - Web Server for Mini App
Serves the Telegram Mini App dashboard and API endpoints.
"""
import os
import json
from flask import Flask, render_template, jsonify, request
from database import init_db, get_scan_history, get_energy_status, get_leaderboard, get_or_create_user

app = Flask(__name__, template_folder="templates", static_folder="static")


@app.route("/")
def index():
    """Health check."""
    return jsonify({"status": "ok", "app": "Dr. Inker Chart Scanner"})


@app.route("/app")
def mini_app():
    """Serve the Telegram Mini App."""
    user_id = request.args.get("user_id", "0")
    return render_template("mini_app.html", user_id=user_id)


# ═══════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════

@app.route("/api/history/<int:user_id>")
def api_history(user_id):
    """Get scan history for a user."""
    limit = request.args.get("limit", 50, type=int)
    scans = get_scan_history(user_id, limit=limit)
    
    # Parse full_analysis JSON
    for scan in scans:
        if scan.get("full_analysis"):
            try:
                scan["full_analysis"] = json.loads(scan["full_analysis"])
            except:
                pass
    
    return jsonify({"scans": scans})


@app.route("/api/energy/<int:user_id>")
def api_energy(user_id):
    """Get energy status for a user."""
    energy = get_energy_status(user_id)
    return jsonify(energy)


@app.route("/api/leaderboard")
def api_leaderboard():
    """Get leaderboard."""
    leaders = get_leaderboard(20)
    return jsonify({"leaderboard": leaders})


@app.route("/api/stats/<int:user_id>")
def api_stats(user_id):
    """Get user stats and analytics."""
    scans = get_scan_history(user_id, limit=200)
    
    if not scans:
        return jsonify({
            "total_scans": 0,
            "accuracy": 0,
            "top_tokens": [],
            "trend_distribution": {},
            "action_distribution": {},
            "risk_distribution": {}
        })
    
    # Calculate stats
    trends = {}
    actions = {}
    risks = {}
    tokens = {}
    
    for scan in scans:
        t = scan.get("trend", "Unknown")
        trends[t] = trends.get(t, 0) + 1
        
        a = scan.get("action", "Unknown")
        actions[a] = actions.get(a, 0) + 1
        
        r = scan.get("risk_level", "Unknown")
        risks[r] = risks.get(r, 0) + 1
        
        tk = scan.get("token", "Unknown")
        if tk and tk != "Unknown":
            tokens[tk] = tokens.get(tk, 0) + 1
    
    top_tokens = sorted(tokens.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return jsonify({
        "total_scans": len(scans),
        "top_tokens": [{"token": t, "count": c} for t, c in top_tokens],
        "trend_distribution": trends,
        "action_distribution": actions,
        "risk_distribution": risks,
        "avg_confidence": sum(s.get("confidence", 0) or 0 for s in scans) / len(scans) if scans else 0
    })


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
