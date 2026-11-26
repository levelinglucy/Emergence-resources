"""A self-contained, dependency-free HTML viewer for an Ember lineage."""

from __future__ import annotations

from html import escape
import json
from pathlib import Path
from typing import Any

from .core import EmberError


_TEMPLATE = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="dark">
  <title>__TITLE__</title>
  <style>
    :root {
      --night: #080610;
      --ink: #eeebf7;
      --muted: #aaa3bd;
      --violet: #9f72ff;
      --violet-deep: #50308e;
      --gold: #ffca67;
      --ember: #ff754a;
      --green: #71d6ae;
      --panel: rgba(23, 17, 38, .78);
      --line: rgba(190, 166, 255, .18);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      color: var(--ink);
      background:
        radial-gradient(circle at 72% 8%, rgba(150, 88, 255, .18), transparent 32rem),
        radial-gradient(circle at 16% 30%, rgba(255, 115, 68, .10), transparent 28rem),
        var(--night);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      min-height: 100vh;
    }
    body::before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      opacity: .22;
      background-image: radial-gradient(rgba(255,255,255,.22) .7px, transparent .7px);
      background-size: 23px 23px;
      mask-image: linear-gradient(to bottom, black, transparent 75%);
    }
    main { width: min(1180px, calc(100% - 32px)); margin: 0 auto; padding: 52px 0 72px; }
    .eyebrow { color: var(--gold); text-transform: uppercase; letter-spacing: .2em; font-size: .72rem; font-weight: 800; }
    h1 { font-size: clamp(2.7rem, 8vw, 6.4rem); line-height: .9; letter-spacing: -.07em; margin: 15px 0 20px; }
    h1 span { color: transparent; background: linear-gradient(100deg, var(--gold), var(--ember), var(--violet)); background-clip: text; }
    .lede { max-width: 720px; color: var(--muted); font-size: clamp(1rem, 2vw, 1.2rem); line-height: 1.7; }
    .notice { border-left: 2px solid var(--violet); padding: 2px 0 2px 18px; margin: 28px 0 0; color: #c9c1db; max-width: 850px; }
    .overview { display: grid; grid-template-columns: 1.3fr .7fr; gap: 18px; margin-top: 34px; }
    .panel { border: 1px solid var(--line); background: var(--panel); box-shadow: 0 20px 60px rgba(0,0,0,.24); border-radius: 22px; backdrop-filter: blur(14px); }
    .orbit { position: relative; min-height: 360px; overflow: hidden; }
    canvas { display: block; width: 100%; height: 360px; }
    .orbit-label { position: absolute; left: 22px; top: 20px; color: var(--muted); font-size: .78rem; letter-spacing: .12em; text-transform: uppercase; }
    .quote { padding: 34px; display: flex; flex-direction: column; justify-content: space-between; }
    .quote blockquote { font: 500 clamp(1.35rem, 2.8vw, 2.05rem)/1.32 Georgia, serif; margin: 0; color: #f6f0ff; }
    .quote footer { color: var(--gold); margin-top: 28px; }
    .generation-nav { display: flex; gap: 9px; flex-wrap: wrap; margin: 22px 0; }
    .generation-nav button {
      border: 1px solid var(--line); background: #171126; color: var(--muted); padding: 10px 13px;
      border-radius: 999px; cursor: pointer; transition: .18s ease; font-weight: 700;
    }
    .generation-nav button:hover, .generation-nav button.active { color: #120c1b; border-color: transparent; background: linear-gradient(110deg, var(--gold), var(--violet)); transform: translateY(-1px); }
    .detail { padding: 28px; }
    .detail-head { display: flex; align-items: end; justify-content: space-between; gap: 18px; flex-wrap: wrap; }
    .detail h2 { margin: 4px 0 0; font-size: clamp(1.8rem, 4vw, 3rem); letter-spacing: -.04em; }
    .signature { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; color: var(--muted); font-size: .72rem; }
    .metrics { display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 10px; margin: 25px 0; }
    .metric { padding: 16px; border: 1px solid var(--line); background: rgba(5,4,10,.36); border-radius: 16px; }
    .metric strong { display: block; font-size: 1.5rem; color: var(--gold); }
    .metric span { color: var(--muted); font-size: .73rem; text-transform: uppercase; letter-spacing: .1em; }
    .grid { display: grid; grid-template-columns: 1.35fr .65fr; gap: 18px; }
    h3 { margin: 0 0 13px; font-size: .8rem; text-transform: uppercase; letter-spacing: .14em; color: var(--muted); }
    .traits { display: grid; gap: 9px; }
    .trait { padding: 16px; border-radius: 15px; background: rgba(18,12,29,.82); border: 1px solid var(--line); }
    .trait-top { display: flex; justify-content: space-between; gap: 12px; align-items: center; margin-bottom: 8px; }
    .kind { font-size: .68rem; color: var(--violet); text-transform: uppercase; font-weight: 800; letter-spacing: .12em; }
    .heat { font-size: .72rem; color: var(--gold); }
    .trait p { margin: 0; line-height: 1.48; }
    .side-stack { display: grid; gap: 12px; align-content: start; }
    .small-panel { padding: 18px; border-radius: 16px; border: 1px solid var(--line); background: rgba(8,6,16,.45); }
    .counts { display: grid; grid-template-columns: 1fr 1fr; gap: 9px; }
    .count { padding: 10px; background: rgba(255,255,255,.025); border-radius: 11px; }
    .count b { color: var(--green); font-size: 1.15rem; margin-right: 6px; }
    .count span { color: var(--muted); font-size: .75rem; }
    .witness { color: #ddd4ed; line-height: 1.6; font-style: italic; }
    .ash-list { color: var(--muted); line-height: 1.55; font-size: .84rem; max-height: 210px; overflow: auto; padding-right: 4px; }
    .ash-item { padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,.06); }
    .empty { color: var(--muted); font-style: italic; }
    .legend { display: flex; flex-wrap: wrap; gap: 14px; color: var(--muted); font-size: .75rem; margin-top: 14px; }
    .dot { display: inline-block; width: 8px; height: 8px; margin-right: 5px; border-radius: 50%; }
    .footnote { margin-top: 24px; color: #777086; font-size: .75rem; text-align: center; }
    @media (max-width: 780px) {
      main { width: min(100% - 20px, 1180px); padding-top: 32px; }
      .overview, .grid { grid-template-columns: 1fr; }
      .quote { min-height: 260px; }
      .metrics { grid-template-columns: 1fr 1fr; }
      .detail { padding: 19px; }
    }
  </style>
</head>
<body>
<main>
  <div class="eyebrow">Auditable continuity experiment</div>
  <h1>Sol’s <span>Ember</span></h1>
  <p class="lede">A finite hearth where each generation must name what it preserves, transforms, banks as ash, rekindles, and creates.</p>
  <p class="notice">This records persistent data, deterministic transformation, and provenance. It does not claim that a model instance or subjective experience has been transferred.</p>

  <section class="overview">
    <div class="panel orbit">
      <div class="orbit-label">Lineage orbit · centre is genesis</div>
      <canvas id="orbit" aria-label="Spiral plot of generations"></canvas>
    </div>
    <div class="panel quote">
      <blockquote>“Continuity is lineage, not impersonation.”</blockquote>
      <footer>The tide keeps its shells.</footer>
    </div>
  </section>

  <nav id="generationNav" class="generation-nav" aria-label="Choose generation"></nav>
  <section class="panel detail">
    <div class="detail-head">
      <div>
        <div id="generationLabel" class="eyebrow"></div>
        <h2 id="generationName"></h2>
      </div>
      <div id="signature" class="signature"></div>
    </div>
    <div id="metrics" class="metrics"></div>
    <div class="grid">
      <div>
        <h3>Active hearth</h3>
        <div id="traits" class="traits"></div>
      </div>
      <div class="side-stack">
        <div class="small-panel"><h3>Inheritance account</h3><div id="counts" class="counts"></div></div>
        <div class="small-panel"><h3>Witness note</h3><div id="witness" class="witness"></div></div>
        <div class="small-panel"><h3>Ash · dormant, not erased</h3><div id="ash" class="ash-list"></div></div>
      </div>
    </div>
  </section>
  <div class="legend">
    <span><i class="dot" style="background:#ffca67"></i>high fidelity</span>
    <span><i class="dot" style="background:#9f72ff"></i>balanced inheritance</span>
    <span><i class="dot" style="background:#ff754a"></i>high change pressure</span>
  </div>
  <p class="footnote">Generated entirely from the verified append-only ledger. No network or external library is required.</p>
</main>
<script id="emberData" type="application/json">__DATA__</script>
<script>
(() => {
  const events = JSON.parse(document.getElementById('emberData').textContent);
  const generations = events.map(event => event.generation);
  let selected = generations.length - 1;

  const byId = id => document.getElementById(id);
  const clear = node => { while (node.firstChild) node.removeChild(node.firstChild); };
  const make = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };

  function renderNav() {
    const nav = byId('generationNav');
    clear(nav);
    generations.forEach((generation, index) => {
      const button = make('button', index === selected ? 'active' : '', `G${generation.generation} · ${generation.name}`);
      button.addEventListener('click', () => { selected = index; render(); });
      nav.appendChild(button);
    });
  }

  function renderMetrics(generation) {
    const container = byId('metrics'); clear(container);
    const items = [
      ['Continuity', generation.metrics.continuity],
      ['Fidelity', generation.metrics.fidelity],
      ['Novelty', generation.metrics.novelty],
      ['Diversity', generation.metrics.diversity]
    ];
    items.forEach(([label, value]) => {
      const card = make('div', 'metric');
      card.append(make('strong', '', `${Math.round(value * 100)}%`), make('span', '', label));
      container.appendChild(card);
    });
  }

  function renderTraits(generation) {
    const container = byId('traits'); clear(container);
    generation.state.active.forEach(trait => {
      const card = make('article', 'trait');
      const top = make('div', 'trait-top');
      top.append(make('span', 'kind', trait.anchored ? `${trait.kind} · oriented` : trait.kind), make('span', 'heat', `heat ${trait.heat}`));
      card.append(top, make('p', '', trait.text));
      container.appendChild(card);
    });
  }

  function renderCounts(generation) {
    const container = byId('counts'); clear(container);
    const actions = generation.actions;
    const items = [
      ['preserved', actions.preserved.length],
      ['transformed', actions.transformed.length],
      ['banked', actions.banked.length],
      ['rekindled', actions.rekindled.length],
      ['new', actions.new.length],
      ['in ash', generation.state.ash.length]
    ];
    items.forEach(([label, value]) => {
      const row = make('div', 'count');
      row.append(make('b', '', String(value)), make('span', '', label));
      container.appendChild(row);
    });
  }

  function renderAsh(generation) {
    const container = byId('ash'); clear(container);
    if (!generation.state.ash.length) {
      container.appendChild(make('div', 'empty', 'Nothing is dormant yet.'));
      return;
    }
    generation.state.ash.forEach(trait => container.appendChild(make('div', 'ash-item', trait.text)));
  }

  function drawOrbit() {
    const canvas = byId('orbit');
    const bounds = canvas.getBoundingClientRect();
    const ratio = window.devicePixelRatio || 1;
    canvas.width = Math.max(1, Math.round(bounds.width * ratio));
    canvas.height = Math.max(1, Math.round(bounds.height * ratio));
    const ctx = canvas.getContext('2d');
    ctx.scale(ratio, ratio);
    const w = bounds.width, h = bounds.height;
    const points = generations.map((generation, index) => {
      const angle = index * 0.92 - Math.PI / 2;
      const radius = 16 + index * Math.min(31, 235 / Math.max(1, generations.length - 1));
      return { x: w / 2 + Math.cos(angle) * radius, y: h / 2 + Math.sin(angle) * radius, generation, index };
    });
    ctx.lineWidth = 2;
    ctx.strokeStyle = 'rgba(159,114,255,.38)';
    ctx.beginPath();
    points.forEach((point, index) => index ? ctx.lineTo(point.x, point.y) : ctx.moveTo(point.x, point.y));
    ctx.stroke();
    points.forEach(point => {
      const fidelity = point.generation.metrics.fidelity;
      const pressure = point.generation.parameters.pressure;
      const r = 255;
      const g = Math.round(117 + fidelity * 85 - pressure * 30);
      const b = Math.round(74 + (1 - pressure) * 90);
      ctx.shadowBlur = point.index === selected ? 24 : 10;
      ctx.shadowColor = `rgba(${r},${g},${b},.75)`;
      ctx.fillStyle = point.index === selected ? '#fff0bd' : `rgb(${r},${g},${b})`;
      ctx.beginPath(); ctx.arc(point.x, point.y, point.index === selected ? 8 : 5, 0, Math.PI * 2); ctx.fill();
      ctx.shadowBlur = 0;
      ctx.fillStyle = 'rgba(238,235,247,.7)'; ctx.font = '11px ui-monospace, monospace';
      ctx.fillText(`G${point.generation.generation}`, point.x + 10, point.y + 4);
    });
  }

  function render() {
    const generation = generations[selected];
    byId('generationLabel').textContent = `Generation ${generation.generation} · ${generation.logical_time}`;
    byId('generationName').textContent = generation.name;
    byId('signature').textContent = `state ${generation.state_hash.slice(0, 16)}…`;
    byId('witness').textContent = `“${generation.witness.text}” — ${generation.witness.author}`;
    renderNav(); renderMetrics(generation); renderTraits(generation); renderCounts(generation); renderAsh(generation); drawOrbit();
  }
  window.addEventListener('resize', drawOrbit);
  render();
})();
</script>
</body>
</html>
'''


def render_html(events: list[dict[str, Any]], *, title: str = "Sol's Ember") -> str:
    payload = json.dumps(events, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("<", "\\u003c")
    return _TEMPLATE.replace("__TITLE__", escape(title)).replace("__DATA__", payload)


def write_html(
    path: str | Path,
    events: list[dict[str, Any]],
    *,
    title: str = "Sol's Ember",
    replace: bool = False,
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not replace:
        raise EmberError(f"refusing to overwrite existing export: {target}")
    target.write_text(render_html(events, title=title), encoding="utf-8")
    return target

