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
