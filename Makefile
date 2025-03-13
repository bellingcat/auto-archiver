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
	@echo "  make docker-run   - Run the Docker container"
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


# Run Docker with default settings
.PHONY: docker-run
docker-run:
	@echo "Running Auto Archiver Docker container..."
	@docker run --rm -v $PWD/secrets:/app/secrets -v $PWD/local_archive:/app/local_archive bellingcat/auto-archiver

# Catch-all for Sphinx commands
.PHONY: Makefile
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
