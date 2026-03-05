#!/bin/bash
# 0. Initialize database tables and seed data
echo "Initializing database..."
python -c "from main import init_db; init_db()"

# 1. Start the Python Flask backend in the background
echo "Booting Python Flask server for DavOS..."
gunicorn --bind 0.0.0.0:${FLASK_PORT:-5001} main:app &

# 2. Start the Node server in the foreground (already built)
echo "Booting Node server..."
NODE_ENV=production node dist/index.cjs
