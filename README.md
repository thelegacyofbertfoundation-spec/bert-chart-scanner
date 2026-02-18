# 🔬 Dr. Inker Chart Scanner

**AI-Powered Screenshot-to-Trade Analysis Bot for Telegram**

Send any chart screenshot → Get instant AI technical analysis with trend direction, support/resistance levels, pattern detection, risk assessment, and Buy/Sell/Hold verdicts.

Built by **Dr. Inker LABS** | Powered by Google Gemini Vision AI

---

## ✨ Features

### Telegram Bot
- 📸 Send any chart screenshot (DexScreener, TradingView, Birdeye, etc.)
- 🧠 AI-powered technical analysis via Gemini Vision
- 📊 Trend, support/resistance, patterns, volume, risk assessment
- ⚡ Energy system (3 free scans/day)
- 👑 Premium tier (unlimited scans via Telegram Stars)
- 🔗 Referral system (earn bonus scans)
- 🏆 Leaderboard

### Mini App Dashboard
- 📜 Full scan history with detail view
- 📊 Analytics (trend distribution, action breakdown, top tokens)
- ⚡ Energy status
- 🏆 Global leaderboard

---

## 🚀 Quick Setup

### 1. Prerequisites
- Python 3.10+
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Google Gemini API Key (from [AI Studio](https://aistudio.google.com/apikey))

### 2. Create the Bot
1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow the prompts
3. Save the bot token
4. Send `/setdescription` → Set a description
5. Send `/setabouttext` → Set about text
6. **Important:** Send `/setmenubutton` → Set the Mini App URL later

### 3. Get Gemini API Key
1. Go to [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Click "Create API Key"
3. Save the key

### 4. Local Development
```bash
# Clone/download the project
cd screenshot-trade-bot

# Install dependencies
pip install -r requirements.txt

# Copy env file and fill in your values
cp .env.example .env
# Edit .env with your tokens

# Run the bot
python bot.py

# In another terminal, run the web server
python web_server.py
```

### 5. Deploy to Railway
1. Push code to GitHub
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Add environment variables:
   - `TELEGRAM_BOT_TOKEN` = your bot token
   - `GEMINI_API_KEY` = your Gemini key
   - `WEBAPP_URL` = your Railway URL (e.g., `https://your-app.up.railway.app`)
4. Railway will auto-detect the Procfile and deploy

### 6. Configure Mini App
After deployment, go back to @BotFather:
1. `/setmenubutton` → Select your bot → Enter your `WEBAPP_URL/app`
2. This adds the "Dashboard" button in the bot chat

---

## 📁 Project Structure

```
screenshot-trade-bot/
├── bot.py              # Main Telegram bot (handlers, commands, payments)
├── gemini_analyzer.py  # Gemini Vision chart analysis engine
├── database.py         # SQLite database (users, scans, energy, referrals)
├── web_server.py       # Flask server for Mini App + API
├── config.py           # Configuration and Gemini prompt
├── start.sh            # Startup script (bot + web server)
├── Procfile            # Railway deployment config
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variables template
└── templates/
    └── mini_app.html   # Telegram Mini App dashboard
```

---

## 💰 Monetization

| Feature | Price | Notes |
|---------|-------|-------|
| Free daily scans | 3/day | Resets daily |
| Scan refill | 5 Stars = 5 scans | Bonus scans never expire |
| Premium | 150 Stars/month | Unlimited scans + extras |
| Referral bonus | 5 scans/referral | Referrer gets 5, referee gets 3 |

---

## 🔧 Customization

### Adjust Energy/Pricing
Edit `config.py`:
```python
FREE_DAILY_SCANS = 3          # Free scans per day
ENERGY_REFILL_STARS = 5       # Stars per refill pack
PREMIUM_STARS_MONTHLY = 150   # Monthly premium cost
REFERRAL_BONUS_SCANS = 5      # Scans per referral
```

### Change Gemini Model
Edit `config.py`:
```python
GEMINI_MODEL = "gemini-2.0-flash"     # Fast & cheap
# or
GEMINI_MODEL = "gemini-2.0-pro"       # More accurate, slower
```

### Customize Analysis Prompt
Edit `CHART_ANALYSIS_PROMPT` in `config.py` to adjust what the AI looks for.

---

## ⚠️ Disclaimer

This bot provides AI-generated technical analysis for educational purposes only.
It is NOT financial advice. Always do your own research (DYOR) before making
any trading decisions. Dr. Inker LABS is not responsible for any financial losses.

---

## 📝 License

Built by Dr. Inker LABS. All rights reserved.
