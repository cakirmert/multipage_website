# GitHub Pages Launch Plan

Goal: make the client-side geochemistry tools easy for Lukas to publish, review,
and maintain as the main public repository if he wants that.

## Recommended repository setup

Use Lukas's repository as the upstream source of truth and keep this repo as the
working fork until he is comfortable with the static version.

Reasons this can become the main repo:

- The site is now pure static HTML/CSS/JS, so GitHub Pages can host it without a
  Python server or paid app platform.
- Pull requests can get live previews later if Pages is switched to a `gh-pages`
  branch publishing model or a preview host is added.
- Production deploys are automatic from `main`, `master`, or `client-side-port`.
- All scientific source files, static assets, WebAssembly runtime files, and
  validation scripts stay in one repository.
- The credit page keeps authorship clear without taking project ownership away
  from Lukas.

The current production setting is Pages -> Source -> GitHub Actions. Keep this
setting while `tools.enhanced-weathering.de` is deployed by
`.github/workflows/pages.yml`.

If PR previews become more important than the GitHub Actions setup, switch Pages
to Source -> Deploy from a branch -> `gh-pages` -> `/ (root)` and add a preview
workflow that publishes PR folders under `/previews/pr-<number>/`.

## Project name

Use **Weathering Tools** as the public tool-suite name. It fits
`tools.enhanced-weathering.de`, keeps the tools attached to Lukas's existing
site, and is broad enough for carbonate chemistry, PHREEQC speciation, mineral
dissolution, and XRF helper workflows.

## Domain ideas

Check availability and renewal price before buying. Avoid domains that are cheap
for year one but expensive to renew.

If a separate redirect domain is still useful later, check:

- `weatheringlab.org`
- `weatheringlab.science`
- `weathering-tools.org`
- `carbonateweathering.org`

For now, the best domain is already available as a subdomain:
`tools.enhanced-weathering.de`. A separate domain can redirect there later.

## Custom domain steps

After buying the domain:

1. Add the domain in GitHub repository Settings -> Pages -> Custom domain.
2. Add DNS records at the registrar according to GitHub's Pages instructions.
3. Keep `static/CNAME` set to:

   ```text
   tools.enhanced-weathering.de
   ```

4. Wait for DNS and HTTPS provisioning.
5. Check the legal pages and privacy page with the final domain and hosting
   details.

## Message to Lukas

Suggested wording:

> I moved the tools into Weathering Tools at tools.enhanced-weathering.de, a pure
> client-side GitHub Pages version that can run without a server and can show
> live previews for pull requests. I kept the credit page explicit: the
> scientific direction and project choices are yours; my part is the
> implementation, cleanup, earlier PR work, and the static hosting setup. If you
> like it, this repo can become the main tool repo. If not, it can stay as a
> preview branch/fork linked from the main Enhanced Weathering website.
