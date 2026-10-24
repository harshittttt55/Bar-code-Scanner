#!/bin/bash

echo "🚀 Starting BarcodeAI App..."

# Backend
echo "📦 Setting up backend..."
cd backend
python3 -m venv venv 2>/dev/null || true
source venv/bin/activate
pip install -r requirements.txt -q

if [ ! -f .env ]; then
  cp .env.example .env
  echo ""
  echo "⚠️  Please edit backend/.env and add your GEMINI_API_KEY"
  echo "   Get one free at: https://aistudio.google.com/app/apikey"
  echo ""
fi

uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!
echo "✅ Backend started (PID: $BACKEND_PID) at http://localhost:8000"

# Frontend
cd ../frontend
echo "📦 Installing frontend dependencies..."
npm install -q

echo "✅ Starting frontend at http://localhost:3000"
npm start &
FRONTEND_PID=$!

echo ""
echo "🎉 Both servers running!"
echo "   Frontend: http://localhost:3000"
echo "   Backend:  http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo '✋ Stopped.'" INT TERM
wait
