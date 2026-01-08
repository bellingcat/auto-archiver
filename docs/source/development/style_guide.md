# Style Guide


The project uses [Ruff](https://docs.astral.sh/ruff/) for linting and  formatting.
Our style configurations are set in the `pyproject.toml` file. If needed, you can modify them there.


### **Formatting (Auto-Run Before Commit) 🛠️**  

We have a pre-commit hook to run the formatter before you commit.
This requires you to set it up once locally, then it will run automatically when you commit changes.

```shell
poetry run pre-commit install
```

Ruff can also be to run automatically.
Alternative: Ruff can also be [integrated with most editors](https://docs.astral.sh/ruff/editors/setup/)  for real-time formatting.

If you wish to disable the pre-commit hook (for example, if you want to commit some WIP code) you can use the `--no-verify` flag when you commit.
For example: `git commit -m "WIP Code" --no-verify`

### **Linting (Check Before Pushing) 🔍**

We recommend you also run the linter before pushing code. 

We have [Makefile](../../../Makefile) commands to run common tasks. 

Tip: if you're on Windows you might need to install `make` first, or alternatively you can use ruff commands directly.


**Lint Check:** This outputs a report of any issues found, without attempting to fix them: 
```shell
make ruff-check
```

Tip: To see a more detailed linting report, you can remove the following line from the `pyproject.toml` file:
```toml
[tool.ruff]

# Remove this for a more detailed lint report
output-format = "concise"
```

**Lint Fix:** This command will attempt to fix some of the issues it picked up with the lint check.

Note not all warnings can be fixed automatically.

⚠️ Warning: This can cause breaking changes. ⚠️

Most fixes are safe, but some non-standard practices such as dynamic loading are not picked up by linters. Ensure you check any modifications by this before committing them.
```shell
make ruff-clean
```

**Changing Configurations ⚙️**


Our rules are quite lenient for general usage, but if you want to run more rigorous checks you can then run checks with additional rules to see more nuanced errors which you can review manually.
Check out the [ruff documentation](https://docs.astral.sh/ruff/configuration/) for the full list of rules.
One example is to extend the selected rules for linting the `pyproject.toml` file:

```toml 
[tool.ruff.lint]
# Extend the rules to check for by adding them to this option:
# See documentation for more details: https://docs.astral.sh/ruff/rules/
extend-select = ["B"]
```

Then re-run the `make ruff-check` command to see the new rules in action.
