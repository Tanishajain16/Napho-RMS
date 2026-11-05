#!/bin/bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "============================================"
echo "  Napho RMS — Starting All Services"
echo "============================================"

# 1. Setup backend venv
echo ""
echo "Setting up backend..."
cd "$ROOT/backend"
if [ ! -d "venv" ]; then
    echo "  Creating virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt -q

# 2. Seed demo data (idempotent — safe to run every time)
echo "  Seeding demo data..."
python seed.py

# 3. Start backend
echo ""
echo "Starting backend (FastAPI)..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/napho-backend.log 2>&1 &
BACKEND_PID=$!

# Wait for backend
for i in $(seq 1 15); do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "  Backend ready at http://localhost:8000"
        break
    fi
    sleep 1
done

# 4. Start frontend
echo ""
echo "Starting frontend (Next.js)..."
cd "$ROOT/frontend"
if [ ! -d "node_modules" ]; then
    echo "  Installing npm packages..."
    npm install -q
fi
npm run dev > /tmp/napho-frontend.log 2>&1 &
FRONTEND_PID=$!

sleep 3
echo ""
echo "============================================"
echo "  Napho RMS is running!"
echo "============================================"
echo ""
echo "  App:      http://localhost:3000"
echo "  API:      http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo "  DB:       SQLite (backend/napho.db)"
echo ""
echo "  Demo Credentials:"
echo "  +-----------------------------------------+"
echo "  | Employee  aryan@napho.com / password123  |"
echo "  | Employee  sneha@napho.com / password123  |"
echo "  | Approver  priya@napho.com / password123  |"
echo "  | Finance   rahul@napho.com / password123  |"
echo "  | Admin     admin@napho.com / password123  |"
echo "  +-----------------------------------------+"
echo ""
echo "  Logs:"
echo "    Backend:  /tmp/napho-backend.log"
echo "    Frontend: /tmp/napho-frontend.log"
echo ""
echo "  Press Ctrl+C to stop all services"
echo ""

trap "echo ''; echo 'Stopping...'; kill \$BACKEND_PID \$FRONTEND_PID 2>/dev/null; echo 'All stopped.'" EXIT INT TERM
wait $BACKEND_PID $FRONTEND_PID
