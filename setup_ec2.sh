#!/bin/bash
# ═══════════════════════════════════════
# setup_ec2.sh — Run ONCE on fresh EC2
# sudo bash setup_ec2.sh
# ═══════════════════════════════════════

set -e

echo "═══════════════════════════════════"
echo " EC2 Bootstrap — Installing tools"
echo "═══════════════════════════════════"

# Update system
apt-get update && apt-get upgrade -y

# Install Docker
echo "[1/3] Installing Docker..."
apt-get install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
  | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Install docker-compose standalone
echo "[2/3] Installing docker-compose..."
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Add ubuntu user to docker group
usermod -aG docker ubuntu

# Install git
echo "[3/3] Installing git..."
apt-get install -y git

# Enable Docker on boot
systemctl enable docker
systemctl start docker

echo ""
echo "✅ EC2 setup complete!"
echo "   Docker: $(docker --version)"
echo "   Compose: $(docker-compose --version)"
echo "   Git: $(git --version)"
echo ""
echo "⚠️  Log out and back in for docker group to take effect"
echo "═══════════════════════════════════"