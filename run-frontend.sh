#!/bin/bash

# Run Angular Frontend Locally (Development)
# This starts the Angular dev server for local development

set -e

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$BASE_DIR/ecommerce-bot"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

FRONTEND_CLI="./node_modules/@angular/cli/bin/ng"
if [ ! -x "$FRONTEND_CLI" ]; then
    echo "📦 Angular CLI not found in node_modules. Installing dependencies..."
    npm install
fi

echo "🚀 Starting development server..."
echo ""
echo "Frontend will be available at: http://localhost:4200"
echo "Backend API should be running at: http://localhost:8001"
echo ""
echo "Press Ctrl+C to stop"
echo ""

exec node "$FRONTEND_CLI" serve --proxy-config proxy.conf.json --host 0.0.0.0 --port 4200