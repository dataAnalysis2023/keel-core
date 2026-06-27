.PHONY: test test-all lint serve mcp install clean

# Tests rápidos (excluye MCP que requieren ~5 min)
test:
	pytest tests/ --ignore=tests/test_mcp.py -v --tb=short

# Suite completa incluyendo tests MCP
test-all:
	pytest tests/ -v --tb=short

# Lint con ruff
lint:
	ruff check src/ tests/

# Inicia el servidor REST en localhost:7331
serve:
	keel serve

# Inicia el servidor MCP (stdio)
mcp:
	keel mcp

# Instala en modo desarrollo
install:
	pip install -e ".[dev]"

# Elimina artefactos de build y cachés
clean:
	rm -rf dist/ build/ .pytest_cache/ __pycache__/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
