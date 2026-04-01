import pytest
from types import SimpleNamespace
from cockpit.ui.preboot import PreBootScreen, _ServiceCheck

class MockButton:
    def __init__(self):
        self.classes = set()

    def set_class(self, value, name):
        if value:
            self.classes.add(name)
        else:
            self.classes.discard(name)

    def has_class(self, name):
        return name in self.classes

@pytest.mark.asyncio
async def test_repair_button_visibility_logic():
    screen = PreBootScreen()
    
    # Mock checks where critical services are OK
    screen._checks = [
        _ServiceCheck("Backend API", "http://localhost:8000", status="ok"),
        _ServiceCheck("llama.cpp", "http://localhost:8001", status="ok"),
    ]
    
    # Mock UI elements
    mock_log = SimpleNamespace(clear=lambda: None, write=lambda x: None)
    mock_repair_btn = MockButton()
    
    # We need to mock query_one and set_class
    def mock_query_one(selector, cls=None):
        if selector == "#health-log": return mock_log
        if selector == "#btn-repair": return mock_repair_btn
        return SimpleNamespace(update=lambda x: None)

    screen.query_one = mock_query_one
    
    screen._refresh_llm_widgets = lambda: None
    screen._router_mode_tag = lambda: ""

    # Test 1: All OK -> button hidden
    screen._render_health()
    assert not mock_repair_btn.has_class("-visible")

    # Test 2: Backend Down -> button visible
    screen._checks[0].status = "error"
    screen._render_health()
    assert mock_repair_btn.has_class("-visible")

    # Test 3: llama.cpp Down -> button visible
    screen._checks[0].status = "ok"
    screen._checks[1].status = "error"
    screen._render_health()
    assert mock_repair_btn.has_class("-visible")

    # Test 4: Both Down -> button visible
    screen._checks[0].status = "error"
    screen._render_health()
    assert mock_repair_btn.has_class("-visible")
