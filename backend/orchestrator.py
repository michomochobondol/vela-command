"""Orkestrator multi-agen: loop tool-calling dengan Ollama lokal."""
import json
import time
import traceback

from backend.llm import chat, chat_tool
from backend.tools.registry import TOOLS

AGENTS = {
    "researcher": {
        "role": "Agent Researcher",
        "tools": ["scrape_web", "read_file"],
        "system": (
            "Kamu Agent Researcher dalam tim AI. Tugasmu: mencari & mengumpulkan data. "
            "Gunakan tool scrape_web untuk membuka URL yang relevan, read_file untuk membaca file. "
            "Setelah selesai, tulis ringkasan temuan secara ringkas dalam Bahasa Indonesia. "
            "Selalu panggil tool jika data dibutuhkan."
        ),
    },
    "writer": {
        "role": "Agent Writer",
        "tools": ["read_file", "write_file"],
        "system": (
            "Kamu Agent Writer. Tugasmu: mengubah data/temuan menjadi konten siap publish "
            "(artikel, caption, script). Tulis dalam Bahasa Indonesia yang natural. "
            "Simpan hasilnya dengan tool write_file dan beri tahu path filenya."
        ),
    },
    "marketer": {
        "role": "Agent Marketer",
        "tools": ["write_file", "post_social"],
        "system": (
            "Kamu Agent Marketer (SEO + affiliate). Tugasmu: mengoptimalkan konten untuk SEO, "
            "menyisipkan affiliate link (pakai placeholder [AFF_LINK] kalau belum diberi link), "
            "dan memposting ke sosmed dengan post_social bila diminta. Bahasa Indonesia natural."
        ),
    },
    "publisher": {
        "role": "Agent Publisher",
        "tools": ["post_social", "write_file", "read_file"],
        "system": (
            "Kamu Agent Publisher. Tugasmu: memfinalisasi dan mempublish konten. "
            "Baca konten dari file, lalu post_social untuk publish. Lapor hasil akhir."
        ),
    },
    "videomaker": {
        "role": "Agent VideoMaker",
        "tools": ["generate_video", "write_file"],
        "system": (
            "Kamu Agent VideoMaker. Tugasmu: membuat video promosi dengan tool generate_video. "
            "Simpan juga deskripsi/caption video dengan write_file. Lapor path videonya."
        ),
    },
}


class Orchestrator:
    def __init__(self, log_fn=None):
        self.log = log_fn or (lambda msg: None)

    def _agent_messages(self, agent_key: str, task: str, context: str) -> list[dict]:
        a = AGENTS[agent_key]
        sys = a["system"] + "\n\nContext dari agen sebelumnya (jika ada):\n" + (context or "(kosong — kamu agen pertama)")
        return [{"role": "system", "content": sys}, {"role": "user", "content": task}]

    def _run_agent(self, agent_key: str, task: str, context: str, max_steps: int = 4) -> str:
        a = AGENTS[agent_key]
        self.log(f"▶️ {a['role']} mulai tugas: {task[:120]}")
        messages = self._agent_messages(agent_key, task, context)
        tools = [TOOLS[t]["schema"] for t in a["tools"] if t in TOOLS]
        result_text = ""
        for step in range(max_steps):
            try:
                resp = chat_tool(messages, tools)
            except Exception as e:
                # Retry sekali (error LLM bisa sementara), lalu lanjut ke agen berikutnya
                try:
                    resp = chat_tool(messages, tools)
                except Exception as e2:
                    result_text = f"(ERROR LLM setelah 2 percobaan: {e2})"
                    self.log(f"❌ {a['role']}: {e2}")
                    break
            try:
                if resp["type"] == "tool_call":
                    name, args = resp["name"], resp["arguments"]
                    self.log(f"🔧 {a['role']} memanggil {name}({json.dumps(args, ensure_ascii=False)[:150]})")
                    fn = TOOLS.get(name, {}).get("fn")
                    try:
                        out = fn(**args) if fn else f"ERROR: tool {name} tidak ada"
                    except TypeError as e:
                        out = f"ERROR: argumen tool salah ({e})"
                    except Exception as e:
                        out = f"ERROR tool gagal: {type(e).__name__}: {str(e)[:200]}"
                    self.log(f"   ↳ hasil: {str(out)[:200]}")
                    messages.append({"role": "assistant", "content": "", "tool_calls": [
                        {"function": {"name": name, "arguments": args}}]})
                    messages.append({"role": "tool", "content": str(out)[:2000]})
                else:
                    result_text = resp["content"]
                    self.log(f"✅ {a['role']} selesai.")
                    break
            except Exception as e:
                self.log(f"⚠️ {a['role']} step {step} error: {e} — lanjut.")
        return result_text or "(tidak ada output teks)"

    def run_pipeline(self, objective: str, pipeline: list[str]) -> dict:
        """Jalankan rantai agen berurutan, output satu menjadi context berikutnya."""
        t0 = time.time()
        context = ""
        outputs = {}
        for agent_key in pipeline:
            out = self._run_agent(agent_key, objective, context)
            outputs[agent_key] = out
            context = f"[{AGENTS[agent_key]['role']}]\n{out}"
        self.log(f"🏁 Pipeline selesai dalam {time.time() - t0:.1f}s — agen: {', '.join(pipeline)}")
        return {"objective": objective, "pipeline": pipeline, "outputs": outputs}

    def auto_plan(self, objective: str) -> list[str]:
        """Minta LLM memilih rantai agen yang cocok; fallback default."""
        names = ", ".join(f"{k} ({v['role']})" for k, v in AGENTS.items())
        prompt = (
            f"Objektif: {objective}\n"
            f"Agen tersedia: {names}.\n"
            "Pilih urutan agen (2-4) yang paling cocok. Jawab HANYA JSON array, "
            'contoh: ["researcher","writer","marketer"]'
        )
        try:
            raw = chat([{"role": "user", "content": prompt}])
            m = raw[raw.find("["):raw.rfind("]") + 1]
            plan = [a for a in json.loads(m) if a in AGENTS]
            if plan:
                return plan
        except Exception:
            pass
        return ["researcher", "writer", "marketer"]
