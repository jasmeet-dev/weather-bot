#!/bin/bash
cd "$(dirname "$0")"
echo "Starting Weather Bot GUI..."
open http://localhost:8501
python3 -m streamlit run app.py --server.headless true
