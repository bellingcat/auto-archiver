
# Developer Guidelines

This section of the documentation provides guidelines for developers who want to modify or contribute to the tool.


## Developer Install

1. Clone the project using `git clone https://github.com/bellingcat/auto-archiver.git` 
2. Install poetry using `curl -sSL https://install.python-poetry.org | python3 -` ([other installation methods](https://python-poetry.org/docs/#installation))
3. Install dependencies with `poetry install`

## Running 
4. Run the code with `poetry run auto-archiver [my args]`

```{note}
Add the plugin [poetry-shell-plugin](https://github.com/python-poetry/poetry-plugin-shell) and run `poetry shell` to activate the virtual environment.
This allows you to run the auto-archiver without the `poetry run` prefix.
```

### Optional Development Packages

Install development packages (used for unit tests etc.) using:
`poetry install --with dev`


```{toctree}
:hidden:
creating_modules
docker_development
testing
docs
release
settings_page
style_guide
```
