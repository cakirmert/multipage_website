# Weathering Tools - pure-client tools

This folder is the production site for `tools.enhanced-weathering.de`. It is a
static rebuild of the Dash app in the repository root. Each page is plain
HTML/CSS/JS, with PHREEQC and carbonate system calculations running in the
visitor's browser through WebAssembly and JavaScript.

## Quick start

Do not open `index.html` directly from the filesystem. Browser security rules
block ES modules, `fetch`, and WASM over `file://`.

```sh
cd static
python -m http.server 8080
```

Open <http://localhost:8080>.

## Layout

```text
static/
|-- index.html
|-- pages/
|   |-- open-carbonate.html
|   |-- seawater.html
|   |-- charge-balance.html
|   |-- xrf.html
|   |-- mineral-dissolution.html
|   |-- forsterite-dissolution.html
|   |-- bjerrum.html
|   |-- dic-pco2.html
|   |-- impressum.html
|   |-- datenschutz.html
|   |-- barrierefreiheit.html
|   `-- credits.html
|-- js/
|   |-- common.js
|   |-- phreeqc.js
|   `-- co2sys.js
|-- driver/
|   |-- iphreeqc.mjs
|   |-- iphreeqc.wasm
|   `-- iphreeqc.data
|-- assets/
|   |-- data/
|   |-- markdown/
|   `-- *.jpg
`-- test/
```

## Legal and credit pages

The legal pages are static HTML so the privacy page can be read without loading
Markdown or formula-rendering scripts from a CDN.

Files:

- `pages/impressum.html`
- `pages/datenschutz.html`
- `pages/barrierefreiheit.html`
- `pages/credits.html`

Review contact details, hosting text, and accessibility status before the public
launch.

## GitHub Pages

Production deployment is handled by the root workflow
`.github/workflows/pages.yml`. It uploads `static/` directly through GitHub
Actions.

The repository setting should be:

1. Settings -> Pages.
2. Source: GitHub Actions.

Per-PR previews require a separate preview host or a switch to a `gh-pages`
branch publishing model, because GitHub Pages can only serve one source for this
repository at a time.

## Custom domain

The current custom domain is set by `CNAME`:

```text
tools.enhanced-weathering.de
```

The deployment workflow publishes that file to GitHub Pages. Keep the matching
custom domain configured in GitHub Pages settings and the DNS CNAME pointing at
`cakirmert.github.io`.

## Validation

Reference generators and validators are in `test/`.

```sh
cd static/test
python generate_reference.py
python generate_co2sys_reference.py
node validate_wasm.mjs
node validate_table.mjs
node validate_co2sys.mjs
```

The committed `driver/` folder is the runtime needed by the site. Rebuild
instructions for IPhreeqc/WebAssembly are in `BUILD.md`.
