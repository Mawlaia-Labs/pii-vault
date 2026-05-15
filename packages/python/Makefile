.PHONY: install spacy test lint fmt

install:
	pip install -e ".[all]"

spacy:
	python -m spacy download en_core_web_sm

test:
	pytest tests/ -v

lint:
	ruff check pii_vault/

fmt:
	black pii_vault/ tests/
