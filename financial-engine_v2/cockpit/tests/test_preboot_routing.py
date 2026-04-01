from __future__ import annotations
from types import MethodType, SimpleNamespace
from cockpit.ui.preboot import PreBootScreen

def test_collect_flags_includes_hybrid_router_policy():
    screen = PreBootScreen()
    widgets = {
        "#opt-readonly": SimpleNamespace(value=False),
        "#opt-web": SimpleNamespace(value=True),
        "#opt-rag": SimpleNamespace(value=True),
        "#opt-verbose": SimpleNamespace(value=False),
        "#opt-profile": SimpleNamespace(value="full"),
        "#opt-routing": SimpleNamespace(value="api_only"),
    }

    def _query_one(self, selector, cls=None):
        return widgets[selector]

    screen.query_one = MethodType(_query_one, screen)

    flags = screen._collect_flags()

    assert flags["hybrid_router_policy"] == "api_only"

def test_collect_flags_handles_blank_routing_policy():
    screen = PreBootScreen()
    # Mocking Select.BLANK or None
    widgets = {
        "#opt-readonly": SimpleNamespace(value=False),
        "#opt-web": SimpleNamespace(value=True),
        "#opt-rag": SimpleNamespace(value=True),
        "#opt-verbose": SimpleNamespace(value=False),
        "#opt-profile": SimpleNamespace(value="full"),
        "#opt-routing": SimpleNamespace(value=None),
    }

    def _query_one(self, selector, cls=None):
        return widgets[selector]

    screen.query_one = MethodType(_query_one, screen)

    flags = screen._collect_flags()

    assert flags["hybrid_router_policy"] is None
