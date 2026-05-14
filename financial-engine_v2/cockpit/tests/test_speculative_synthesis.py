from cockpit.core.agent_loop import AgentLoop
from unittest.mock import MagicMock
import pytest

def test_build_synthesis_messages_speculative():
    loop = AgentLoop(llm_client=MagicMock(), tool_executor=MagicMock())
    evidence = [
        {
            "type": "orchestrator",
            "result": {"is_speculative": True}
        }
    ]
    messages = loop._build_synthesis_messages(
        evidence=evidence,
        question="What is the status of AR1?",
        ticker="AR1",
        conversation_history=[],
        draft_answer="Draft answer"
    )
    
    system_msg = next(m["content"] for m in messages if m["role"] == "system")
    assert "⚠️ SPECULATIVE ASSESSMENT" in system_msg
    assert "structured financial data is missing" in system_msg.lower()

def test_build_synthesis_messages_not_speculative():
    loop = AgentLoop(llm_client=MagicMock(), tool_executor=MagicMock())
    evidence = [
        {
            "type": "orchestrator",
            "result": {"is_speculative": False}
        }
    ]
    messages = loop._build_synthesis_messages(
        evidence=evidence,
        question="What is the status of AR1?",
        ticker="AR1",
        conversation_history=[],
        draft_answer="Draft answer"
    )
    
    system_msg = next(m["content"] for m in messages if m["role"] == "system")
    assert "⚠️ SPECULATIVE ASSESSMENT" not in system_msg
