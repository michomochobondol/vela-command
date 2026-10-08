"""Test backend tanpa browser: tools + pipeline 2 agen."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.tools.registry import scrape_web, write_file, read_file, generate_video, post_social
from backend.orchestrator import Orchestrator

print("== TEST 1: write_file ==")
print(write_file("test.txt", "Halo dari Web Command Center!"))

print("\n== TEST 2: read_file ==")
print(read_file("test.txt"))

print("\n== TEST 3: scrape_web ==")
print(scrape_web("https://example.com")[:200])

print("\n== TEST 4: generate_video ==")
print(generate_video("Kopi Herbal Sehat"))

print("\n== TEST 5: post_social (belum dikonfigurasi = pesan informasi) ==")
print(post_social("Tes posting dari Web Command Center"))

print("\n== TEST 6: pipeline 2 agen (researcher -> writer) ==")
logs = []
o = Orchestrator(log_fn=lambda m: (logs.append(m), print("  [log]", m))[1])
result = o.run_pipeline(
    "Buat 1 caption promosi singkat tentang kopi herbal untuk pemula.",
    ["researcher", "writer"],
)
print("\n--- OUTPUT WRITER ---")
print(result["outputs"]["writer"][:800])
print("\nALL TESTS DONE")
