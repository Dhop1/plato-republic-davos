#!/bin/bash
# 1. Start the Python Flask backend in the background
echo "Booting Python Flask server for DavOS..."
gunicorn --bind 0.0.0.0:$FLASK_PORT main:app &

# 2. Start the Node frontend/server in the foreground
echo "Booting Node server..."
npm run build && NODE_ENV=production node dist/index.cjs
