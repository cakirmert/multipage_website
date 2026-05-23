// Shared header/footer, breadcrumbs, and global styling for every page.
// Pages call setupChrome({ title, crumbs }) once on load.

const STYLE = `
:root {
    --green:    #149c7d;
    --dark:     #0d7359;
    --gray-50:  #f9fafb;
    --gray-100: #f3f4f6;
    --gray-200: #e5e7eb;
    --gray-300: #d1d5db;
    --gray-700: #374151;
    --gray-900: #111827;
    --red:      #dc2626;
    --red-bg:   #fee2e2;
    --green-bg: #dcfce7;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
    color: var(--gray-900);
    background: #fff;
    line-height: 1.5;
}
header.site {
    border-bottom: 1px solid var(--gray-200);
    padding: .85rem 1rem;
    background: #fff;
}
header.site .inner {
    max-width: 1160px; margin: 0 auto;
    display: flex; align-items: center; justify-content: space-between; gap: 1.5rem;
}
header.site .site-nav {
    display: flex; align-items: center; gap: .9rem; flex-wrap: wrap;
    font-size: .9rem; font-weight: 600;
}
header.site .site-nav a {
    color: var(--gray-700); text-decoration: none;
}
header.site .site-nav a:hover {
    color: var(--green); text-decoration: underline;
}
header.site .crumbs {
    font-size: .9rem; color: var(--gray-700);
    flex: 1;
    min-width: 12rem;
    text-align: left;
}
header.site .crumbs a { color: var(--green); text-decoration: none; }
header.site .crumbs a:hover { text-decoration: underline; }
@media (max-width: 720px) {
    header.site .inner {
        align-items: flex-start;
        flex-direction: column;
        gap: .75rem;
    }
    header.site .crumbs {
        text-align: left;
    }
}
main {
    max-width: 1160px; margin: 0 auto; padding: 2rem 1rem 4rem;
}
h1 { font-size: 1.75rem; margin: 0 0 .5rem; }
h2 { font-size: 1.3rem; margin: 1.5rem 0 .5rem; }
h3 { font-size: 1.05rem; margin: 1rem 0 .5rem; }
p  { margin: .5rem 0; }
.card {
    background: #fff; border: 1px solid var(--gray-200);
    border-radius: .75rem; padding: 1.25rem;
    box-shadow: 0 1px 2px rgba(0,0,0,.04);
    margin-bottom: 1rem;
}
.row { display: flex; gap: 1rem; flex-wrap: wrap; align-items: flex-end; }
label.field {
    display: flex; flex-direction: column;
    font-size: .85rem; color: var(--gray-700);
    min-width: 9rem;
}
label.field input, label.field select {
    margin-top: .25rem; padding: .45rem .55rem;
    font-size: 1rem; border: 1px solid var(--gray-300);
    border-radius: .375rem; background: #fff;
}
button {
    padding: .45rem 1rem;
    font-size: 1rem; font-weight: 500;
    background: var(--green); color: #fff;
    border: 0; border-radius: .375rem; cursor: pointer;
}
button:hover { background: var(--dark); }
button.secondary { background: var(--gray-200); color: var(--gray-900); }
button.secondary:hover { background: var(--gray-300); }
.status {
    display: inline-block;
    font-family: ui-monospace, monospace; font-size: .85rem;
    padding: .35rem .65rem; border-radius: .375rem;
    background: var(--gray-100); color: var(--gray-700);
}
.status.ok  { background: var(--green-bg); color: #064e3b; }
.status.err { background: var(--red-bg);   color: #7f1d1d; }
table.dt {
    width: 100%; border-collapse: collapse;
    font-size: .9rem;
}
table.dt th, table.dt td {
    border: 1px solid var(--gray-200);
    padding: .35rem .55rem;
    text-align: right;
}
table.dt th {
    background: var(--gray-50); font-weight: 600;
}
table.dt td.label, table.dt th:first-child {
    text-align: left;
}
table.dt tr:nth-child(even) td { background: var(--gray-50); }
.danger { background: #fecaca !important; }
.warning { background: #fef3c7 !important; }
.tabs {
    display: flex; gap: .5rem; margin-bottom: 1rem;
    border-bottom: 1px solid var(--gray-200);
}
.tab {
    padding: .6rem 1.2rem; cursor: pointer;
    border: 1px solid transparent; border-bottom: none;
    border-radius: .5rem .5rem 0 0;
    background: transparent; color: var(--gray-700);
    font-weight: 500; font-size: 1rem;
}
.tab.active { background: var(--green); color: #fff; }
.tab:not(.active):hover { background: var(--gray-100); }
.tab-panel { display: none; }
.tab-panel.active { display: block; }
html, body { height: 100%; }
body { display: flex; flex-direction: column; min-height: 100vh; }
main { flex: 1 0 auto; }
footer.site {
    background: rgba(8,24,38,.58); color: #fff;
    padding: 1rem; text-align: center;
    margin-top: auto;
    flex-shrink: 0;
    border-top: 1px solid rgba(255,255,255,.14);
    backdrop-filter: blur(10px);
}
footer.site a { color: #fff; margin: 0 .8rem; text-decoration: none; }
footer.site a:hover { text-decoration: underline; }
.summary-pills span {
    display: inline-block;
    background: var(--gray-100); padding: .35rem .75rem;
    margin: .25rem .5rem .25rem 0; border-radius: 1rem;
    font-family: ui-monospace, monospace; font-size: .9rem;
}
.summary-pills span b { color: var(--dark); }
.note {
    font-size: .85rem; color: var(--gray-700);
    border-left: 3px solid var(--gray-300);
    padding: .25rem 0 .25rem .75rem; margin: .75rem 0;
}
.legal-page {
    max-width: 860px;
}
.legal-page section {
    border-top: 1px solid var(--gray-200);
    padding-top: 1rem;
    margin-top: 1.5rem;
}
.legal-page address {
    font-style: normal;
    white-space: pre-line;
}
.legal-page ul {
    padding-left: 1.25rem;
}
.legal-page .meta {
    color: var(--gray-700);
    font-size: .9rem;
}
.credit-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 1rem;
}
.credit-list {
    margin: .75rem 0 0;
}
.credit-list li {
    margin-bottom: .45rem;
}
.callout {
    border-left: 4px solid var(--green);
    background: var(--gray-50);
    padding: .9rem 1rem;
    margin: 1rem 0;
}
`;

/**
 * Render header + footer once, with the given title and breadcrumb chain.
 * crumbs: array of [label, href] pairs. Last entry is the current page.
 */
export function setupChrome({ title = "", crumbs = [] } = {}) {
    if (!document.getElementById("site-style")) {
        const s = document.createElement("style");
        s.id = "site-style";
        s.textContent = STYLE;
        document.head.appendChild(s);
    }
    if (title) {
        document.title = title === "Weathering Tools" ? title : title + " - Weathering Tools";
    }

    const crumbsHtml = crumbs.map((c, i) => {
        const [label, href] = c;
        const last = i === crumbs.length - 1;
        return last ? `<span>${label}</span>` : `<a href="${href}">${label}</a> &gt;`;
    }).join(" ");
    const inSubpage = location.pathname.includes("/pages/");
    const homeHref = inSubpage ? "../index.html" : "./index.html";
    const pagesBase = inSubpage ? "../pages/" : "./pages/";

    const header = document.createElement("header");
    header.className = "site";
    header.innerHTML = `
        <div class="inner">
            ${crumbsHtml ? `<nav class="crumbs" aria-label="Breadcrumb">${crumbsHtml}</nav>` : ""}
            <nav class="site-nav" aria-label="Site">
                <a href="${homeHref}">Tools</a>
                <a href="https://enhanced-weathering.de/">Main site</a>
            </nav>
        </div>
    `;
    document.body.prepend(header);

    const footer = document.createElement("footer");
    footer.className = "site";
    footer.innerHTML = `
        <a href="https://enhanced-weathering.de/">Enhanced Weathering</a>
        <a href="${pagesBase}impressum.html">Impressum</a>
        <a href="${pagesBase}datenschutz.html">Datenschutz</a>
        <a href="${pagesBase}barrierefreiheit.html">Barrierefreiheit</a>
        <a href="${pagesBase}credits.html">Credits</a>
    `;
    document.body.append(footer);
}

/** Minimal tab controller: clicking .tab switches .tab-panel by data-panel attr. */
export function setupTabs(container = document) {
    const tabs = container.querySelectorAll(".tab");
    tabs.forEach(t => {
        t.addEventListener("click", () => {
            const panel = t.dataset.panel;
            container.querySelectorAll(".tab").forEach(x => x.classList.toggle("active", x === t));
            container.querySelectorAll(".tab-panel").forEach(p => {
                p.classList.toggle("active", p.dataset.panel === panel);
            });
        });
    });
}

/**
 * Fetch a markdown file, render with marked.js, and run KaTeX auto-render on
 * the result so $...$ / $$...$$ become typeset equations. Loads marked + KaTeX
 * from CDN on first call only.
 */
let _mdReady = null;
async function ensureMdLoaded() {
    if (_mdReady) return _mdReady;
    _mdReady = (async () => {
        // KaTeX CSS
        if (!document.querySelector('link[data-katex]')) {
            const l = document.createElement("link");
            l.rel = "stylesheet";
            l.href = "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css";
            l.dataset.katex = "1";
            document.head.appendChild(l);
        }
        // marked + KaTeX + auto-render via dynamic <script> tags
        async function loadScript(src) {
            return new Promise((res, rej) => {
                const s = document.createElement("script");
                s.src = src; s.async = true;
                s.onload = res; s.onerror = () => rej(new Error("failed " + src));
                document.head.appendChild(s);
            });
        }
        if (!window.marked) await loadScript("https://cdn.jsdelivr.net/npm/marked/marked.min.js");
        if (!window.katex)  await loadScript("https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js");
        if (!window.renderMathInElement) await loadScript("https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js");
    })();
    return _mdReady;
}

export async function renderMarkdownInto(target, mdSource) {
    await ensureMdLoaded();
    const el = typeof target === "string" ? document.querySelector(target) : target;
    if (!el) return;
    el.innerHTML = window.marked.parse(mdSource);
    window.renderMathInElement(el, {
        delimiters: [
            { left: "$$", right: "$$", display: true },
            { left: "$",  right: "$",  display: false },
            { left: "\\(", right: "\\)", display: false },
            { left: "\\[", right: "\\]", display: true },
        ],
        throwOnError: false,
    });
}

/** Convenience: fetch then render. */
export async function renderMarkdownUrl(url, target) {
    const md = await (await fetch(url)).text();
    await renderMarkdownInto(target, md);
}

/**
 * Build a simple HTML table from an array of {col: value} rows.
 * cols: array of {key, label, fmt?: (v)=>string, condClass?: (v, row)=>string|null}
 */
export function makeTable(rows, cols) {
    const head = "<thead><tr>" + cols.map(c => `<th>${c.label}</th>`).join("") + "</tr></thead>";
    const body = "<tbody>" + rows.map(row =>
        "<tr>" + cols.map(c => {
            const v = row[c.key];
            const text = c.fmt ? c.fmt(v, row) : (v ?? "");
            const cls  = c.condClass ? (c.condClass(v, row) || "") : "";
            return `<td class="${cls}">${text}</td>`;
        }).join("") + "</tr>"
    ).join("") + "</tbody>";
    return `<table class="dt">${head}${body}</table>`;
}
