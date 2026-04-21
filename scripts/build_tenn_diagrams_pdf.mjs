import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";

const REPO = "/home/l4nd0/tenn";
const OUT_HTML = path.join(REPO, "docs/architecture/_tenn_diagrams_booklet_build.html");
const OUT_PDF = path.join(REPO, "docs/architecture/tenn_diagrams_booklet.pdf");

const HTML_DIAGRAMS = [
  {
    title: "Interactive System Map (Claude-style, docs/tenn-system-map.html)",
    file: path.join(REPO, "docs/tenn-system-map.html"),
  },
  {
    title: "Frontend System Map (docs/architecture/tenn_system_map_frontend.html)",
    file: path.join(REPO, "docs/architecture/tenn_system_map_frontend.html"),
  },
];

const MD_SOURCES = [
  {
    title: "Full System Map Markdown (docs/architecture/tenn_full_system_map.md)",
    file: path.join(REPO, "docs/architecture/tenn_full_system_map.md"),
  },
  {
    title: "Claude System Map Markdown (docs/claude/architecture/system-map.md)",
    file: path.join(REPO, "docs/claude/architecture/system-map.md"),
  },
];

function escapeHtml(s) {
  return s
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function findChrome() {
  const candidates = [
    process.env.CHROME_PATH,
    "/usr/bin/google-chrome-stable",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
  ].filter(Boolean);
  for (const c of candidates) {
    try {
      fs.accessSync(c, fs.constants.X_OK);
      return c;
    } catch {
      /* continue */
    }
  }
  throw new Error(
    "No Chrome/Chromium binary found. Set CHROME_PATH to a chrome executable.",
  );
}

function buildHtml() {
  const mdBlocks = MD_SOURCES.map(({ title, file }) => {
    const text = fs.readFileSync(file, "utf8");
    return `
      <h2>${escapeHtml(title)}</h2>
      <div class="md"><pre>${escapeHtml(text)}</pre></div>`;
  }).join("\n");

  const frames = HTML_DIAGRAMS.map(({ title, file }) => {
    const url = `file://${file}`;
    return `
      <h2>${escapeHtml(title)}</h2>
      <iframe class="frame" src="${escapeHtml(url)}" title="${escapeHtml(title)}"></iframe>`;
  }).join("\n");

  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Tenn Diagram Booklet</title>
<style>
  :root { --bg:#0b1020; --panel:#121a30; --ink:#e8eefc; --muted:#afbddf; --line:#2d3b66; }
  * { box-sizing: border-box; }
  body { margin:0; font-family:Segoe UI, system-ui, sans-serif; background:var(--bg); color:var(--ink); line-height:1.45; }
  .wrap { max-width: 1200px; margin: 0 auto; padding: 24px; }
  h1, h2 { margin: 0 0 10px; }
  h1 { font-size: 26px; }
  h2 { font-size: 17px; margin-top: 22px; border-top: 1px solid var(--line); padding-top: 16px; }
  .meta { color: var(--muted); border: 1px solid var(--line); border-radius: 10px; padding: 10px 12px; background: var(--panel); margin-bottom: 8px; }
  .frame { margin-top: 8px; width: 100%; height: 900px; border: 1px solid var(--line); border-radius: 10px; background: #0a1022; }
  .md { margin-top: 8px; border: 1px solid var(--line); border-radius: 10px; background: var(--panel); padding: 12px; }
  pre { margin: 0; white-space: pre-wrap; word-break: break-word; font-size: 11.5px; color: #dfe7ff; }
  @media print {
    .frame { break-inside: avoid; page-break-inside: avoid; height: 1000px; }
    h2 { break-after: avoid; }
  }
</style>
</head>
<body>
<div class="wrap">
  <h1>Tenn Diagram Booklet</h1>
  <div class="meta">Single PDF export: interactive HTML diagrams + markdown system maps (Codex + Claude).</div>
  ${frames}
  ${mdBlocks}
</div>
</body>
</html>`;
}

fs.writeFileSync(OUT_HTML, buildHtml(), "utf8");

const chrome = findChrome();
execFileSync(
  chrome,
  [
    "--headless=new",
    "--disable-gpu",
    "--no-pdf-header-footer",
    "--allow-file-access-from-files",
    `--print-to-pdf=${OUT_PDF}`,
    `file://${OUT_HTML}`,
  ],
  { stdio: "inherit" },
);

console.log(OUT_PDF);
