.PHONY: help build up down restart logs clean test status shell db-migrate demo dev prod

# Default target
help:
	@echo "LLM Evaluation & Monitoring - Docker Commands"
	@echo "=============================================="
	@echo ""
	@echo "Development:"
	@echo "  make dev          - Start in development mode"
	@echo "  make build        - Build Docker images"
	@echo "  make up           - Start services in background"
	@echo "  make down         - Stop services"
	@echo "  make restart      - Restart services"
	@echo "  make logs         - View logs (follow)"
	@echo "  make status       - Check service status"
	@echo ""
	@echo "Production:"
	@echo "  make prod         - Start in production mode"
	@echo "  make prod-build   - Build production images"
	@echo ""
	@echo "Database:"
	@echo "  make db-shell     - Open database shell"
	@echo "  make db-migrate   - Run database migrations"
	@echo "  make db-backup    - Backup database"
	@echo ""
	@echo "Maintenance:"
	@echo "  make shell        - Shell into API container"
	@echo "  make test         - Run tests in container"
	@echo "  make clean        - Remove containers and volumes"
	@echo "  make clean-all    - Deep clean (images + cache)"
	@echo ""
	@echo "Demo:"
	@echo "  make demo         - Quick demo startup"

# Development mode (with live reload)
dev:
	docker compose up

# Build images
build:
	docker compose build --no-cache

# Start services in background
up:
	docker compose up -d
	@echo ""
	@echo "✓ Services started:"
	@echo "  API:       http://localhost:8000"
	@echo "  API Docs:  http://localhost:8000/docs"
	@echo "  Dashboard: http://localhost:8501"
	@echo "  Database:  localhost:5432"
	@echo ""

# Stop services
down:
	docker compose down

# Restart services
restart:
	docker compose restart
	@echo "✓ Services restarted"

# View logs (follow)
logs:
	docker compose logs -f

# Check service status
status:
	docker compose ps
	@echo ""
	@docker compose exec api curl -s http://localhost:8000/health || echo "API: Not responding"

# Production mode
prod:
	docker compose -f docker compose.prod.yml up -d
	@echo "✓ Production services started"

prod-build:
	docker compose -f docker compose.prod.yml build --no-cache

# Shell into API container
shell:
	docker compose exec api /bin/bash

# Database shell
db-shell:
	docker compose exec postgres psql -U llm_eval -d llm_eval

# Run database migrations
db-migrate:
	docker compose exec api python scripts/init_db.py

# Backup database
db-backup:
	docker compose exec postgres pg_dump -U llm_eval llm_eval > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "✓ Database backed up"

# Run tests in container
test:
	docker compose exec api pytest tests/

# Clean up (remove containers and volumes)
clean:
	docker compose down -v
	@echo "✓ Containers and volumes removed"

# Deep clean (remove everything including images)
clean-all:
	docker compose down -v --rmi all
	docker system prune -af --volumes
	@echo "✓ Complete cleanup done"

# Quick demo
demo:
	@echo "Starting demo..."
	@make build
	@make up
	@echo ""
	@echo "Waiting for services to start..."
	@sleep 10
	@echo ""
	@echo "✓ Demo ready! Access:"
	@echo "  Dashboard: http://localhost:8501"
	@echo "  API Docs:  http://localhost:8000/docs"

# View specific service logs
logs-api:
	docker compose logs -f api

logs-dashboard:
	docker compose logs -f dashboard

logs-db:
	docker compose logs -f postgres

# Check resource usage
stats:
	docker stats

# Inspect a service
inspect-api:
	docker compose exec api env

# Build without cache (CI)
ci-build:
	docker compose build --no-cache --pull

# Run tests in CI
ci-test:
	docker compose run --rm api pytest tests/ -v

# Health check
health:
	@curl -f http://localhost:8000/health || exit 1
	@curl -f http://localhost:8501/_stcore/health || exit 1
	@echo "✓ All services healthy"

# Pull latest images (production)
pull:
	docker compose pull

# Deploy with zero downtime
deploy:
	docker compose pull
	docker compose up -d --no-deps --build api
	docker compose up -d --no-deps --build dashboard

# Rollback to previous version
rollback:
	docker compose down
	git checkout HEAD~1
	docker compose up -d