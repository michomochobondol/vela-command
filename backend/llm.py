"""LLM client — panggil Ollama lokal."""
import json
import httpx

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL = "qwen2.5:3b-instruct"


def chat(messages: list[dict], timeout: int = 300) -> str:
    """Kirim messages ke Ollama, balas teks saja. Raise RuntimeError kalau gagal."""
    payload = {"model": MODEL, "messages": messages, "stream": False}
    r = httpx.post(OLLAMA_URL, json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json()["message"]["content"]


def chat_tool(messages: list[dict], tools: list[dict], timeout: int = 300) -> dict:
    """
    Chat dengan tool-calling. Return dict:
      {"type": "tool_call", "name": ..., "arguments": {...}}
      {"type": "text", "content": ...}
    Ollama (OpenAI-compatible /api/chat) mendukung format tools.
    """
    payload = {"model": MODEL, "messages": messages, "tools": tools, "stream": False}
    r = httpx.post(OLLAMA_URL, json=payload, timeout=timeout)
    r.raise_for_status()
    msg = r.json()["message"]
    if msg.get("tool_calls"):
        tc = msg["tool_calls"][0]
        fn = tc.get("function", {})
        args = fn.get("arguments", {})
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except Exception:
                args = {"raw": args}
        return {"type": "tool_call", "name": fn.get("name", ""), "arguments": args}
    return {"type": "text", "content": msg.get("content", "")}
