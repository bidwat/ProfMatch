.PHONY: setup db-init scrape-seed backend frontend test qa

setup:
	@echo "Python scraper package is ready; install optional extras (beautifulsoup4, pytest) if desired."

db-init:
	@echo "TODO: initialize SQLite schema at db/professor_match.sqlite"

scrape-seed:
	@python -m packages.scraper --adapter stanford --fixture packages/scraper/tests/fixtures/stanford_faculty_roster.html --output-root .

backend:
	cd apps/backend && venv/bin/uvicorn apps.backend.app.main:app --app-dir ../.. --reload --host 127.0.0.1 --port 8000

frontend-setup: apps/frontend/package.json apps/frontend/package-lock.json apps/frontend/node_modules/.package-lock.json
	cd apps/frontend && npm install

frontend: frontend-setup
	cd apps/frontend && npm run dev

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
