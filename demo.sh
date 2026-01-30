#!/bin/bash
# Smart demo launcher - choose local or Docker

echo "🔒 LLM Evaluation & Monitoring Demo"
echo "====================================="
echo ""
echo "Select deployment method:"
echo "  1) Local (fast, uses SQLite)"
echo "  2) Docker (production-like, uses PostgreSQL)"
echo ""
read -p "Choose [1-2]: " choice

case $choice in
    1)
        echo ""
        ./run_demo.sh
        ;;
    2)
        echo ""
        ./run_docker.sh
        ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac