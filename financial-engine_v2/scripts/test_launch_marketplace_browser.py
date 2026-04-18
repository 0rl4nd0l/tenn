from __future__ import annotations

from types import SimpleNamespace

import launch_marketplace_browser as launcher


def test_main_fails_early_without_graphical_session(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        launcher,
        "_parse_args",
        lambda: SimpleNamespace(
            url="https://www.facebook.com/marketplace/",
            browser="auto",
            port=9222,
            fresh_profile=False,
        ),
    )
    monkeypatch.setattr(launcher, "_wait_for_cdp", lambda *args, **kwargs: None)
    monkeypatch.setattr(launcher.sys, "platform", "linux")
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

    exit_code = launcher.main()
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "No graphical desktop session is available in this shell." in captured.err
    assert "--remote-debugging-port=9222" in captured.err


def test_main_reuses_existing_debugger_even_without_display(
    monkeypatch, capsys
) -> None:
    monkeypatch.setattr(
        launcher,
        "_parse_args",
        lambda: SimpleNamespace(
            url="https://www.facebook.com/marketplace/",
            browser="auto",
            port=9222,
            fresh_profile=False,
        ),
    )
    monkeypatch.setattr(
        launcher,
        "_wait_for_cdp",
        lambda *args, **kwargs: {"Browser": "Google Chrome 146.0.7680.153"},
    )
    monkeypatch.setattr(launcher.sys, "platform", "linux")
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

    exit_code = launcher.main()
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Marketplace browser already ready." in captured.out
    assert "http://127.0.0.1:9222" in captured.out


def test_main_delegates_to_helper_when_no_graphical_session(
    monkeypatch, capsys
) -> None:
    monkeypatch.setattr(
        launcher,
        "_parse_args",
        lambda: SimpleNamespace(
            url="https://www.facebook.com/marketplace/",
            browser="auto",
            port=9222,
            fresh_profile=False,
        ),
    )
    monkeypatch.setattr(launcher, "_wait_for_cdp", lambda *args, **kwargs: None)
    monkeypatch.setattr(launcher.sys, "platform", "linux")
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.setattr(
        launcher,
        "_launch_with_helper",
        lambda **kwargs: (
            0,
            "Marketplace browser ready via desktop helper.",
            False,
        ),
    )

    exit_code = launcher.main()
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "desktop helper" in captured.out
