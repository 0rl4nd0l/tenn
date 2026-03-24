#!/usr/bin/env python3
"""
Bug Monitor Web UI
==================
Reads .claude/monitors/alerts.log and presents a dashboard with:
  - All detected bugs/issues grouped by type and severity
  - Per-bug explanation panel
  - Agent debate (two fix proposals + synthesised recommendation)
  - "Deploy Fix" button that applies the winning proposal via git patch

Run:
  /home/l4nd0/tenn/financial-engine_v2/.venv/bin/python .claude/monitors/bug_web_ui.py
  Open: http://localhost:8765
"""

import hashlib, json, os, re, shutil, socketserver, subprocess, textwrap, threading, time, uuid
from pathlib import Path
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler

# ── Paths ─────────────────────────────────────────────────────────────────────
REPO_ROOT  = Path(__file__).resolve().parents[2]
LOG_FILE   = Path(__file__).parent / "alerts.log"
DEBATES_DB = Path(__file__).parent / "debates.json"
PORT       = 8765

JOBS: dict[str, dict] = {}
_JOBS_LOCK = threading.Lock()
_DEBATES_LOCK = threading.Lock()


def _load_json_safe(path) -> dict | None:
    """Return parsed JSON dict from path, or None on any error."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


# ── Debate/fix knowledge base (pre-loaded for confirmed bugs) ─────────────────
KNOWN_FIXES = {
    "uuid-serialization-crash": {
        "title": "UUID Serialization Crash in pipeline_service.py",
        "file": "financial-engine_v2/backend/app/services/pipeline_service.py",
        "severity": "critical",
        "type": "BUGS",
        "explanation": (
            "The errors list built inside run_pipeline_sync() stores raw Python UUID objects "
            "as the 'document_id' field (lines 89, 98, 104). Celery is configured with "
            "task_serializer='json' (celery_app.py:53) and worker_tasks.py returns the "
            "PipelineResult directly from the task. When Celery serialises the result to JSON "
            "for storage in the Redis result backend, json.dumps() raises:\n\n"
            "  TypeError: Object of type UUID is not JSON serializable\n\n"
            "This crash only manifests in TASK_MODE=celery (production). The sync path "
            "(local dev) is unaffected. resume_pending_downloads.py correctly uses "
            "str(row.document_id) — this fix brings pipeline_service.py in line."
        ),
        "agent_a": {
            "name": "Agent A — Minimal Fix",
            "approach": "Wrap each document_id reference in str() at the three error-append sites. "
                        "Smallest possible diff, zero risk of side effects.",
            "diff": textwrap.dedent("""\
                --- a/financial-engine_v2/backend/app/services/pipeline_service.py
                +++ b/financial-engine_v2/backend/app/services/pipeline_service.py
                @@ -86,7 +86,7 @@
                             except Exception as exc:
                -                errors.append({"document_id": document_id, "stage": "download", "error": str(exc)})
                +                errors.append({"document_id": str(document_id), "stage": "download", "error": str(exc)})
                                 continue
                @@ -95,7 +95,7 @@
                                 errors.append({
                -                    "document_id": document_id,
                +                    "document_id": str(document_id),
                @@ -101,7 +101,7 @@
                             except Exception as exc:
                -                errors.append({"document_id": document_id, "stage": "process_document", "error": str(exc)})
                +                errors.append({"document_id": str(document_id), "stage": "process_document", "error": str(exc)})
            """),
        },
        "agent_b": {
            "name": "Agent B — Comprehensive Fix",
            "approach": "Extract a _make_error_entry() helper that always stringifies document_id, "
                        "ensuring any future error-append site is automatically safe. "
                        "Adds ~5 lines but makes the pattern impossible to get wrong.",
            "diff": textwrap.dedent("""\
                --- a/financial-engine_v2/backend/app/services/pipeline_service.py
                +++ b/financial-engine_v2/backend/app/services/pipeline_service.py
                @@ -79,6 +79,12 @@
                +        def _err(stage: str, exc_or_msg: str, **extra) -> dict:
                +            return {"document_id": str(document_id), "stage": stage,
                +                    "error": exc_or_msg, **extra}
                +
                         for document_id in doc_ids:
                             try:
                                 pipeline_core.download_pdf_for_document(db, document_id)
                             except Exception as exc:
                -                errors.append({"document_id": document_id, "stage": "download", "error": str(exc)})
                +                errors.append(_err("download", str(exc)))
                                 continue
                             ...
                -                errors.append({"document_id": document_id, "stage": "process_document",
                -                               "error": "extraction_failed", ...})
                +                errors.append(_err("process_document", "extraction_failed",
                +                                   extraction_status=proc_result.get("extraction_status")))
                             except Exception as exc:
                -                errors.append({"document_id": document_id, "stage": "process_document", "error": str(exc)})
                +                errors.append(_err("process_document", str(exc)))
            """),
        },
        "verdict": "Agent A wins. The helper in Agent B adds conceptual overhead for a 3-site fix. "
                   "str() at point of use is idiomatic Python and matches the pattern already used "
                   "in resume_pending_downloads.py. No abstraction needed for 3 identical one-liners.",
        "winning_agent": "a",
        "status": "open",
    },
    "extraction-failed-count-undercount": {
        "title": "extraction_failed_count Not Incremented on Exception Path",
        "file": "financial-engine_v2/backend/app/services/pipeline_service.py",
        "severity": "critical",
        "type": "BUGS",
        "explanation": (
            "In run_pipeline_sync(), the inner try/except for process_document() at line 103 "
            "appends to errors[] when an exception is raised but does NOT increment "
            "extraction_failed_count. Because processed was already incremented at line 91 "
            "(after a successful download), the formula:\n\n"
            "  processed_ok_count = processed - extraction_failed_count\n\n"
            "overcounts successful documents. Any document where process_document() throws "
            "(network timeout, LLM error, DB write failure) is silently counted as 'ok' "
            "instead of failed. This causes the quality gate in update_ticker_financials.py "
            "to also undercount extraction failures."
        ),
        "agent_a": {
            "name": "Agent A — Minimal Fix",
            "approach": "Add extraction_failed_count += 1 inside the except block. One line.",
            "diff": textwrap.dedent("""\
                --- a/financial-engine_v2/backend/app/services/pipeline_service.py
                +++ b/financial-engine_v2/backend/app/services/pipeline_service.py
                @@ -102,6 +102,7 @@
                             except Exception as exc:
                +                extraction_failed_count += 1
                                 errors.append({"document_id": str(document_id),
                                                "stage": "process_document", "error": str(exc)})
            """),
        },
        "agent_b": {
            "name": "Agent B — Comprehensive Fix",
            "approach": "Unify both failure paths (status='failed' and exception) into one counter "
                        "increment site by restructuring the if/except into a helper that always "
                        "returns (failed: bool, error_dict). Clearer invariant but larger diff.",
            "diff": textwrap.dedent("""\
                --- a/financial-engine_v2/backend/app/services/pipeline_service.py
                +++ b/financial-engine_v2/backend/app/services/pipeline_service.py
                @@ -92,18 +92,20 @@
                             if bool(spec.process_documents):
                -                try:
                -                    proc_result = pipeline_core.process_document(document_id) or {}
                -                    if (proc_result.get("extraction_status") or "").strip().lower() == "failed":
                -                        extraction_failed_count += 1
                -                        errors.append({...})
                -                except Exception as exc:
                -                    errors.append({...})
                +                failed, err = _run_process(pipeline_core, document_id)
                +                if failed:
                +                    extraction_failed_count += 1
                +                    errors.append(err)
                (where _run_process() wraps both paths and always returns a bool)
            """),
        },
        "verdict": "Agent A wins decisively. One line insertion is the correct fix. "
                   "Agent B's refactor changes control flow unnecessarily and introduces "
                   "a new helper function for a single-site fix. CLAUDE.md explicitly "
                   "prohibits unrelated refactors bundled with fixes.",
        "winning_agent": "a",
        "status": "open",
    },
    "ingestion-metrics-always-empty": {
        "title": "ingestion_metrics Always {} — 4 PipelineResult Fields Always 0",
        "file": "financial-engine_v2/backend/app/services/pipeline_service.py",
        "severity": "critical",
        "type": "REGRESSION",
        "explanation": (
            "The refactor in dc0f4a6b replaced pipeline_core._download_and_process_document_ids() "
            "which returned a populated ingestion_metrics dict, with a manual loop that "
            "initialises ingestion_metrics = {} and never populates it.\n\n"
            "PipelineResult fields now always report 0:\n"
            "  chunks_created, chunks_skipped, invalid_payloads, written_points\n\n"
            "These are read by the API, by Celery result inspection, and by monitoring scripts. "
            "Downstream dashboards and alerts that rely on these metrics receive silent zeros."
        ),
        "agent_a": {
            "name": "Agent A — Restore from pipeline_core",
            "approach": "After the loop, call pipeline_core.get_ingestion_metrics(doc_ids) "
                        "or equivalent to retrieve the real metrics. Requires checking what "
                        "pipeline_core exposes publicly.",
            "diff": "Requires reading pipeline_core.py to determine the correct public API. "
                    "Click 'Deploy Fix Agent' to have an agent investigate and propose the exact patch.",
        },
        "agent_b": {
            "name": "Agent B — Accumulate in loop",
            "approach": "Have each process_document() call return ingestion metrics and accumulate "
                        "them in the loop. Requires process_document() to return chunk counts.",
            "diff": "Requires reading process_document() return contract. "
                    "Click 'Deploy Fix Agent' to have an agent investigate and propose the exact patch.",
        },
        "verdict": "Needs investigation — the correct fix depends on what pipeline_core "
                   "exposes publicly after the refactor. Deploy a fix agent to determine the approach.",
        "winning_agent": None,
        "status": "open",
    },
    "github-action-unpinned": {
        "title": "claude-code-action@beta Pins to Mutable Tag",
        "file": ".github/workflows/claude.yml",
        "severity": "warning",
        "type": "SECURITY",
        "explanation": (
            "The workflow uses:\n  uses: anthropics/claude-code-action@beta\n\n"
            "The 'beta' tag is mutable — the action author can push new code to it at any time. "
            "If this happens maliciously or accidentally, the new code runs with:\n"
            "  - ANTHROPIC_API_KEY (from secrets)\n"
            "  - contents: write permission on the repository\n\n"
            "GitHub's own security hardening guide recommends pinning to a full commit SHA "
            "for any action that has elevated permissions. This is a supply-chain risk."
        ),
        "agent_a": {
            "name": "Agent A — Pin to SHA",
            "approach": "Resolve the current SHA of anthropics/claude-code-action@beta and pin to it. "
                        "Add a comment with the tag name for human readability.",
            "diff": textwrap.dedent("""\
                --- a/.github/workflows/claude.yml
                +++ b/.github/workflows/claude.yml
                @@ -23,7 +23,7 @@
                -      - uses: anthropics/claude-code-action@beta
                +      - uses: anthropics/claude-code-action@<SHA>  # beta
                @@ -35,7 +35,7 @@
                -      - uses: anthropics/claude-code-action@beta
                +      - uses: anthropics/claude-code-action@<SHA>  # beta
                (SHA to be resolved at deploy time via: gh api repos/anthropics/claude-code-action/git/ref/heads/beta)
            """),
        },
        "agent_b": {
            "name": "Agent B — Use Dependabot",
            "approach": "Add a .github/dependabot.yml to auto-update pinned action SHAs on a schedule. "
                        "More maintenance-friendly long-term.",
            "diff": textwrap.dedent("""\
                +++ b/.github/dependabot.yml (new file)
                +version: 2
                +updates:
                +  - package-ecosystem: github-actions
                +    directory: /
                +    schedule:
                +      interval: weekly
            """),
        },
        "verdict": "Both. Pin the SHA immediately (Agent A) and add Dependabot (Agent B) "
                   "to keep it updated automatically. The two fixes are complementary.",
        "winning_agent": "both",
        "status": "open",
    },
}

# ── Log parser ────────────────────────────────────────────────────────────────
def parse_alerts():
    if not LOG_FILE.exists():
        return []
    alerts = []
    current = None
    with open(LOG_FILE) as f:
        for line in f:
            line = line.rstrip()
            m = re.match(r'\[(.+?)\] \[(\w+)\] (severity=(\w+)|ok)\s+\((.+?)\)', line)
            if m:
                if current:
                    alerts.append(current)
                ts, agent, sev_full, severity, sha = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
                current = {
                    "timestamp": ts,
                    "agent": agent,
                    "severity": severity or "ok",
                    "sha": sha,
                    "issues": [],
                    "raw": line,
                }
            elif line.startswith("  ⚠") and current:
                issue_m = re.match(r'\s+⚠\s+(.+?) @ (.+?): (.+)', line)
                if issue_m:
                    issue_dict = {
                        "type": issue_m.group(1),
                        "location": issue_m.group(2),
                        "detail": issue_m.group(3),
                    }
                    current["issues"].append(issue_dict)
                    if len(current["issues"]) == 1:  # stable id, set once on first issue
                        current["id"] = hashlib.sha1(
                            f"{current['agent']}:{issue_dict['type']}:{issue_dict['location']}:{issue_dict['detail']}".encode()
                        ).hexdigest()
    if current:
        alerts.append(current)
    return alerts


def get_open_issues():
    """Return only alerts with actual issues (non-ok severity)."""
    seen = set()
    open_issues = []
    for alert in reversed(parse_alerts()):
        if alert["issues"]:
            for issue in alert["issues"]:
                key = f"{alert['agent']}:{issue['type']}:{issue['location']}"
                if key not in seen:
                    seen.add(key)
                    open_issues.append({**alert, "issues": [issue]})
    return open_issues


def match_known_fix(alert):
    for fix_id, fix in KNOWN_FIXES.items():
        if fix["type"] == alert["agent"] and fix["severity"] == alert["severity"]:
            if alert["issues"]:
                issue = alert["issues"][0]
                if (issue["location"].split(":")[0].split("/")[-1] in fix["file"] or
                    fix["file"].split("/")[-1] in issue["location"]):
                    return fix_id, fix
    return None, None

# ── HTML template ─────────────────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bug Monitor Dashboard</title>
<style>
:root {
  --bg: #0d1117; --surface: #161b22; --border: #30363d;
  --text: #e6edf3; --muted: #8b949e; --accent: #58a6ff;
  --critical: #f85149; --warning: #e3b341; --ok: #3fb950;
  --code-bg: #1c2128;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); color: var(--text); font: 14px/1.6 'Segoe UI', system-ui, sans-serif; }
header { padding: 20px 32px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 16px; }
header h1 { font-size: 18px; font-weight: 600; }
.badge { padding: 2px 10px; border-radius: 20px; font-size: 12px; font-weight: 600; }
.badge.critical { background: rgba(248,81,73,.15); color: var(--critical); border: 1px solid rgba(248,81,73,.4); }
.badge.warning { background: rgba(227,179,65,.15); color: var(--warning); border: 1px solid rgba(227,179,65,.4); }
.badge.ok { background: rgba(63,185,80,.15); color: var(--ok); border: 1px solid rgba(63,185,80,.4); }
.badge.info { background: rgba(88,166,255,.15); color: var(--accent); border: 1px solid rgba(88,166,255,.4); }
main { max-width: 1200px; margin: 0 auto; padding: 32px; }
.summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; margin-bottom: 32px; }
.summary-card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 20px; text-align: center; }
.summary-card .count { font-size: 36px; font-weight: 700; line-height: 1; margin-bottom: 4px; }
.summary-card .label { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .5px; }
.count.critical { color: var(--critical); }
.count.warning { color: var(--warning); }
.count.ok { color: var(--ok); }
.section-title { font-size: 16px; font-weight: 600; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }
.bug-card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; margin-bottom: 16px; overflow: hidden; }
.bug-header { padding: 16px 20px; display: flex; align-items: center; gap: 12px; cursor: pointer; user-select: none; }
.bug-header:hover { background: rgba(255,255,255,.03); }
.bug-title { flex: 1; font-weight: 500; }
.bug-meta { color: var(--muted); font-size: 12px; font-family: monospace; }
.chevron { transition: transform .2s; }
.bug-card.open .chevron { transform: rotate(90deg); }
.bug-body { display: none; border-top: 1px solid var(--border); }
.bug-card.open .bug-body { display: block; }
.tab-bar { display: flex; border-bottom: 1px solid var(--border); padding: 0 20px; }
.tab { padding: 10px 16px; cursor: pointer; font-size: 13px; color: var(--muted); border-bottom: 2px solid transparent; margin-bottom: -1px; }
.tab.active { color: var(--accent); border-bottom-color: var(--accent); }
.tab-content { display: none; padding: 20px; }
.tab-content.active { display: block; }
.explanation { line-height: 1.7; white-space: pre-wrap; font-size: 13px; color: var(--text); }
.agent-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 16px; }
.agent-box { background: var(--code-bg); border: 1px solid var(--border); border-radius: 6px; padding: 16px; }
.agent-box.winner { border-color: var(--ok); }
.agent-name { font-weight: 600; font-size: 13px; margin-bottom: 8px; }
.agent-approach { color: var(--muted); font-size: 12px; margin-bottom: 12px; }
.diff-block { background: #0d1117; border-radius: 4px; padding: 12px; font-family: monospace; font-size: 11px; overflow-x: auto; white-space: pre; line-height: 1.5; }
.diff-block .add { color: #3fb950; }
.diff-block .del { color: #f85149; }
.diff-block .hunk { color: #79c0ff; }
.verdict-box { margin-top: 16px; background: rgba(88,166,255,.08); border: 1px solid rgba(88,166,255,.3); border-radius: 6px; padding: 14px; font-size: 13px; }
.verdict-box strong { color: var(--accent); }
.deploy-btn { display: inline-flex; align-items: center; gap: 8px; margin-top: 20px; padding: 10px 20px; background: var(--ok); color: #000; border: none; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer; transition: opacity .15s; }
.deploy-btn:hover { opacity: .85; }
.deploy-btn:disabled { opacity: .5; cursor: not-allowed; }
.deploy-btn.investigating { background: var(--warning); }
.deploy-output { margin-top: 12px; background: var(--code-bg); border: 1px solid var(--border); border-radius: 6px; padding: 12px; font-family: monospace; font-size: 11px; white-space: pre-wrap; display: none; max-height: 300px; overflow-y: auto; }
.location-chip { font-family: monospace; font-size: 11px; background: var(--code-bg); padding: 2px 8px; border-radius: 4px; color: var(--muted); }
.ts { font-size: 11px; color: var(--muted); }
.no-issues { text-align: center; padding: 60px; color: var(--muted); }
.refresh-btn { margin-left: auto; padding: 6px 14px; background: transparent; border: 1px solid var(--border); color: var(--muted); border-radius: 6px; cursor: pointer; font-size: 12px; }
.refresh-btn:hover { border-color: var(--accent); color: var(--accent); }
</style>
</head>
<body>
<header>
  <h1>🔍 Bug Monitor</h1>
  <span class="badge info" id="last-updated">loading…</span>
  <button class="refresh-btn" onclick="loadData()">↺ Refresh</button>
</header>
<main>
  <div class="summary" id="summary"></div>
  <div class="section-title">Open Issues</div>
  <div id="issues-list"></div>
</main>

<script>
let allData = [];

function colorDiff(diff) {
  return diff.split('\n').map(l => {
    if (l.startsWith('+++') || l.startsWith('---')) return `<span class="hunk">${esc(l)}</span>`;
    if (l.startsWith('+')) return `<span class="add">${esc(l)}</span>`;
    if (l.startsWith('-')) return `<span class="del">${esc(l)}</span>`;
    if (l.startsWith('@@')) return `<span class="hunk">${esc(l)}</span>`;
    return esc(l);
  }).join('\n');
}

function esc(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function renderDiff(diff) {
  return `<div class="diff-block">${colorDiff(diff)}</div>`;
}

function makeBugCard(item) {
  const sev = item.severity;
  const fix_id = item.fix_id;
  const fix = item.known_fix;
  const issue = item.issues[0];
  const id = `card-${item.id}`;

  let bodyHtml = '';
  if (fix) {
    const winA = fix.winning_agent === 'a' || fix.winning_agent === 'both';
    const winB = fix.winning_agent === 'b' || fix.winning_agent === 'both';
    bodyHtml = `
      <div class="tab-bar">
        <div class="tab active" onclick="switchTab(this,'${id}-explanation')">Explanation</div>
        <div class="tab" onclick="switchTab(this,'${id}-debate')">Agent Debate</div>
        <div class="tab" onclick="switchTab(this,'${id}-fix')">Proposed Fix</div>
      </div>
      <div class="tab-content active" id="${id}-explanation">
        <div class="explanation">${esc(fix.explanation)}</div>
      </div>
      <div class="tab-content" id="${id}-debate">
        <div class="agent-row">
          <div class="agent-box ${winA?'winner':''}">
            <div class="agent-name">${esc(fix.agent_a.name)} ${winA?'✓':''}</div>
            <div class="agent-approach">${esc(fix.agent_a.approach)}</div>
            ${fix.agent_a.diff && !fix.agent_a.diff.includes('Deploy Fix') ? renderDiff(fix.agent_a.diff) : `<div class="agent-approach">${esc(fix.agent_a.diff||'')}</div>`}
          </div>
          <div class="agent-box ${winB?'winner':''}">
            <div class="agent-name">${esc(fix.agent_b.name)} ${winB?'✓':''}</div>
            <div class="agent-approach">${esc(fix.agent_b.approach)}</div>
            ${fix.agent_b.diff && !fix.agent_b.diff.includes('Deploy Fix') ? renderDiff(fix.agent_b.diff) : `<div class="agent-approach">${esc(fix.agent_b.diff||'')}</div>`}
          </div>
        </div>
        <div class="verdict-box"><strong>Verdict:</strong> ${esc(fix.verdict)}</div>
      </div>
      <div class="tab-content" id="${id}-fix">
        ${fix.winning_agent && fix.agent_a.diff && !fix.agent_a.diff.includes('Deploy Fix')
          ? renderDiff(fix.winning_agent === 'b' ? fix.agent_b.diff : fix.agent_a.diff)
          : '<div class="explanation">Deploy an agent to investigate and generate the exact patch.</div>'}
        <button class="deploy-btn ${fix.winning_agent?'':'investigating'}"
                onclick="deployFix('${fix_id}', this)"
                id="deploy-${fix_id}">
          ${fix.winning_agent ? '▶ Deploy Fix Agent' : '🔍 Investigate & Fix'}
        </button>
        <div class="deploy-output" id="output-${fix_id}"></div>
      </div>`;
  } else {
    bodyHtml = `
      <div class="tab-bar">
        <div class="tab active" onclick="switchTab(this,'${id}-explanation')">Issue</div>
      </div>
      <div class="tab-content active" id="${id}-explanation">
        <div class="explanation">${esc(issue.detail)}</div>
        <button class="deploy-btn investigating" onclick="deployFix('${item.id}', this)" id="deploy-${item.id}">
          🔍 Investigate & Fix
        </button>
        <div class="deploy-output" id="output-${item.id}"></div>
      </div>`;
  }

  return `
    <div class="bug-card" id="${id}">
      <div class="bug-header" onclick="toggleCard('${id}')">
        <span class="badge ${sev}">${sev}</span>
        <span class="badge info">${esc(item.agent)}</span>
        <span class="bug-title">${fix ? esc(fix.title) : esc(issue.type.replace(/-/g,' '))}</span>
        <span class="location-chip">${esc(issue.location)}</span>
        <span class="ts">${item.timestamp.split('T')[1].split('+')[0]}</span>
        <span class="chevron">›</span>
      </div>
      <div class="bug-body">${bodyHtml}</div>
    </div>`;
}

function switchTab(el, targetId) {
  const bar = el.closest('.tab-bar');
  bar.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  el.classList.add('active');
  const body = bar.closest('.bug-body');
  body.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  document.getElementById(targetId)?.classList.add('active');
}

function toggleCard(id) {
  document.getElementById(id)?.classList.toggle('open');
}

async function deployFix(fixId, btn) {
  btn.disabled = true;
  btn.textContent = '⏳ Deploying…';
  const out = document.getElementById(`output-${fixId}`);
  out.style.display = 'block';
  out.textContent = 'Spawning fix agent…\n';

  try {
    const resp = await fetch(`/api/deploy/${encodeURIComponent(fixId)}`, {method:'POST'});
    const data = await resp.json();
    out.textContent = data.message || JSON.stringify(data, null, 2);
    btn.textContent = data.ok ? '✓ Fix Applied' : '⚠ See Output';
    if (data.ok) btn.style.background = 'var(--ok)';
    else { btn.disabled = false; btn.textContent = '↺ Retry'; }
  } catch(e) {
    out.textContent = `Error: ${e.message}`;
    btn.disabled = false;
    btn.textContent = '↺ Retry';
  }
}

async function loadData() {
  const resp = await fetch('/api/data');
  const data = await resp.json();
  allData = data;

  document.getElementById('last-updated').textContent =
    `Updated ${new Date().toLocaleTimeString()}`;

  const critCount = data.filter(d => d.severity === 'critical').length;
  const warnCount = data.filter(d => d.severity === 'warning').length;
  document.getElementById('summary').innerHTML = `
    <div class="summary-card"><div class="count critical">${critCount}</div><div class="label">Critical</div></div>
    <div class="summary-card"><div class="count warning">${warnCount}</div><div class="label">Warnings</div></div>
    <div class="summary-card"><div class="count ok">${data.length - critCount - warnCount}</div><div class="label">Passing</div></div>
    <div class="summary-card"><div class="count">${data.length}</div><div class="label">Total Checks</div></div>
  `;

  const issues = data.filter(d => d.severity === 'critical' || d.severity === 'warning');
  const list = document.getElementById('issues-list');
  if (!issues.length) {
    list.innerHTML = '<div class="no-issues">✓ No open issues</div>';
    return;
  }

  // Sort: critical first
  issues.sort((a,b) => {
    const order = {critical:0, warning:1};
    return (order[a.severity]??2) - (order[b.severity]??2);
  });

  list.innerHTML = issues.map(makeBugCard).join('');
}

loadData();
setInterval(loadData, 30000);
</script>
</body>
</html>
"""

_ISSUE_ID_RE = re.compile(r'^[a-f0-9]{40}$')

_DEBATE_SYSTEM_PROMPT = (
    "You are a code-fix debate moderator. You will be given a detected code issue.\n"
    "Propose TWO competing fixes: Agent A (minimal \u2014 smallest safe change) and Agent B\n"
    "(comprehensive \u2014 cleaner abstraction). Then give a verdict on which is better.\n\n"
    "Respond with ONLY a valid JSON object matching this exact schema:\n"
    '{\n'
    '  "agent_a": {"name": "Agent A \u2014 Minimal Fix", "approach": "<one sentence>", "diff": "<unified diff or explanation>"},\n'
    '  "agent_b": {"name": "Agent B \u2014 Comprehensive Fix", "approach": "<one sentence>", "diff": "<unified diff or explanation>"},\n'
    '  "verdict": "<explanation of which is better and why>",\n'
    '  "winning_agent": "a" | "b" | "both" | null\n'
    "}\n"
    "No markdown fences. No preamble. JSON only."
)


def _call_debate_api(agent: str, severity: str, issue_type: str,
                     location: str, detail: str) -> dict:
    """Call Anthropic API; return parsed debate dict. Raises on error."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")
    try:
        import anthropic
    except ImportError:
        raise RuntimeError("anthropic package not installed")
    client = anthropic.Anthropic(api_key=api_key)
    user_msg = (
        f"Agent: {agent}\nSeverity: {severity}\nIssue type: {issue_type}\n"
        f"Location: {location}\nDetail: {detail}\n\nPropose two fixes and give a verdict."
    )
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=_DEBATE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    raw = message.content[0].text.strip()
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)


def _generate_debate(issue_id: str, agent: str, severity: str,
                     issue_type: str, location: str, detail: str) -> dict:
    """Return debate for issue_id, using cache if available."""
    with _DEBATES_LOCK:
        cached = _load_json_safe(DEBATES_DB) or {}
        if issue_id in cached:
            return cached[issue_id]

    result = _call_debate_api(agent, severity, issue_type, location, detail)
    result["_issue_type"] = issue_type
    result["_location"] = location
    result["_detail"] = detail

    with _DEBATES_LOCK:
        existing = _load_json_safe(DEBATES_DB) or {}
        existing[issue_id] = result
        DEBATES_DB.write_text(json.dumps(existing, indent=2), encoding="utf-8")

    return result


_FIX_ID_SLUG_RE = re.compile(r'^[a-z0-9][a-z0-9\-]{0,79}$')
_FIX_ID_SHA1_RE = re.compile(r'^[a-f0-9]{40}$')


def _build_task_string(fix_id: str, fix: dict | None, debates: dict) -> str:
    """Construct the -p task string for the claude subprocess."""
    if fix is not None:
        winning = fix.get("winning_agent")
        if winning is None:
            return (
                f"Investigate and fix the following issue in {fix['file']}:\n\n"
                f"Issue: {fix['title']}\n"
                f"Description: {fix['explanation']}\n\n"
                f"Two approaches have been proposed:\n"
                f"- Agent A: {fix['agent_a']['approach']}\n"
                f"- Agent B: {fix['agent_b']['approach']}\n\n"
                "Steps:\n"
                f"1. Read {fix['file']} and all relevant files it imports\n"
                "2. Determine which approach is correct given the current code state\n"
                "3. Apply the better fix\n"
                "4. Run ruff check and pytest for the affected module\n"
                "5. Create a git commit: fix(<subsystem>): <brief title>"
            )
        agent = fix["agent_b"] if winning == "b" else fix["agent_a"]
        return (
            f"Fix the following confirmed bug in {fix['file']}:\n\n"
            f"Issue: {fix['title']}\n"
            f"Winning approach: {agent['name']} — {agent['approach']}\n\n"
            f"Proposed diff for reference:\n{agent['diff']}\n\n"
            "Steps:\n"
            f"1. Read {fix['file']} to confirm the exact current code\n"
            "2. Apply the fix described above\n"
            f"3. Run: ruff check {fix['file']}\n"
            "4. If ruff passes, create a git commit: fix(<subsystem>): <brief title>"
        )
    # Dynamic debate
    debate = debates.get(fix_id, {})
    issue_type = debate.get("_issue_type", "unknown issue")
    location = debate.get("_location", "unknown location")
    detail = debate.get("_detail", "see debate")
    location_file = location.split(":")[0]
    winning = debate.get("winning_agent")
    if winning is None:
        a_approach = debate.get("agent_a", {}).get("approach", "see debate")
        b_approach = debate.get("agent_b", {}).get("approach", "see debate")
        return (
            "Fix the following detected code issue (approach undecided — investigate and choose):\n\n"
            f"Location: {location}\nIssue type: {issue_type}\nDetail: {detail}\n\n"
            f"Two approaches proposed:\n- Agent A: {a_approach}\n- Agent B: {b_approach}\n\n"
            f"Steps:\n1. Read {location_file} to confirm the exact current code\n"
            "2. Choose and apply the better fix\n3. Run ruff/pytest as appropriate\n"
            "4. Create a git commit: fix(<subsystem>): <brief description>"
        )
    winner = debate.get("agent_b") if winning == "b" else debate.get("agent_a", {})
    return (
        f"Fix the following detected code issue:\n\n"
        f"Location: {location}\nIssue type: {issue_type}\nDetail: {detail}\n"
        f"Winning approach: {winner.get('name', 'Agent A')} — {winner.get('approach', 'see debate')}\n\n"
        f"Steps:\n1. Read {location_file} to confirm the exact current code\n"
        "2. Apply the fix described above\n3. Run ruff/pytest as appropriate\n"
        "4. Create a git commit: fix(<subsystem>): <brief description>"
    )


def _run_agent_job(fix_id: str, cmd: list) -> None:
    """Worker thread: run claude subprocess and stream output into JOBS[fix_id]."""
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    deadline = time.time() + 300
    for line in proc.stdout:
        with _JOBS_LOCK:
            JOBS[fix_id]["output"].append(line.rstrip())
        if time.time() > deadline:
            proc.kill()
            proc.wait()
            with _JOBS_LOCK:
                JOBS[fix_id]["status"] = "error"
                JOBS[fix_id]["output"].append("[timeout after 300s]")
                JOBS[fix_id]["exit_code"] = -1
            return
    proc.wait()
    with _JOBS_LOCK:
        JOBS[fix_id]["status"] = "done" if proc.returncode == 0 else "error"
        JOBS[fix_id]["exit_code"] = proc.returncode


# ── HTTP handler ──────────────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # silence access log

    def send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, html):
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/":
            self.send_html(HTML)
        elif self.path == "/api/data":
            open_issues = get_open_issues()
            with _DEBATES_LOCK:
                cached_debates = _load_json_safe(DEBATES_DB) or {}
            result = []
            for item in open_issues:
                fix_id, fix = match_known_fix(item)
                if fix is None and item.get("id") in cached_debates:
                    fix_id = item["id"]
                    fix = cached_debates[item["id"]]
                result.append({**item, "fix_id": fix_id, "known_fix": fix})
            self.send_json(result)
        elif self.path.startswith("/api/job/"):
            fix_id = self.path.removeprefix("/api/job/")
            with _JOBS_LOCK:
                job = JOBS.get(fix_id)
            if job is None:
                self.send_json({"status": "not_found", "output": [], "exit_code": None}, 404)
            else:
                self.send_json(dict(job))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path.startswith("/api/debate/"):
            issue_id = self.path.split("/api/debate/")[1]
            if not _ISSUE_ID_RE.match(issue_id):
                self.send_json({"ok": False, "message": "Invalid issue_id"}, 400)
                return
            try:
                cl = self.headers.get("Content-Length")
                content_length = int(cl) if cl and cl.strip().isdigit() else 0
                body_bytes = self.rfile.read(min(content_length, 8192))
                body = json.loads(body_bytes.decode("utf-8"))
                issues_list = body.get("issues", [{}])
                issue = issues_list[0] if issues_list else {}
                debate = _generate_debate(
                    issue_id,
                    agent=body.get("agent", ""),
                    severity=body.get("severity", ""),
                    issue_type=issue.get("type", ""),
                    location=issue.get("location", ""),
                    detail=issue.get("detail", ""),
                )
                self.send_json(debate)
            except ValueError as e:
                self.send_json({"ok": False, "message": str(e)}, 400)
            except json.JSONDecodeError as e:
                self.send_json({"ok": False, "message": f"Model response was not valid JSON: {e}"}, 500)
            except Exception as e:
                self.send_json({"ok": False, "message": str(e)}, 500)
            return
        elif self.path.startswith("/api/deploy/"):
            fix_id = self.path.split("/api/deploy/")[1]
            if not (_FIX_ID_SLUG_RE.match(fix_id) or _FIX_ID_SHA1_RE.match(fix_id)):
                self.send_json({"ok": False, "message": "Invalid fix_id"}, 400)
                return
            fix = KNOWN_FIXES.get(fix_id)
            if fix is None:
                with _DEBATES_LOCK:
                    debates = _load_json_safe(DEBATES_DB) or {}
                if fix_id not in debates:
                    self.send_json({"ok": False, "message": f"Unknown fix_id: {fix_id}"}, 404)
                    return
            self.send_json(self._run_deploy(fix_id, fix))
        else:
            self.send_response(404)
            self.end_headers()

    def _run_deploy(self, fix_id: str, fix: dict | None) -> dict:
        if shutil.which("claude") is None:
            return {"ok": False, "message": "claude CLI not found — ensure it is on PATH"}
        with _DEBATES_LOCK:
            debates = _load_json_safe(DEBATES_DB) or {}
        task = _build_task_string(fix_id, fix, debates)
        cmd = ["claude", "--allowedTools", "Edit,Read,Bash,Glob,Grep", "--print", "-p", task]
        with _JOBS_LOCK:
            JOBS[fix_id] = {"status": "running", "output": [], "exit_code": None}
        threading.Thread(target=_run_agent_job, args=(fix_id, cmd), daemon=True).start()
        return {"ok": True, "status": "running"}


class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True


def main():
    server = ThreadedHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Bug Monitor UI → http://localhost:{PORT}", flush=True)
    print(f"Reading alerts from: {LOG_FILE}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
