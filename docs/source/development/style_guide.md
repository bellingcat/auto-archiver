# Style Guide


## Ruff
The project uses [ruff](https://docs.astral.sh/ruff/) for linting and  formatting.
Our style configurations are set in the `pyproject.toml` file, and can be modified from there.

### Formatting

We have a pre-commit hook to run the formatter before you commit.
This requires you to set it up once locally, then it will run automatically when you commit changes.

```shell
poetry run pre-commit install
```

Ruff can also be [integrated with most editors](https://docs.astral.sh/ruff/editors/setup/) to run automatically.

### Linting

We recommend you also run the linter before pushing code. 

We have Makefile commands to run common tasks (Note if you're on Windows you might need to install `make` first, or alternatively you can use ruff commands directly):

This outputs a report of any issues found:
```shell
make ruff-check
```

To see a more detailed linting report, you can remove the following line from the `pyproject.toml` file:
```toml
[tool.ruff]

# Remove this for a more detailed lint report
output-format = "concise"
```

**Lint Fix**

This command will attempt to fix any issues it can:

⚠️ Warning: This can cause breaking changes. ⚠️

Ensure you check any modifications by this before committing them.
```shell
make ruff-fix
```

**Note:** If you're on Windows you might not have `make` installed by default.
This is included with [Git for Windows](https://gitforwindows.org/) or you can install make via [Chocolatey](https://chocolatey.org/):
```shell
choco install make
```

**Changing the configs**

Our rules are quite lenient for general usage, but if you want to explore more rigorous checks you can check out the [ruff documentation](https://docs.astral.sh/ruff/configuration/).
You can then run checks with additional rules to see more nuanced errors which you can review manually.
One example is to extend the selected rules for linting the `pyproject.toml` file:

```toml 
[tool.ruff.lint]
# Extend the rules to check for by adding them to this option:
# See documentation for more details: https://docs.astral.sh/ruff/rules/
extend-select = ["B"]
```

Then re-run the `make ruff-check` command to see the new rules in action.