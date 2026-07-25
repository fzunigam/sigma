.PHONY: help install web dev api test lint check app clean

help:
	@echo "make install   Instalar dependencias de Python y de la interfaz"
	@echo "make web       Compilar la interfaz"
	@echo "make dev       Abrir la aplicación (compila la interfaz si falta)"
	@echo "make api       Solo el backend, para trabajar con 'npm run dev'"
	@echo "make test      Ejecutar los tests"
	@echo "make lint      Revisar el estilo del código"
	@echo "make check     lint + test"
	@echo "make app       Construir dist/Sigma.app"
	@echo "make clean     Borrar artefactos de compilación"

install:
	python3.12 -m pip install -e ".[dev]"
	cd web && npm install

web:
	cd web && npm run build

dev:
	@[ -f src/sigma/web/static/index.html ] || $(MAKE) web
	python3.12 -m sigma.main

api:
	python3.12 -c "import uvicorn; uvicorn.run('sigma.api:app', host='127.0.0.1', port=8765, reload=True)"

test:
	python3.12 -m pytest -q

lint:
	python3.12 -m ruff check .
	cd web && npx tsc --noEmit

check: lint test

app:
	bash scripts/build_macos_app.sh

clean:
	rm -rf build dist src/sigma/web/static .pytest_cache .ruff_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
