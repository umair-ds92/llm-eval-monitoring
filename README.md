# LLM Evaluation & Monitoring System

A production-grade framework for evaluating, monitoring, and benchmarking Large Language Models (LLMs) with a focus on cybersecurity applications. Built for enterprises that need reliable, observable, and compliant AI systems.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-green.svg)](https://www.sqlalchemy.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-teal.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Overview

Large Language Models deployed in production require continuous evaluation and monitoring to ensure accuracy, safety, performance, and reliability. This framework provides a modular platform for:

- **Evaluating** LLM outputs against multiple quality dimensions
- **Monitoring** runtime behavior and performance metrics
- **Alerting** on threshold violations and anomalies
- **Analyzing** trends and patterns in model behavior

### Importance

- **Prevent Silent Degradation**: Catch quality regressions before they impact users
- **Ensure Safety**: Detect toxic, harmful, or inappropriate content
- **Maintain Compliance**: Meet regulatory requirements for AI systems
- **Optimize Performance**: Identify and resolve latency bottlenecks

---

## Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                   Client Applications                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │   FastAPI REST API   │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │  Evaluation Pipeline │
              └──────────┬───────────┘
                         │
        ┌────────────────┼────────────────┬──────────────┐
        ▼                ▼                ▼              ▼
   ┌─────────┐    ┌──────────┐    ┌──────────┐   ┌──────────┐
   │ Latency │    │ Toxicity │    │Factuality│   │   IOC    │
   │         │    │          │    │          │   │Extraction│
   └─────────┘    └──────────┘    └──────────┘   └──────────┘
        │                │                │              │
        └────────────────┼────────────────┼──────────────┘
                         ▼                ▼
              ┌──────────────────┐  ┌──────────┐
              │   PostgreSQL/    │  │  Redis   │
              │   SQLite DB      │  │  Cache   │
              └──────────┬───────┘  └──────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │  Monitoring & Alerts │
              └──────────────────────┘
```

---

## Features

### Core Capabilities

- **Latency Measurement**: Track response times (p50, p95, p99, mean)
- **Toxicity Detection**: Identify harmful or inappropriate content using ML models
- **Factuality Assessment**: Validate accuracy via LLM-as-judge or semantic similarity
- **Semantic Similarity**: Compare responses using sentence embeddings
- **Alert System**: Configurable thresholds with cooldown periods

### Cybersecurity-Specific

- **IOC Extraction**: Validate extraction of IPs, domains, hashes, CVEs
- **Threat Intelligence**: Verify threat actor identification
- **Malware Analysis**: Evaluate sandbox output interpretation
- **CVE Detection**: Assess vulnerability identification accuracy

### Integration & Deployment

- **REST API**: Complete OpenAPI/Swagger documentation
- **Multiple Databases**: SQLite (dev), PostgreSQL (prod)
- **Caching Layer**: Redis for performance optimization
- **Docker Support**: Production-ready containerization

---

## Evaluation Metrics

| Metric | Description | Thresholds |
|--------|-------------|------------|
| **Latency** | Response time with percentile tracking | p95 < 2s, p99 < 5s |
| **Toxicity** | Multi-category harmful content detection | score < 0.7 |
| **Factuality** | Accuracy via LLM judge or similarity | score > 0.8 |
| **IOC Extraction** | Precision/recall of threat indicators | F1 > 0.75 |
| **CVE Detection** | Vulnerability identification accuracy | Recall > 0.8 |

---

## Quick Start

### Installation
```bash
# Clone and setup
git clone https://github.com/yourusername/llm-eval-monitoring.git
cd llm-eval-monitoring

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python scripts/init_db.py

# Run evaluations
python -m src.experiments.run_smoke_eval

# Start API (optional - for external access)
uvicorn src.api.main:app --reload --port 8000

# Start dashboard
python -m streamlit run src/monitoring/dashboard.py

```

Access:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs  
- **Dashboard**: http://localhost:8501

---

## Project Structure
```
llm-eval-monitoring/
├── configs/                    # Environment configurations
│   ├── dev.yaml
│   └── prod.yaml
├── data/
│   ├── golden/                # Test datasets
│   └── prompts/               # Prompt templates
├── scripts/
│   └── init_db.py            # Database initialization
├── src/
│   ├── api/                  # FastAPI application
│   ├── common/               # Shared utilities
│   ├── evaluation/           # Evaluation metrics
│   ├── inference/            # LLM routing
│   ├── monitoring/           # Monitoring & alerts
│   └── storage/              # Database layer
├── tests/                    # Test 
|── run_demo.sh
├── requirements.txt
└── README.md
```

---
