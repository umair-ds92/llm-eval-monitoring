#!/bin/bash
# Quick demo script

echo "LLM Eval & Monitoring Demo"
echo "=============================="

# Initialize database
echo "Initializing database..."
python scripts/init_db.py

# Run evaluations
echo "Running evaluations..."
python -m src.experiments.run_smoke_eval

# Start API in background
echo "Starting API..."
uvicorn src.api.main:app --port 8000 > /dev/null 2>&1 &
API_PID=$!

# Wait for API
sleep 3

# Start dashboard
echo "Starting dashboard at http://localhost:8501"
echo "Press Ctrl+C to stop"

# Use python -m streamlit OR set PYTHONPATH
# PYTHONPATH=. streamlit run src/monitoring/dashboard.py
python -m streamlit run src/monitoring/dashboard.py

# Cleanup
kill $API_PID 2>/dev/null