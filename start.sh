#!/bin/bash
# Dr. Inker LABS - Screenshot-to-Trade Bot Launcher
# Starts both the Telegram bot and the Flask web server

echo "🔬 Dr. Inker Chart Scanner - Starting..."

# Create data directory
mkdir -p data

# Start Flask web server in background
echo "🌐 Starting web server on port ${PORT:-8080}..."
gunicorn web_server:app --bind 0.0.0.0:${PORT:-8080} --workers 2 --timeout 120 &
WEB_PID=$!

# Small delay to let web server start
sleep 2

# Start Telegram bot
echo "🤖 Starting Telegram bot..."
python bot.py &
BOT_PID=$!

echo "✅ All services started!"
echo "   Web server PID: $WEB_PID"
echo "   Bot PID: $BOT_PID"

# Wait for either process to exit
wait -n $WEB_PID $BOT_PID
EXIT_CODE=$?

# Kill remaining process
kill $WEB_PID $BOT_PID 2>/dev/null

echo "❌ Service exited with code $EXIT_CODE"
exit $EXIT_CODE
