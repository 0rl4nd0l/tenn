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
