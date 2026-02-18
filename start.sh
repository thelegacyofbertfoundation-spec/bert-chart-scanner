#!/bin/bash
echo "BERT Chart Scanner - Starting..."
mkdir -p data

echo "Starting server (webhook mode)..."
exec gunicorn web_server:app --bind 0.0.0.0:${PORT:-8080} --workers 1 --threads 4 --timeout 120
```

Save, then:
```
cd C:\Users\Sjpch\OneDrive\Desktop\BertCS\screenshot-trade-bot
git add -A
git commit -m "Fix worker preload"
git push --force
