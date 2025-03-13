### Style Guide

The project uses [ruff](https://docs.astral.sh/ruff/) for linting and  formatting.
Our style configurations are set in the `pyproject.toml` file.

We have a pre-commit hook to run the formatter before you commit, but Ruff can also be [integrated with most editors](https://docs.astral.sh/ruff/editors/setup/) to run automatically.

We recommend you also run the linter before pushing code. 

# Running the linter

We have Makefile commands to run common tasks (Note if you're on Windows you might need to install `make` first, or you can use ruff directly):

This outputs a report of any issues found:
```shell
make ruff-check
```

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

**Running directly with ruff**

Alternatively, you can run the commands directly with ruff.

Our rules are quite lenient for general usage, but if you want to explore more rigorous checks you can explore the [ruff documentation](https://docs.astral.sh/ruff/configuration/).
You can then run checks to see more nuanced errors which you can review manually.