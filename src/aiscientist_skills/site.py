"""Static, searchable catalog page built from catalog.json (deployed to GitHub Pages)."""

from __future__ import annotations

import html
import json
from pathlib import Path

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AiScientist Skills</title>
<meta name="description" content="Tested, reproducible agent skills for scientific data analysis.">
<meta name="color-scheme" content="light dark">
<style>
:root {{
  --bg:#fafaf9; --fg:#1c1917; --muted:#78716c; --card:#fff; --line:#e7e5e4; --accent:#0f766e;
  --accent-soft:#ccfbf1; --code:#f5f5f4;
  --core:#15803d; --core-bg:#dcfce7; --verified:#1d4ed8; --verified-bg:#dbeafe;
  --community:#57534e; --community-bg:#f5f5f4;
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --bg:#0c0a09; --fg:#f5f5f4; --muted:#a8a29e; --card:#1c1917; --line:#292524; --accent:#2dd4bf;
    --accent-soft:#134e4a; --code:#292524;
    --core:#86efac; --core-bg:#14532d; --verified:#93c5fd; --verified-bg:#1e3a8a;
    --community:#d6d3d1; --community-bg:#292524;
  }}
}}
* {{ box-sizing: border-box; }}
html {{ scroll-behavior: smooth; }}
body {{ margin:0; background:var(--bg); color:var(--fg);
  font:15px/1.55 ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
  -webkit-font-smoothing: antialiased; }}
a {{ color:var(--accent); }}
code, kbd, .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
main {{ max-width: 1000px; margin: 0 auto; padding: 48px 16px 64px; }}
header {{ margin-bottom: 28px; }}
.eyebrow {{ color:var(--accent); font-size:12px; font-weight:600; letter-spacing:.08em;
  text-transform:uppercase; margin:0 0 8px; }}
h1 {{ margin:0 0 6px; font-size: 34px; line-height:1.15; letter-spacing: -0.025em; }}
.lede {{ color:var(--muted); margin:0 0 20px; font-size:17px; max-width: 60ch; }}
.stats {{ display:flex; gap:24px; flex-wrap:wrap; margin:0 0 24px; padding:0; list-style:none; }}
.stats li {{ display:flex; flex-direction:column; }}
.stats b {{ font-size:22px; letter-spacing:-0.02em; }}
.stats span {{ color:var(--muted); font-size:13px; }}
.install {{ display:flex; align-items:center; gap:10px; background:var(--code);
  border:1px solid var(--line); border-radius:10px; padding:10px 14px; font-size:13px;
  overflow-x:auto; white-space:nowrap; }}
.install code {{ flex:1; }}
.copy {{ font:inherit; color:var(--fg); background:var(--card); border:1px solid var(--line);
  border-radius:6px; padding:3px 10px; cursor:pointer; flex:none; }}
.copy:hover {{ border-color:var(--accent); }}
.bar {{ position:sticky; top:0; z-index:1; display:flex; gap:8px; flex-wrap:wrap; padding:12px 0;
  margin-bottom:16px; background:var(--bg); border-bottom:1px solid var(--line); }}
input, select {{ font:inherit; color:inherit; background:var(--card); border:1px solid var(--line);
  border-radius:8px; padding:8px 12px; }}
input:focus, select:focus {{ outline:2px solid var(--accent); outline-offset:1px; }}
input {{ flex:1; min-width: 200px; }}
.hint {{ color:var(--muted); font-size:13px; margin:0 0 12px; }}
.hint kbd {{ border:1px solid var(--line); border-radius:4px; padding:0 5px; font-size:12px; }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:18px 20px;
  margin-bottom:12px; }}
.card header {{ display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin:0 0 6px; }}
.card h2 {{ margin:0; font-size:16px; }}
.card h2 a {{ text-decoration:none; }}
.card h2 a:hover {{ text-decoration:underline; }}
.pill {{ display:inline-block; font-size:12px; font-weight:600; border-radius:999px; padding:2px 10px;
  line-height:1.5; }}
.pill.core {{ color:var(--core); background:var(--core-bg); }}
.pill.verified {{ color:var(--verified); background:var(--verified-bg); }}
.pill.community {{ color:var(--community); background:var(--community-bg); }}
.version {{ color:var(--muted); font-size:13px; }}
.meta {{ color:var(--muted); font-size:13px; margin:0 0 10px; }}
.card p {{ margin:0 0 10px; }}
.req {{ display:flex; gap:6px; flex-wrap:wrap; margin:0 0 10px; }}
.req span {{ font-size:12px; color:var(--muted); background:var(--code); border-radius:6px;
  padding:2px 8px; }}
.tag {{ display:inline-block; font-size:12px; border:1px solid var(--line); border-radius:999px;
  padding:1px 8px; margin:0 4px 4px 0; color:var(--muted); cursor:pointer; }}
.tag:hover {{ border-color:var(--accent); color:var(--accent); }}
.card .install {{ margin-top:10px; }}
.empty {{ color:var(--muted); padding:32px 0; text-align:center; }}
footer {{ color:var(--muted); font-size:13px; margin-top:40px; padding-top:16px;
  border-top:1px solid var(--line); }}
footer a {{ color:inherit; }}
@media (max-width: 600px) {{ h1 {{ font-size:28px; }} .stats {{ gap:16px; }} }}
</style>
</head>
<body>
<main>
<header>
  <p class="eyebrow">Skill registry</p>
  <h1>AiScientist Skills</h1>
  <p class="lede">Tested, reproducible agent skills for scientific data analysis. Each skill packages one
  analysis method: setup, commands, parameter choices and the checks that show the result can be trusted.</p>
  <ul class="stats">
    <li><b>{count}</b><span>skills</span></li>
    <li><b>{n_categories}</b><span>categories</span></li>
    <li><b>{n_core}</b><span>core</span></li>
    <li><b>{n_verified}</b><span>verified</span></li>
    <li><b>v{version}</b><span>registry</span></li>
  </ul>
  <div class="install"><code>/plugin marketplace add {slug}</code>
    <button class="copy" data-copy="/plugin marketplace add {slug}">Copy</button></div>
</header>
<div class="bar">
  <input id="q" type="search" placeholder="Search skills, tools, tags…" aria-label="Search">
  <select id="cat" aria-label="Category"><option value="">All categories</option>{cat_options}</select>
  <select id="status" aria-label="Status"><option value="">Any status</option>
    <option>core</option><option>verified</option><option>community</option></select>
</div>
<p class="hint" id="hint">Press <kbd>/</kbd> to search.</p>
<div id="list"></div>
<footer>Generated from <a href="catalog.json">catalog.json</a> ·
<a href="{repo}">Source on GitHub</a> · <a href="{repo}/releases/latest">Latest release</a> ·
<a href="{repo}/blob/main/CONTRIBUTING.md">Contribute a skill</a></footer>
</main>
<script>
const DATA = {data};
const REPO = {repo_json};
const MARKET = {marketplace_json};
const esc = s => String(s).replace(/[&<>"]/g, c => ({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}})[c]);
const $ = id => document.getElementById(id);
function reqs(r) {{
  const out = [];
  if (r.compute) out.push(esc(r.compute));
  if (r.gpu) out.push("GPU");
  if (r.scheduler && r.scheduler !== "none") out.push("Slurm " + esc(r.scheduler));
  if (r.network && r.network !== "none") out.push("network: " + esc(r.network));
  if (r.secrets && r.secrets.length) out.push("secrets: " + esc(r.secrets.join(", ")));
  return out.length ? `<div class="req">${{out.map(x => `<span>${{x}}</span>`).join("")}}</div>` : "";
}}
function render() {{
  const q = $("q").value.toLowerCase().trim();
  const cat = $("cat").value, st = $("status").value;
  const hits = DATA.skills.filter(s =>
    (!cat || s.category === cat) && (!st || s.status === st) &&
    (!q || [s.name, s.description, s.category, s.tags.join(" "), s.tested_with, s.author]
      .join(" ").toLowerCase().includes(q)));
  $("hint").textContent = `${{hits.length}} of ${{DATA.skills.length}} skills` + (q || cat || st ? "" : ". Press / to search.");
  $("list").innerHTML = hits.length ? hits.map(s => `
    <article class="card">
      <header>
        <h2 class="mono"><a href="${{REPO}}/tree/main/${{esc(s.path)}}">${{esc(s.name)}}</a></h2>
        <span class="pill ${{esc(s.status)}}">${{esc(s.status)}}</span>
        <span class="version">v${{esc(s.version)}}</span>
      </header>
      <div class="meta">${{esc(s.category)}}${{s.tested_with ? " · tested with " + esc(s.tested_with) : ""}}${{s.author ? " · " + esc(s.author) : ""}}</div>
      <p>${{esc(s.description)}}</p>
      ${{reqs(s.requirements)}}
      <div>${{s.tags.map(t => `<span class="tag" data-tag="${{esc(t)}}">${{esc(t)}}</span>`).join("")}}</div>
      <div class="install"><code>/plugin install ${{esc(s.category)}}@${{esc(MARKET)}}</code>
        <button class="copy" data-copy="/plugin install ${{esc(s.category)}}@${{esc(MARKET)}}">Copy</button></div>
    </article>`).join("") : '<p class="empty">No skills match. Try a tool name, assay or tag.</p>';
}}
for (const id of ["q", "cat", "status"]) $(id).addEventListener("input", render);
document.addEventListener("click", e => {{
  const copy = e.target.closest(".copy");
  if (copy && navigator.clipboard) {{
    navigator.clipboard.writeText(copy.dataset.copy).then(() => {{
      copy.textContent = "Copied"; setTimeout(() => copy.textContent = "Copy", 1200);
    }});
  }}
  const tag = e.target.closest(".tag");
  if (tag) {{ $("q").value = tag.dataset.tag; render(); }}
}});
document.addEventListener("keydown", e => {{
  if (e.key === "/" && document.activeElement !== $("q")) {{ e.preventDefault(); $("q").focus(); }}
  if (e.key === "Escape" && document.activeElement === $("q")) {{ $("q").value = ""; render(); }}
}});
render();
</script>
</body>
</html>
"""


def build_site(catalog: dict, out: Path, repo: str) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    cats = "".join(
        f'<option value="{html.escape(c["name"])}">{html.escape(c["name"])}</option>'
        for c in catalog["categories"]
    )
    skills = catalog["skills"]
    slug = repo.removeprefix("https://github.com/")  # for `/plugin marketplace add`
    marketplace = catalog["registry"]  # for `/plugin install <plugin>@<marketplace>`
    data = json.dumps(catalog, ensure_ascii=False).replace("</", "<\\/")
    page = PAGE.format(
        count=len(skills),
        n_categories=len(catalog["categories"]),
        n_core=sum(s["status"] == "core" for s in skills),
        n_verified=sum(s["status"] == "verified" for s in skills),
        version=html.escape(catalog.get("registry_version", "")),
        cat_options=cats,
        data=data,
        repo=html.escape(repo),
        repo_json=json.dumps(repo),
        slug=html.escape(slug),
        marketplace=html.escape(marketplace),
        marketplace_json=json.dumps(marketplace),
    )
    (out / "index.html").write_text(page, encoding="utf-8")
    (out / "catalog.json").write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    return out / "index.html"
