#!/bin/bash

# Deploy Angular Ecommerce Bot
# This builds and serves the Angular application

set -e

echo "🛍️  Deploying Angular Ecommerce Bot"
echo "==================================="

cd ecommerce-bot

# Install dependencies
echo "📦 Installing dependencies..."
npm install

# Build for production
echo "🔨 Building application..."
npm run build

# Serve the application
echo "🚀 Starting server..."
npm run serve:ssr:ecommerce-bot

echo ""
echo "✅ Ecommerce Bot deployed!"
echo "   🌐 Available at: http://localhost:4000"