SHELL := /usr/bin/env bash

.PHONY: setup scrape-seed backend backend-setup worker frontend frontend-setup frontend-test frontend-e2e test qa env-check

setup:
	@echo "Python scraper package is ready; install optional extras (beautifulsoup4, pytest) if desired."

scrape-seed:
	@python -m packages.scraper --adapter stanford --fixture packages/scraper/tests/fixtures/stanford_faculty_roster.html --output-root .

env-check: backend-setup
	@apps/backend/venv/bin/python -c "from dotenv import dotenv_values; c=dotenv_values('.env'); print('Firebase credentials found; backend will use Firestore.' if (c.get('FIREBASE_SERVICE_ACCOUNT_JSON') or c.get('GOOGLE_APPLICATION_CREDENTIALS') or '').strip() else 'No Firebase credentials found; backend will use the in-memory store (data resets on restart).')"

backend-setup: apps/backend/requirements.txt
	@if [[ ! -x apps/backend/venv/bin/python ]]; then \
		python3 -m venv apps/backend/venv; \
	fi
	@apps/backend/venv/bin/python -m pip install -r apps/backend/requirements.txt

backend: backend-setup
	@echo "Starting backend on http://127.0.0.1:8000"
	@echo "Environment is loaded by python-dotenv from .env; not shell-sourced, so passwords with special characters are safe."
	@PYTHONPATH=. apps/backend/venv/bin/uvicorn apps.backend.app.main:app --host 127.0.0.1 --port 8000 --reload

worker: backend-setup
	@echo "Starting durable scan worker"
	@PYTHONPATH=. apps/backend/venv/bin/python -m apps.backend.app.workers.scan_worker

frontend-setup: apps/frontend/package.json apps/frontend/package-lock.json
	@if [[ ! -d apps/frontend/node_modules ]]; then \
		cd apps/frontend && npm install; \
	fi

frontend: frontend-setup
	@echo "Starting frontend on http://localhost:3000 -> $${BACKEND_URL:-http://localhost:8000}"
	@cd apps/frontend && BACKEND_URL="$${BACKEND_URL:-http://localhost:8000}" npm run dev

frontend-test: frontend-setup
	cd apps/frontend && npm run test

frontend-e2e: frontend-setup
	cd apps/frontend && npx playwright install && npm run test:e2e

test:
	@python -m unittest discover packages/scraper/tests -v
	@apps/backend/venv/bin/python -m pytest apps/backend/tests -q

qa: frontend-setup
	@python -m unittest discover packages/scraper/tests -v
	@apps/backend/venv/bin/python -m pytest apps/backend/tests -q
	@cd apps/frontend && npm run test -- --runInBand
	@cd apps/frontend && npm run build
	@cd apps/frontend && npx playwright test
	@test -f docs/qa-reports/latest.md
	@echo "QA checks passed; update docs/qa-reports/latest.md with any new evidence before marking work done."
