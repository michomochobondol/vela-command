"""Tools nyata yang bisa dipakai agen. Semua fungsi dieksekusi sungguhan."""
import json
import os
import re
import subprocess
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

WORKSPACE = Path(__file__).resolve().parents[2] / "workspace"
WORKSPACE.mkdir(exist_ok=True)
CONFIG_DIR = Path(__file__).resolve().parent


# ---------- 1. Scrape web ----------
def scrape_web(url: str) -> str:
    """Ambil teks utama dari sebuah halaman web. Tidak melempar exception — balas pesan error."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
        r = httpx.get(url, headers=headers, timeout=30, follow_redirects=True)
        r.raise_for_status()
    except httpx.HTTPStatusError as e:
        return f"ERROR: halaman {url} balas HTTP {e.response.status_code}. Coba URL lain."
    except Exception as e:
        return f"ERROR: gagal membuka {url}: {type(e).__name__}. Coba URL lain atau kesimpulkan dari pengetahuanmu."
    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = re.sub(r"\n{3,}", "\n\n", soup.get_text(separator="\n").strip())
    return text[:4000]


# ---------- 2. File I/O ----------
def write_file(path: str, content: str) -> str:
    p = (WORKSPACE / path).resolve()
    if not str(p).startswith(str(WORKSPACE)):
        return "ERROR: path di luar workspace dilarang."
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"OK: {len(content)} chars ditulis ke {path}"


def read_file(path: str) -> str:
    p = (WORKSPACE / path).resolve()
    if not str(p).startswith(str(WORKSPACE)) or not p.exists():
        return "ERROR: file tidak ditemukan."
    return p.read_text(encoding="utf-8")[:4000]


# ---------- 3. Generate video (ffmpeg) ----------
def generate_video(topic: str, out_path: str = None) -> str:
    """Buat video slideshow sederhana dengan teks judul + subtitle (ffmpeg)."""
    out = out_path or f"video_{topic[:20].replace(' ', '_')}.mp4"
    p = (WORKSPACE / out).resolve()
    if not str(p).startswith(str(WORKSPACE)):
        return "ERROR: path di luar workspace dilarang."
    safe_topic = topic.replace("'", "").replace(":", "\\:").replace("%", "")
    title = safe_topic[:60]
    vf = (
        f"drawtext=text='{title}':fontcolor=white:fontsize=40:"
        "x=(w-text_w)/2:y=(h-text_h)/2-40:box=1:boxcolor=black@0.5:boxborderw=20,"
        "drawtext=text='AI Generated • Web Command Center':fontcolor=0x88ccff:fontsize=22:"
        "x=(w-text_w)/2:y=(h-text_h)/2+40"
    )
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=0x1a1a2e:s=1280x720:d=5:r=24",
        "-vf", vf,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(p),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        return f"ERROR ffmpeg: {r.stderr[-300:]}"
    return f"OK: video {p.stat().st_size} bytes -> {out}"


# ---------- 4. Posting sosmed ----------
def _load_social_config() -> dict:
    cfg = CONFIG_DIR / "social_config.json"
    if cfg.exists():
        return json.loads(cfg.read_text())
    return {"webhook_url": "", "api_url": "", "api_token": "", "api_field": "text"}


def post_social(text: str) -> str:
    """Posting teks ke sosmed via webhook (Discord/Slack/Telegram) atau API custom."""
    cfg = _load_social_config()
    try:
        if cfg.get("webhook_url"):
            r = httpx.post(cfg["webhook_url"], json={"content": text[:2000]}, timeout=30)
            r.raise_for_status()
            return "OK: terkirim via webhook."
        if cfg.get("api_url"):
            headers = {"Authorization": f"Bearer {cfg['api_token']}"} if cfg.get("api_token") else {}
            field = cfg.get("api_field", "text")
            r = httpx.post(cfg["api_url"], json={field: text}, headers=headers, timeout=30)
            r.raise_for_status()
            return "OK: terkirim via API custom."
        return "BELUM DIKONFIGURASI: isi backend/tools/social_config.json (webhook_url atau api_url)."
    except httpx.HTTPStatusError as e:
        return f"ERROR: HTTP {e.response.status_code} — {e.response.text[:200]}"


# ---------- Registry ----------
TOOLS = {
    "scrape_web": {
        "fn": scrape_web,
        "desc": "Ambil teks utama dari sebuah halaman web. Parameter: url (string).",
        "schema": {
            "type": "function",
            "function": {
                "name": "scrape_web",
                "description": "Scrape teks dari halaman web.",
                "parameters": {
                    "type": "object",
                    "properties": {"url": {"type": "string", "description": "URL lengkap"}},
                    "required": ["url"],
                },
            },
        },
    },
    "write_file": {
        "fn": write_file,
        "desc": "Tulis konten ke file di workspace. Parameter: path, content.",
        "schema": {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Tulis file output (artikel, caption, dll).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                },
            },
        },
    },
    "read_file": {
        "fn": read_file,
        "desc": "Baca file dari workspace. Parameter: path.",
        "schema": {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Baca file yang sudah ada di workspace.",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
        },
    },
    "generate_video": {
        "fn": generate_video,
        "desc": "Generate video mp4 dengan teks judul (ffmpeg). Parameter: topic, out_path (opsional).",
        "schema": {
            "type": "function",
            "function": {
                "name": "generate_video",
                "description": "Buat video promosi sederhana (mp4 5 detik) dari topic.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string"},
                        "out_path": {"type": "string"},
                    },
                    "required": ["topic"],
                },
            },
        },
    },
    "post_social": {
        "fn": post_social,
        "desc": "Posting teks ke sosmed (webhook/API). Parameter: text.",
        "schema": {
            "type": "function",
            "function": {
                "name": "post_social",
                "description": "Publish konten ke media sosial.",
                "parameters": {
                    "type": "object",
                    "properties": {"text": {"type": "string"}},
                    "required": ["text"],
                },
            },
        },
    },
}
