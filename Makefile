.PHONY: dev api test fmt lint ui dev-ui tauri

dev: ## run backend dev server
	uvicorn context_cache.app:app --reload --port 5173

api: ## print OpenAPI spec JSON
	python -c "from context_cache.app import app; import json; print(app.openapi_json())"

test: ## run backend test suite
	pytest -q

fmt: ## format code with ruff
	ruff check --fix .

lint: ## lint codebase without fixing
	ruff check .

ui: ## install UI deps and build
	cd desktop/ui && npm install && npm run build

dev-ui: ## run UI dev server
	cd desktop/ui && npm install && npm run dev

tauri: ## run Tauri app in dev mode
	cd desktop && npm install && npm run tauri dev
