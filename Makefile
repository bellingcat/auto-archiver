# Variables
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = docs/source
BUILDDIR      = docs/_build

.PHONY: help
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
	@echo "Additional Commands:"
	@echo "  make test         - Run all tests in 'tests/' with pytest"
	@echo "  make lint         - Run ruff linter and auto-fix issues"
	@echo "  make docs         - Generate documentation (same as 'make html')"
	@echo "  make clean_docs   - Remove generated docs"
	@echo "  make docker-run   - Run the Docker container"

.PHONY: test
test:
	@echo "Running tests..."
	@pytest tests --disable-warnings

.PHONY: lint
lint:
	@echo "Linting with ruff..."
	@ruff check --fix .

.PHONY: docs
docs:
	@echo "Building documentation..."
	@$(SPHINXBUILD) -M html "$(SOURCEDIR)" "$(BUILDDIR)"

.PHONY: clean_docs
clean_docs:
	@echo "Cleaning up generated documentation files..."
	@$(SPHINXBUILD) -M clean "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
	@rm -rf "$(SOURCEDIR)/autoapi/" "$(SOURCEDIR)/modules/autogen/"
	@echo "Cleanup complete."


# Run Docker with default settings
.PHONY: docker-run
docker-run:
	@echo "Running Auto Archiver Docker container..."
	@docker run --rm -v $PWD/secrets:/app/secrets -v $PWD/local_archive:/app/local_archive bellingcat/auto-archiver

# Catch-all for Sphinx commands
.PHONY: Makefile
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
