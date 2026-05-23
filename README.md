# Weathering Tools

Interactive geochemistry calculators for enhanced-weathering research,
carbonate chemistry, charge-balance checking, mineral dissolution, Bjerrum
plots, and XRF oxide conversion.

The current deployable site lives in [`static/`](static/) and is intended for
`tools.enhanced-weathering.de`. It is a pure
client-side port: HTML, CSS, JavaScript, JSON assets, and a WebAssembly PHREEQC
runtime. No Python server is needed for production hosting.

## Run locally

ES modules, `fetch`, and WebAssembly need HTTP, so serve the `static/` folder:

```sh
cd static
python -m http.server 8080
```

Open <http://localhost:8080>.

## Deployment

GitHub Pages deployment is configured in `.github/workflows/pages.yml`.

The current repository setting should be:

1. Open GitHub repository settings.
2. Go to **Pages**.
3. Set **Source** to **GitHub Actions**.

After that, every push to `main`, `master`, or `client-side-port` publishes the
contents of `static/` to GitHub Pages.

## Pull-request previews

GitHub Pages has one active publishing source per repository. The current
GitHub Actions setup is the simplest way to keep `tools.enhanced-weathering.de`
updated. Per-PR previews can be added later by switching Pages to a `gh-pages`
branch publishing model, or by adding a preview host such as Cloudflare Pages or
Vercel.

## Credits

Project credit is shown on the site in
[`static/pages/credits.html`](static/pages/credits.html). In short: Lukas Rieder
owns the main scientific direction, content choices, and project curation; Mert
Cakir contributed structure, app implementation work, performance/stability
fixes, the pure client-side port, and the GitHub Pages/preview setup reflected
in the repository history.

## More details

See [`static/README.md`](static/README.md) for the static app layout,
validation commands, and WebAssembly runtime notes.
