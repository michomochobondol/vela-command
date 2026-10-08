# Web Command Center — Multi-Agent AI System (100% local & free)

Dashboard web untuk mengendalikan tim agen AI otonom yang berkolaborasi
mengeksekusi tugas nyata: riset web, generate video, posting sosmed,
SEO, dan affiliate marketing.

## Arsitektur

```
Frontend (HTML/JS, tanpa build step)
   │  POST /api/command  + WebSocket /ws
   ▼
Backend (FastAPI, uvicorn)
   │
   ▼
Orchestrator (custom, tool-calling loop)
   ├── Agent Researcher  → scrape_web, read_file
   ├── Agent Analyst     → bahan konten & strategi
   ├── Agent Marketer    → SEO + affiliate link
   ├── Agent Publisher   → post_social, write_file
   └── Agent VideoMaker  → generate_video (ffmpeg)
   │
   ▼
Ollama (qwen2.5:3b-instruct, lokal)
```

## Run

```bash
# 1. Pastikan Ollama jalan
ollama serve &            # kalau belum otomatis
ollama pull qwen2.5:3b-instruct

# 2. Install deps backend
uv pip install -r requirements.txt   # fastapi uvicorn websockets httpx

# 3. Jalankan server
uvicorn backend.main:app --reload --port 8000

# 4. Buka dashboard
# http://localhost:8000
```

## Konfigurasi posting sosmed
`backend/tools/social_config.json`:
```json
{
  "webhook_url": "https://discord.com/api/webhooks/...",   // opsi 1
  "api_url": "", "api_token": "", "api_field": "text"      // opsi 2: API custom
}
```
Webhook Discord/Slack/Telegram = cara termudah tanpa key resmi.

## Tools tersedia
| Tool | Fungsi |
|---|---|
| `scrape_web(url)` | Ambil teks halaman web |
| `write_file(path, content)` | Tulis file output |
| `read_file(path)` | Baca file |
| `generate_video(topic, out_path)` | Render video slideshow + teks (ffmpeg) |
| `post_social(text)` | Posting ke sosmed via webhook/API |

## Test cepat
```bash
python3 scripts/test_backend.py
```
