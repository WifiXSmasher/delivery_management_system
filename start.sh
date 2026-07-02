#!/bin/bash
cd "$(dirname "$0")"

echo "============================================"
echo "  TRANSPORT - Delivery Management"
echo "============================================"

# Auto-backup DB on start
if [ -f kap_transport.db ]; then
    mkdir -p backups
    cp kap_transport.db "backups/autobackup_$(date +%Y%m%d_%H%M%S).db"
    echo "[OK] Auto-backup created."
fi

# Create venv if needed
if [ ! -d venv ]; then
    echo "[..] First-time setup..."
    python3 -m venv venv
fi

# Install deps
venv/bin/pip install -r requirements.txt --quiet
echo "[OK] Dependencies ready."

# Migrate
venv/bin/python manage.py migrate --run-syncdb > /dev/null 2>&1
echo "[OK] Database ready."

# Open browser
sleep 2 && open http://localhost:8000 2>/dev/null || xdg-open http://localhost:8000 2>/dev/null &

echo ""
echo "  App running at: http://localhost:8000"
echo "  Default login:  admin / admin123"
echo "  Press Ctrl+C to stop."
echo ""
venv/bin/python manage.py runserver 8000
