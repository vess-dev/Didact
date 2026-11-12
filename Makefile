# Didact developer tasks. `make check` must be green before any change is done.
unexport VIRTUAL_ENV
unexport DIDACT_LANG  # the skill's references and packs are English
UV := uv run --quiet

.PHONY: check fmt fmt-check lint types test sync skill packs docs i18n clean

check: fmt-check lint types test

fmt:
	$(UV) ruff format src tests tools
	$(UV) ruff check --fix src tests tools

fmt-check:
	$(UV) ruff format --check src tests tools

lint:
	$(UV) ruff check src tests tools

types:
	$(UV) mypy

test:
	$(UV) pytest

sync:
	uv sync --all-extras

skill:  # regenerate the Claude skill's references: the command list and the guides
	$(UV) didact commands > claude/skills/didact/references/commands.md
	cp src/didact/guides/*.md claude/skills/didact/references/

# the packs published in .gitignore (`!/packs/<id>/`), core aside: it's part of Didact
SHIPPED := $(filter-out core,$(patsubst !/packs/%/,%,$(filter !/packs/%/,$(shell cat .gitignore))))

packs:  # rebuild the .didactpack files of the packs that ship with Didact, from their folders
	rm -f packs/*.didactpack
	for pack in $(SHIPPED); do $(UV) didact pack export packs/$$pack --to packs || exit 1; done
	$(UV) python -c "from pathlib import Path; from didact.packs.share import write_catalog; write_catalog(Path('packs'))"

docs:  # the code's API documentation, from its docstrings and types (`didact docs build`)
	$(UV) didact docs build

i18n:  # after changing the browser app's words: the catalogs follow the code (tools/i18n.py)
	$(UV) python tools/i18n.py update

clean:  # developer caches and build output in this checkout; keeps .venv (your library's: `didact cache clear`)
	rm -rf .mypy_cache .ruff_cache .pytest_cache .hypothesis build dist
	find . -path ./.venv -prune -o -type d \( -name __pycache__ -o -name .build \) -prune -exec rm -rf {} +
	find . -path ./.venv -prune -o -name .DS_Store -type f -exec rm -f {} +
