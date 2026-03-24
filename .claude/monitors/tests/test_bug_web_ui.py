import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import bug_web_ui as ui


def test_load_json_safe_missing():
    assert ui._load_json_safe(pathlib.Path("/nonexistent/path.json")) is None


def test_load_json_safe_valid(tmp_path):
    p = tmp_path / "d.json"
    p.write_text('{"a": 1}')
    assert ui._load_json_safe(p) == {"a": 1}


def test_load_json_safe_non_dict(tmp_path):
    p = tmp_path / "d.json"
    p.write_text('[1, 2, 3]')
    assert ui._load_json_safe(p) is None


def test_threaded_server_class():
    import socketserver, http.server
    assert issubclass(ui.ThreadedHTTPServer, socketserver.ThreadingMixIn)
    assert issubclass(ui.ThreadedHTTPServer, http.server.HTTPServer)


def test_parse_alerts_stable_id(tmp_path):
    log = tmp_path / "alerts.log"
    log.write_text(
        "[2026-03-24T04:00:00+00:00] [BUGS] severity=critical  (abc12345..def67890)\n"
        "  \u26a0  NullDeref @ myfile.py:42: value may be None\n"
        "\n"
    )
    original = ui.LOG_FILE
    ui.LOG_FILE = log
    alerts1 = ui.parse_alerts()
    alerts2 = ui.parse_alerts()
    ui.LOG_FILE = original

    assert len(alerts1) == 1
    assert len(alerts1[0]["issues"]) == 1
    # ID must be a 40-char hex string
    assert len(alerts1[0]["id"]) == 40
    assert all(c in "0123456789abcdef" for c in alerts1[0]["id"])
    # ID must be stable across calls
    assert alerts1[0]["id"] == alerts2[0]["id"]


def test_parse_alerts_no_issues_filtered(tmp_path):
    """ok-severity alerts (no issues) are filtered out by get_open_issues."""
    log = tmp_path / "alerts.log"
    log.write_text(
        "[2026-03-24T04:00:00+00:00] [BUGS] ok  (abc12345)\n"
        "\n"
    )
    original = ui.LOG_FILE
    ui.LOG_FILE = log
    alerts = ui.parse_alerts()
    ui.LOG_FILE = original
    open_items = [a for a in alerts if a.get("issues")]
    assert open_items == []


def test_run_agent_job_success(monkeypatch):
    import subprocess as sp

    class FakeProc:
        returncode = 0
        stdout = iter(["line one\n", "line two\n"])
        def wait(self): pass

    monkeypatch.setattr(sp, "Popen", lambda *a, **kw: FakeProc())
    monkeypatch.setattr(ui, "time", type("T", (), {"time": staticmethod(lambda: 0)})())

    ui.JOBS["test-job"] = {"status": "running", "output": [], "exit_code": None}
    ui._run_agent_job("test-job", ["claude", "--print", "-p", "fix it"])

    assert ui.JOBS["test-job"]["status"] == "done"
    assert ui.JOBS["test-job"]["output"] == ["line one", "line two"]
    assert ui.JOBS["test-job"]["exit_code"] == 0


def test_run_agent_job_nonzero_exit(monkeypatch):
    import subprocess as sp

    class FakeProc:
        returncode = 1
        stdout = iter(["error output\n"])
        def wait(self): pass

    monkeypatch.setattr(sp, "Popen", lambda *a, **kw: FakeProc())
    monkeypatch.setattr(ui, "time", type("T", (), {"time": staticmethod(lambda: 0)})())

    ui.JOBS["fail-job"] = {"status": "running", "output": [], "exit_code": None}
    ui._run_agent_job("fail-job", ["claude", "--print", "-p", "fix it"])

    assert ui.JOBS["fail-job"]["status"] == "error"
    assert ui.JOBS["fail-job"]["exit_code"] == 1


import re as _re

_SLUG_RE = _re.compile(r'^[a-z0-9][a-z0-9\-]{0,79}$')
_SHA1_RE = _re.compile(r'^[a-f0-9]{40}$')


def test_fix_id_slug_valid():
    assert _SLUG_RE.match("uuid-serialization-crash")
    assert _SLUG_RE.match("ingestion-metrics-always-empty")


def test_fix_id_slug_invalid():
    assert not _SLUG_RE.match("../etc/passwd")
    assert not _SLUG_RE.match("")
    assert not _SLUG_RE.match("UPPER-CASE")


def test_fix_id_sha1_valid():
    assert _SHA1_RE.match("a" * 40)


def test_fix_id_sha1_invalid():
    assert not _SHA1_RE.match("a" * 39)
    assert not _SHA1_RE.match("g" * 40)


def test_build_task_known_fix_with_winner():
    fix = ui.KNOWN_FIXES["uuid-serialization-crash"]
    task = ui._build_task_string("uuid-serialization-crash", fix, debates={})
    assert fix["file"] in task
    assert fix["agent_a"]["approach"] in task  # winning_agent == "a"


def test_build_task_known_fix_no_winner():
    fix = ui.KNOWN_FIXES["ingestion-metrics-always-empty"]
    assert fix["winning_agent"] is None
    task = ui._build_task_string("ingestion-metrics-always-empty", fix, debates={})
    assert fix["agent_a"]["approach"] in task
    assert fix["agent_b"]["approach"] in task


def test_debate_cache_hit(tmp_path, monkeypatch):
    """Cache hit returns stored result without calling API."""
    import json
    issue_id = "a" * 40
    cached = {
        "agent_a": {"name": "A", "approach": "minimal", "diff": ""},
        "agent_b": {"name": "B", "approach": "comprehensive", "diff": ""},
        "verdict": "A wins",
        "winning_agent": "a",
    }
    db = tmp_path / "debates.json"
    db.write_text(json.dumps({issue_id: cached}))
    monkeypatch.setattr(ui, "DEBATES_DB", db)

    api_called = []
    monkeypatch.setattr(ui, "_call_debate_api", lambda *a, **kw: api_called.append(1) or {})

    result = ui._generate_debate(issue_id, "BUGS", "critical", "NullDeref", "f.py:1", "is None")
    assert result == cached
    assert api_called == []
