PYTHON ?= python3.11
VENV ?= .venv
ACTIVATE = . $(VENV)/bin/activate

.PHONY: setup lint format typecheck test run docker-build docker-run

setup:
	$(PYTHON) -m venv $(VENV)
	$(ACTIVATE) && pip install --upgrade pip
	$(ACTIVATE) && pip install -r requirements.txt
	$(ACTIVATE) && pre-commit install

lint:
	$(ACTIVATE) && ruff check .

format:
	$(ACTIVATE) && black .

typecheck:
	$(ACTIVATE) && mypy src

test:
	$(ACTIVATE) && pytest -q

run:
	$(ACTIVATE) && python -m obsidian_remote_mcp.server

docker-build:
	docker build -t obsidian-remote-mcp .

docker-run:
	docker run --rm -p 8000:8000 --env-file .env -v $$(pwd)/vaults:/vaults obsidian-remote-mcp
