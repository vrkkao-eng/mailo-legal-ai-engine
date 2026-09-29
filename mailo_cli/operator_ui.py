"""Minimal dependency-free operator UI for the RegAI workflow service."""

OPERATOR_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>MAILO RegAI Operator</title>
  <style>
    :root { font-family: Inter, system-ui, sans-serif; color-scheme: light dark; }
    body { margin: 0; background: Canvas; color: CanvasText; }
    header { padding: 22px 28px 14px; border-bottom: 1px solid color-mix(in srgb, CanvasText 18%, transparent); }
    h1 { margin: 0 0 6px; font-size: 24px; }
    header p { margin: 0; opacity: .72; }
    nav { display: flex; gap: 8px; padding: 14px 28px; border-bottom: 1px solid color-mix(in srgb, CanvasText 12%, transparent); }
    button { font: inherit; padding: 8px 12px; border: 1px solid color-mix(in srgb, CanvasText 24%, transparent); border-radius: 8px; background: Canvas; color: CanvasText; cursor: pointer; }
    button.active { font-weight: 700; }
    main { padding: 24px 28px 40px; max-width: 1200px; margin: auto; }
    .view { display: none; }
    .view.active { display: block; }
    .cards { display: grid; grid-template-columns: repeat(auto-fit,minmax(160px,1fr)); gap: 12px; margin: 0 0 18px; }
    .card { border: 1px solid color-mix(in srgb, CanvasText 16%, transparent); border-radius: 10px; padding: 14px; }
    .card strong { display: block; font-size: 22px; margin-top: 4px; }
    table { width: 100%; border-collapse: collapse; font-size: 14px; }
    th, td { padding: 10px 8px; border-bottom: 1px solid color-mix(in srgb, CanvasText 12%, transparent); text-align: left; vertical-align: top; }
    th { opacity: .72; }
    code { font-family: ui-monospace, monospace; font-size: 12px; }
    .status { font-weight: 700; text-transform: uppercase; font-size: 12px; }
    .trace { display: grid; gap: 10px; }
    .trace-item { border-left: 3px solid color-mix(in srgb, CanvasText 35%, transparent); padding: 8px 12px; }
    .muted { opacity: .66; }
    .toolbar { display: flex; gap: 8px; margin-bottom: 16px; }
    input { flex: 1; min-width: 200px; padding: 8px 10px; border: 1px solid color-mix(in srgb, CanvasText 24%, transparent); border-radius: 8px; background: Canvas; color: CanvasText; }
    .error { border: 1px solid currentColor; padding: 12px; border-radius: 8px; }
  </style>
</head>
<body>
<header>
  <h1>MAILO RegAI Operator</h1>
  <p>Operational views for regulatory changes, focused review work, and auditable case traces.</p>
</header>
<nav>
  <button data-view="changes" class="active">Regulatory Changes</button>
  <button data-view="reviews">Review Queue</button>
  <button data-view="trace">Case Trace</button>
</nav>
<main>
  <section id="changes" class="view active">
    <div id="change-cards" class="cards"></div>
    <table>
      <thead><tr><th>Change</th><th>Runs</th><th>Latest status</th><th>Failures</th><th>Latest run</th></tr></thead>
      <tbody id="changes-body"></tbody>
    </table>
  </section>

  <section id="reviews" class="view">
    <div id="review-cards" class="cards"></div>
    <table>
      <thead><tr><th>Status</th><th>Role</th><th>Subject</th><th>Change</th><th>Run</th></tr></thead>
      <tbody id="reviews-body"></tbody>
    </table>
  </section>

  <section id="trace" class="view">
    <div class="toolbar">
      <input id="trace-run-id" placeholder="workflow run id">
      <button id="trace-load">Load trace</button>
    </div>
    <div id="trace-content" class="trace muted">Select a run from another view or enter a workflow run ID.</div>
  </section>
</main>
<script>
const esc = (value) => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const show = (name) => {
  document.querySelectorAll(".view").forEach(v => v.classList.toggle("active", v.id === name));
  document.querySelectorAll("nav button").forEach(b => b.classList.toggle("active", b.dataset.view === name));
};
document.querySelectorAll("nav button").forEach(b => b.addEventListener("click", () => show(b.dataset.view)));

async function loadChanges() {
  const r = await fetch("/operator/api/changes");
  const rows = await r.json();
  const totalRuns = rows.reduce((n,x)=>n+x.run_count,0);
  const failures = rows.reduce((n,x)=>n+x.failed_run_count,0);
  document.getElementById("change-cards").innerHTML =
    '<div class="card">Changes<strong>' + rows.length + '</strong></div>' +
    '<div class="card">Workflow runs<strong>' + totalRuns + '</strong></div>' +
    '<div class="card">Failed runs<strong>' + failures + '</strong></div>';
  document.getElementById("changes-body").innerHTML = rows.map(x =>
    '<tr><td><code>' + esc(x.change_id) + '</code></td><td>' + x.run_count + '</td>' +
    '<td><span class="status">' + esc(x.latest_status) + '</span></td><td>' + x.failed_run_count + '</td>' +
    '<td><button onclick="openTrace(\'' + esc(x.latest_run_id) + '\')"><code>' + esc(x.latest_run_id) + '</code></button></td></tr>'
  ).join("");
}

async function loadReviews() {
  const r = await fetch("/operator/api/reviews");
  const rows = await r.json();
  const open = rows.filter(x => x.status === "open" || x.status === "in_review").length;
  const escalated = rows.filter(x => x.status === "escalated").length;
  document.getElementById("review-cards").innerHTML =
    '<div class="card">Review cases<strong>' + rows.length + '</strong></div>' +
    '<div class="card">Open / in review<strong>' + open + '</strong></div>' +
    '<div class="card">Escalated<strong>' + escalated + '</strong></div>';
  document.getElementById("reviews-body").innerHTML = rows.map(x =>
    '<tr><td><span class="status">' + esc(x.status) + '</span></td><td>' + esc(x.reviewer_role) + '</td>' +
    '<td>' + esc(x.subject_type) + '<br><code>' + esc(x.subject_id) + '</code></td><td><code>' + esc(x.change_id) + '</code></td>' +
    '<td><button onclick="openTrace(\'' + esc(x.run_id) + '\')"><code>' + esc(x.run_id) + '</code></button></td></tr>'
  ).join("");
}

async function openTrace(runId) {
  show("trace");
  document.getElementById("trace-run-id").value = runId;
  const target = document.getElementById("trace-content");
  target.className = "trace muted";
  target.textContent = "Loading…";
  const r = await fetch("/operator/api/cases/" + encodeURIComponent(runId));
  if (!r.ok) {
    target.className = "error";
    target.textContent = "Unable to load case trace (" + r.status + ").";
    return;
  }
  const x = await r.json();
  const run = x.run;
  const pieces = [
    '<div class="trace-item"><strong>Regulatory change</strong><br><code>' + esc(run.change_id) + '</code></div>',
    '<div class="trace-item"><strong>Workflow run</strong><br><code>' + esc(run.run_id) + '</code><br><span class="status">' + esc(run.status) + '</span></div>'
  ];
  x.steps.forEach(s => pieces.push(
    '<div class="trace-item"><strong>' + esc(s.step) + '</strong> — ' + esc(s.status) + ' · ' + Number(s.duration_ms).toFixed(2) + ' ms<br><span class="muted">' + esc(s.detail) + '</span></div>'
  ));
  x.reviews.forEach(v => pieces.push(
    '<div class="trace-item"><strong>Human review</strong> — ' + esc(v.status) + '<br>' + esc(v.reviewer_role) + ' · ' + esc(v.subject_type) + '<br><code>' + esc(v.subject_id) + '</code></div>'
  ));
  x.audit_events.forEach(a => pieces.push(
    '<div class="trace-item"><strong>Audit</strong> — ' + esc(a.event_type) + '<br><span class="muted">' + esc(a.actor_role) + ' · ' + esc(a.detail) + '</span></div>'
  ));
  if (run.failed_step) pieces.push(
    '<div class="trace-item"><strong>Failure</strong><br>' + esc(run.failed_step) + ' · ' + esc(run.error_code) + ' · retryable=' + esc(run.retryable) + '</div>'
  );
  pieces.push('<div class="trace-item"><strong>Compliance determination produced</strong><br>' + esc(x.compliance_determination_produced) + '</div>');
  target.className = "trace";
  target.innerHTML = pieces.join("");
}
document.getElementById("trace-load").addEventListener("click", () => openTrace(document.getElementById("trace-run-id").value.trim()));

Promise.all([loadChanges(), loadReviews()]).catch(() => {
  document.querySelector("main").insertAdjacentHTML("afterbegin", '<div class="error">Operator data could not be loaded.</div>');
});
</script>
</body>
</html>
"""
