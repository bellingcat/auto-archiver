
### Building the Docs

The documentation is built using [Sphinx](https://www.sphinx-doc.org/en/master/) and [AutoAPI](https://sphinx-autoapi.readthedocs.io/en/latest/) and hosted on ReadTheDocs.
To build the documentation locally, run the following commands:

**Install required dependencies:**
- Install the docs group of dependencies: 
```shell
# only the docs dependencies
poetry install --only docs

# or for all dependencies 
poetry install
```
- Either use [poetry-plugin-shell](https://github.com/python-poetry/poetry-plugin-shell) to activate the virtual environment: `poetry shell`
- Or prepend the following commands with `poetry run`

**Create the documentation:**
- Build the documentation: 
```shell
# Using makefile (Linux/macOS):
make -C docs html

# or using sphinx directly (Windows/Linux/macOS):
sphinx-build -b html docs/source docs/_build/html
```
- If you make significant changes and want a fresh build run: `make -C docs clean` to remove the old build files.

**Viewing the documentation:**
```shell
# to open the documentation in your browser.
open docs/_build/html/index.html

# or run autobuild to automatically update the documentation when you make changes
sphinx-autobuild docs/source docs/_build/html
```

