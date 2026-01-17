.PHONY: help install dev run test clean docker migrate seed

help:
	@echo "Available commands:"
	@echo "  make install    - Install dependencies"
	@echo "  make dev        - Run in development mode"
	@echo "  make run        - Run in production mode"
	@echo "  make test       - Run tests"
	@echo "  make clean      - Clean cache files"
	@echo "  make docker     - Build Docker image"
	@echo "  make docker-up  - Start Docker Compose"
	@echo "  make migrate    - Run database migrations"
	@echo "  make seed       - Seed vaccine data"
	@echo "  make lint       - Run linters"

install:
	pip install -r requirements.txt

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

test:
	pytest --cov=app tests/ --cov-report=html

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage

docker:
	docker build -t vaccination-backend .

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

migrate:
	alembic upgrade head

migration:
	alembic revision --autogenerate -m "$(msg)"

seed:
	python scripts/seed_vaccines.py

lint:
	black --check app
	flake8 app
	mypy app

format:
	black app
	isort app

