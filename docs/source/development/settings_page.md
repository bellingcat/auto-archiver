# Settings Page

The settings page (viewable here TODO: add link), is an easy-to-use UI for users to edit their auto-archiver settings.

The single-file app is built using React and vite. To get started developing the package, follow these steps:

1. Make sure you have Node v22 installed.

```{note} Tip: if you don't have node installed:

Use `nvm` to manage your node installations. Use: 
`curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash` to install `nvm` and then `nvm i 22` to install Node v22
```

2. Generate the `schema.json` file for the currently installed modules using `python scripts/generate_settings_schema.py`
3. Go to the settings folder `cd scripts/settings/` and build your environment with `npm i`
4. Run a development version of the page with `npm run dev`
5. Build a release version of the page with `npm run build`

A release version creates a single-file app called `dist/index.html`