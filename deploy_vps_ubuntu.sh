#!/bin/bash
# ==============================================================================
# SCRIPT CÀI ĐẶT 1-CLICK PARENTAL CONTROL TRÊN UBUNTU VPS
# ==============================================================================

set -e

echo "🚀 ĐANG TIẾN HÀNH CÀI ĐẶT PARENTAL CONTROL V2.0 TRÊN UBUNTU VPS..."

# 1. Cập nhật hệ thống
sudo apt-get update && sudo apt-get upgrade -y

# 2. Cài đặt Docker & Docker Compose nếu chưa có
if ! command -v docker &> /dev/null; then
    echo "📦 Đang cài đặt Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
fi

if ! command -v docker-compose &> /dev/null; then
    echo "📦 Đang cài đặt Docker Compose..."
    sudo apt-get install -y docker-compose-plugin docker-compose
fi

# 3. Chạy Docker Compose
echo "🛠️ Đang build và khởi chạy các Docker Container (PostgreSQL + FastAPI + Nginx)..."
sudo docker-compose down || true
sudo docker-compose up -d --build

echo "=============================================================================="
echo "✅ HOÀN TẤT DEPLOYMENT THÀNH CÔNG TRÊN UBUNTU VPS!"
echo "🌐 Manager Web URL:  http://$(curl -s ifconfig.me)"
echo "🔌 Backend API URL:   http://$(curl -s ifconfig.me)/api"
echo "⚡ WebSocket Stream:   ws://$(curl -s ifconfig.me)/ws"
echo "=============================================================================="
