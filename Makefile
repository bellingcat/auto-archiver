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
	@echo "  make ruff-check   - Run Ruff linting and formatting checks (safe)"
	@echo "  make ruff-clean   - Auto-fix Ruff linting and formatting issues"
	@echo "  make docs         - Generate documentation (same as 'make html')"
	@echo "  make clean-docs   - Remove generated docs"
	@echo "  make docker-build - Build the Auto Archiver Docker image"
	@echo "  make docker-compose - Run Auto Archiver with Docker Compose"
	@echo "  make docker-compose-rebuild - Rebuild and run Auto Archiver with Docker Compose"
	@echo "  make show-docs    - Build and open the documentation in a browser"



.PHONY: test
test:
	@echo "Running tests..."
	@pytest tests --disable-warnings


.PHONY: ruff-check
ruff-check:
	@echo "Checking code style with Ruff (safe)..."
	@ruff check .


.PHONY: ruff-clean
ruff-clean:
	@echo "Fixing lint and formatting issues with Ruff..."
	@ruff check . --fix
	@ruff format .


.PHONY: docs
docs:
	@echo "Building documentation..."
	@$(SPHINXBUILD) -M html "$(SOURCEDIR)" "$(BUILDDIR)"


.PHONY: clean-docs
clean-docs:
	@echo "Cleaning up generated documentation files..."
	@$(SPHINXBUILD) -M clean "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
	@rm -rf "$(SOURCEDIR)/autoapi/" "$(SOURCEDIR)/modules/autogen/"
	@echo "Cleanup complete."


.PHONY: show-docs
show-docs:
	@echo "Opening documentation in browser..."
	@open "$(BUILDDIR)/html/index.html"

.PHONY: docker-build
docker-build:
	@echo "Building local Auto Archiver Docker image..."
	@docker compose build  # Uses the same build context as docker-compose.yml

.PHONY: docker-compose
docker-compose:
	@echo "Running Auto Archiver with Docker Compose..."
	@docker compose up

.PHONY: docker-compose-rebuild
docker-compose-rebuild:
	@echo "Rebuilding and running Auto Archiver with Docker Compose..."
	@docker compose up --build

# Catch-all for Sphinx commands
.PHONY: Makefile
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
