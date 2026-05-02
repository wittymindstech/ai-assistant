#!/bin/bash

# Run Angular Frontend Locally (Development)
# This starts the Angular dev server for local development

set -e

echo "🛍️  Starting Angular Ecommerce Frontend (Development)"
echo "==================================================="

cd ecommerce-bot

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

echo "🚀 Starting development server..."
echo ""
echo "Frontend will be available at: http://localhost:4200"
echo "Backend API should be running at: http://localhost:8001"
echo ""
echo "Press Ctrl+C to stop"
echo ""

npm start