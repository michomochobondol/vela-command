"""LLM client — dukung Ollama lokal & Groq (OpenAI-compatible), pilih via env."""
import json
import os
import httpx

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b-instruct")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")


def _env_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")


def _groq_key() -> str:
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key and os.path.exists(_env_path()):
        for line in open(_env_path()):
            if line.startswith("GROQ_API_KEY="):
                key = line.split("=", 1)[1].strip()
    return key


def _provider() -> str:
    p = os.environ.get("LLM_PROVIDER", "").lower()
    if p:
        return p
    # Auto: kalau ada GROQ_API_KEY dan tidak ada ollama lokal, pakai groq
    try:
        httpx.get(OLLAMA_URL.replace("/api/chat", "/api/tags"), timeout=2)
        return "ollama"
    except Exception:
        return "groq" if _groq_key() else "ollama"


# ---------- Konversi format pesan untuk Groq (OpenAI-style) ----------
def _to_openai_messages(messages: list[dict]) -> list[dict]:
    """Ubah pesan format ollama (role tool tanpa id) jadi OpenAI-compatible."""
    out = []
    pending_id = 1
    for m in messages:
        if m["role"] == "assistant" and m.get("tool_calls"):
            out.append({
                "role": "assistant",
                "content": m.get("content") or None,
                "tool_calls": [{
                    "id": f"call_{pending_id}",
                    "type": "function",
                    "function": {
                        "name": mtc["function"]["name"],
                        "arguments": json.dumps(mtc["function"]["arguments"], ensure_ascii=False),
                    },
                } for mtc in m["tool_calls"]],
            })
            pending_id += 1
        elif m["role"] == "tool":
            out.append({"role": "tool", "tool_call_id": f"call_{pending_id - 1}", "content": m["content"]})
        else:
            out.append({"role": m["role"], "content": m.get("content", "")})
    return out


def chat(messages: list[dict], timeout: int = 300) -> str:
    """Kirim messages, balas teks saja. Raise RuntimeError kalau gagal."""
    if _provider() == "groq":
        key = _groq_key()
        if not key:
            raise RuntimeError("GROQ_API_KEY belum diisi (di .env atau env).")
        payload = {"model": GROQ_MODEL, "messages": _to_openai_messages(messages)}
        r = httpx.post(GROQ_URL, json=payload, headers={"Authorization": f"Bearer {key}"},
                       timeout=timeout)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    payload = {"model": OLLAMA_MODEL, "messages": messages, "stream": False}
    r = httpx.post(OLLAMA_URL, json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json()["message"]["content"]


def chat_tool(messages: list[dict], tools: list[dict], timeout: int = 300) -> dict:
    """
    Chat dengan tool-calling. Return dict:
      {"type": "tool_call", "name": ..., "arguments": {...}}
      {"type": "text", "content": ...}
    """
    if _provider() == "groq":
        key = _groq_key()
        if not key:
            raise RuntimeError("GROQ_API_KEY belum diisi (di .env atau env).")
        payload = {
            "model": GROQ_MODEL,
            "messages": _to_openai_messages(messages),
            "tools": [t if "type" in t else {"type": "function", "function": t["function"]} for t in tools],
        }
        r = httpx.post(GROQ_URL, json=payload, headers={"Authorization": f"Bearer {key}"},
                       timeout=timeout)
        r.raise_for_status()
        msg = r.json()["choices"][0]["message"]
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
        return {"type": "text", "content": msg.get("content") or ""}

    payload = {"model": OLLAMA_MODEL, "messages": messages, "tools": tools, "stream": False}
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
