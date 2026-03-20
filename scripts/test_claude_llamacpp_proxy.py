from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


def _load_proxy_module():
    script_path = Path(__file__).resolve().parent / "claude_llamacpp_proxy.py"
    spec = importlib.util.spec_from_file_location("claude_llamacpp_proxy", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load claude_llamacpp_proxy module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ClaudeLlamaProxyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.proxy = _load_proxy_module()
        cls.config = cls.proxy.ProxyConfig(
            bind_host="127.0.0.1",
            bind_port=8745,
            upstream_base_url="http://127.0.0.1:8001/v1",
            upstream_api_key="local-openai-key",
            upstream_model="qwen2.5-coder-14b",
            timeout_seconds=30.0,
        )

    def test_build_openai_payload_maps_system_tools_and_tool_results(self) -> None:
        request_body = {
            "model": "qwen2.5-coder-14b",
            "system": [{"type": "text", "text": "You are precise."}],
            "messages": [
                {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "I will inspect the repo."},
                        {
                            "type": "tool_use",
                            "id": "toolu_1",
                            "name": "Read",
                            "input": {"file_path": "/tmp/example.py"},
                        },
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "tool_use_id": "toolu_1", "content": "print('ok')"},
                        {"type": "text", "text": "Continue."},
                    ],
                },
            ],
            "tools": [
                {
                    "name": "Bash",
                    "description": "Execute shell commands",
                    "input_schema": {"type": "object", "properties": {"cmd": {"type": "string"}}},
                }
            ],
            "tool_choice": {"type": "tool", "name": "Bash"},
            "max_tokens": 1024,
        }

        payload = self.proxy.build_openai_payload(request_body, self.config)

        self.assertEqual(payload["model"], "qwen2.5-coder-14b")
        self.assertFalse(payload["stream"])
        self.assertEqual(payload["messages"][0], {"role": "system", "content": "You are precise."})
        self.assertEqual(payload["messages"][1]["role"], "assistant")
        self.assertEqual(payload["messages"][1]["tool_calls"][0]["function"]["name"], "Read")
        self.assertEqual(payload["messages"][2]["role"], "tool")
        self.assertEqual(payload["messages"][2]["tool_call_id"], "toolu_1")
        self.assertEqual(payload["messages"][3], {"role": "user", "content": "Continue."})
        self.assertEqual(payload["tools"][0]["function"]["name"], "Bash")
        self.assertEqual(payload["tool_choice"]["function"]["name"], "Bash")

    def test_build_anthropic_message_response_maps_tool_calls(self) -> None:
        request_body = {"model": "qwen2.5-coder-14b", "messages": [{"role": "user", "content": "hi"}]}
        openai_response = {
            "id": "chatcmpl_test",
            "choices": [
                {
                    "finish_reason": "tool_calls",
                    "message": {
                        "content": "Need to inspect a file.",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "Read",
                                    "arguments": '{"file_path":"/tmp/example.py"}',
                                },
                            }
                        ],
                    },
                }
            ],
            "usage": {"prompt_tokens": 111, "completion_tokens": 22},
        }

        payload = self.proxy.build_anthropic_message_response(
            request_body,
            openai_response,
            fallback_model="qwen2.5-coder-14b",
        )

        self.assertEqual(payload["id"], "chatcmpl_test")
        self.assertEqual(payload["stop_reason"], "tool_use")
        self.assertEqual(payload["usage"]["input_tokens"], 111)
        self.assertEqual(payload["usage"]["output_tokens"], 22)
        self.assertEqual(payload["content"][0], {"type": "text", "text": "Need to inspect a file."})
        self.assertEqual(payload["content"][1]["type"], "tool_use")
        self.assertEqual(payload["content"][1]["name"], "Read")
        self.assertEqual(payload["content"][1]["input"]["file_path"], "/tmp/example.py")

    def test_build_count_tokens_response_includes_tools_and_messages(self) -> None:
        request_body = {
            "system": "You are concise.",
            "messages": [{"role": "user", "content": [{"type": "text", "text": "Summarize this file."}]}],
            "tools": [{"name": "Read", "input_schema": {"type": "object"}}],
        }

        payload = self.proxy.build_count_tokens_response(request_body)

        self.assertGreater(payload["input_tokens"], 0)

    def test_iter_sse_events_emits_text_and_tool_use_blocks(self) -> None:
        message_payload = {
            "id": "msg_123",
            "model": "qwen2.5-coder-14b",
            "stop_reason": "tool_use",
            "usage": {"input_tokens": 50, "output_tokens": 10},
            "content": [
                {"type": "text", "text": "Working on it."},
                {
                    "type": "tool_use",
                    "id": "toolu_1",
                    "name": "Read",
                    "input": {"file_path": "/tmp/example.py"},
                },
            ],
        }

        events = self.proxy.iter_sse_events(message_payload)

        self.assertEqual(events[0][0], "message_start")
        self.assertEqual(events[1][0], "content_block_start")
        self.assertEqual(events[2][1]["delta"]["type"], "text_delta")
        self.assertEqual(events[4][1]["content_block"]["type"], "tool_use")
        self.assertEqual(events[5][1]["delta"]["type"], "input_json_delta")
        self.assertEqual(events[-1][0], "message_stop")

    def test_build_openai_payload_preserves_stream_flag(self) -> None:
        payload = self.proxy.build_openai_payload(
            {
                "model": "qwen2.5-coder-14b",
                "messages": [{"role": "user", "content": [{"type": "text", "text": "Stream this."}]}],
                "stream": True,
            },
            self.config,
        )

        self.assertTrue(payload["stream"])

    def test_iter_openai_to_anthropic_sse_events_streams_text_deltas(self) -> None:
        request_body = {
            "system": [{"type": "text", "text": "You are concise."}],
            "messages": [{"role": "user", "content": [{"type": "text", "text": "Say hello."}]}],
            "stream": True,
        }
        openai_chunks = [
            {
                "id": "chatcmpl_stream_text",
                "model": "qwen2.5-coder-14b",
                "choices": [{"index": 0, "delta": {"role": "assistant", "content": None}, "finish_reason": None}],
            },
            {
                "id": "chatcmpl_stream_text",
                "model": "qwen2.5-coder-14b",
                "choices": [{"index": 0, "delta": {"content": "Hello"}, "finish_reason": None}],
            },
            {
                "id": "chatcmpl_stream_text",
                "model": "qwen2.5-coder-14b",
                "choices": [{"index": 0, "delta": {"content": " world"}, "finish_reason": "stop"}],
                "usage": {"completion_tokens": 2},
            },
        ]

        events = list(
            self.proxy.iter_openai_to_anthropic_sse_events(
                request_body,
                openai_chunks,
                fallback_model="qwen2.5-coder-14b",
            )
        )

        self.assertEqual(events[0][0], "message_start")
        self.assertGreater(events[0][1]["message"]["usage"]["input_tokens"], 0)
        self.assertEqual(events[1][0], "content_block_start")
        self.assertEqual(events[2][1]["delta"]["text"], "Hello")
        self.assertEqual(events[3][1]["delta"]["text"], " world")
        self.assertEqual(events[4], ("content_block_stop", {"type": "content_block_stop", "index": 0}))
        self.assertEqual(events[5][0], "message_delta")
        self.assertEqual(events[5][1]["delta"]["stop_reason"], "end_turn")
        self.assertEqual(events[5][1]["usage"]["output_tokens"], 2)
        self.assertEqual(events[6][0], "message_stop")

    def test_iter_openai_to_anthropic_sse_events_streams_tool_call_deltas(self) -> None:
        request_body = {
            "messages": [{"role": "user", "content": [{"type": "text", "text": "Read a file."}]}],
            "stream": True,
        }
        openai_chunks = [
            {
                "id": "chatcmpl_stream_tool",
                "model": "qwen2.5-coder-14b",
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "id": "call_1",
                                    "type": "function",
                                    "function": {"name": "Read", "arguments": ""},
                                }
                            ]
                        },
                        "finish_reason": None,
                    }
                ],
            },
            {
                "id": "chatcmpl_stream_tool",
                "model": "qwen2.5-coder-14b",
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "function": {"arguments": '{"file_path":"'},
                                }
                            ]
                        },
                        "finish_reason": None,
                    }
                ],
            },
            {
                "id": "chatcmpl_stream_tool",
                "model": "qwen2.5-coder-14b",
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "function": {"arguments": '/tmp/example.py"}'},
                                }
                            ]
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
                "usage": {"completion_tokens": 6},
            },
        ]

        events = list(
            self.proxy.iter_openai_to_anthropic_sse_events(
                request_body,
                openai_chunks,
                fallback_model="qwen2.5-coder-14b",
            )
        )

        self.assertEqual(events[0][0], "message_start")
        self.assertEqual(events[1][0], "content_block_start")
        self.assertEqual(events[1][1]["content_block"]["type"], "tool_use")
        self.assertEqual(events[1][1]["content_block"]["id"], "call_1")
        self.assertEqual(events[1][1]["content_block"]["name"], "Read")
        self.assertEqual(events[2][1]["delta"]["partial_json"], '{"file_path":"')
        self.assertEqual(events[3][1]["delta"]["partial_json"], '/tmp/example.py"}')
        self.assertEqual(events[4], ("content_block_stop", {"type": "content_block_stop", "index": 0}))
        self.assertEqual(events[5][1]["delta"]["stop_reason"], "tool_use")
        self.assertEqual(events[5][1]["usage"]["output_tokens"], 6)
        self.assertEqual(events[6][0], "message_stop")


if __name__ == "__main__":
    unittest.main()
