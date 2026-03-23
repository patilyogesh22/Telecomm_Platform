#!/bin/bash
# ═══════════════════════════════════════
# deploy.sh — One-command redeploy script
# Run on EC2: bash deploy.sh
# ═══════════════════════════════════════

set -e

echo "═══════════════════════════════════"
echo " Telecomm Platform — Deploying..."
echo "═══════════════════════════════════"

# Pull latest code
echo "[1/4] Pulling latest code from GitHub..."
git pull origin main

# Stop old containers
echo "[2/4] Stopping existing containers..."
docker-compose down

# Rebuild and start
echo "[3/4] Building and starting containers..."
docker-compose up -d --build

# Show status
echo "[4/4] Checking container status..."
docker-compose ps

echo ""
echo "✅ Deployment complete!"
echo "   App running at: http://$(curl -s ifconfig.me)"
echo "═══════════════════════════════════"