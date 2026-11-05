#!/bin/bash
ROOT="$(cd "$(dirname "$0")" && pwd)"
echo "Stopping Napho RMS..."
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true
pkill -f "next-server" 2>/dev/null || true
cd "$ROOT" && docker compose stop postgres
echo "All services stopped."
echo "   To remove DB data: docker compose down -v"
