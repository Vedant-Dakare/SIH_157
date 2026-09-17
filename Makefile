.PHONY: scaffold seed-demo test lint typecheck coverage build-ui dev-ui

scaffold:
	bash scripts/scaffold.sh

seed-demo:
	python -m satsa.cli seed-demo

test:
	pytest tests -v --tb=short

lint:
	ruff check server/src tests

typecheck:
	mypy server/src

coverage:
	coverage run -m pytest tests -q
	coverage report --include="src/satsa/ingest/*,src/satsa/canonical/*" --fail-under=90

build-ui:
	cd client && npm run build

dev-ui:
	cd client && npm run dev
