# Configuration Editor

The [configuration editor](../installation/config_editor.md), is an easy-to-use UI for users to edit their auto-archiver settings.

The single-file app is built using React and vite. To get started developing the package, follow these steps:

1. Make sure you have Node v22 installed.

```{note} Tip: if you don't have node installed:

Use `nvm` to manage your node installations. Use: 
`curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash` to install `nvm` and then `nvm i 22` to install Node v22
```

2. Generate the `schema.json` file for the currently installed modules using `python scripts/generate_settings_schema.py`
3. Go to the settings folder `cd scripts/settings/` and build your environment with `npm i`
4. Run a development version of the page with `npm run dev` and then open localhost:5173.
5. Build a release version of the page with `npm run build`

A release version creates a single-file app called `dist/index.html`. This file should be copied to `docs/source/installation/settings_base.html` so that it can be integrated into the sphinx docs.

```{note}

The single-file app dist/index.html does not include any `<html>` or `<head>` tags as it is designed to be built into a RTD docs page. Edit `index.html` in the settings folder if you wish to modify the built page.
```

## Readthedocs Integration

The configuration editor is built as part of the RTD deployment (see `.readthedocs.yaml` file). This command is run every time RTD is built:

`cd scripts/settings && npm install && npm run build && yes | cp dist/index.html ../../docs/source/installation/settings_base.html && cd ../..`