#!/bin/bash
echo "🔬 BERT Chart Scanner - Starting..."
mkdir -p data

echo "🌐 Starting server (webhook mode)..."
exec gunicorn web_server:app --bind 0.0.0.0:${PORT:-8080} --workers 1 --threads 4 --timeout 120 --preload
