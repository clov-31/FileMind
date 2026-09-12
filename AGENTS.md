# AGENTS.md — FileMind

Aturan main proyek. Dibaca oleh semua AI agent (Claude Code, Codex, Cursor,
dll). Baca ini dulu sebelum menyentuh kode atau dokumen apa pun.

## Project Overview

AI agent lokal-first untuk manajemen file, jalan di perangkat sendiri via
Ollama. Dua tanggung jawab:
1. **File Manager** — scan/watch folder, klasifikasi, rapikan ke struktur
   yang masuk akal. Tidak pernah hapus permanen.
2. **Productivity Assistant** — chat interface untuk Word, Excel, (nanti) Canva.

Inspirasi: JARVIS, diperkecil ke yang realistis di laptop CPU-only, dengan
opsi eskalasi ke Claude API untuk kasus yang model lokal tidak sanggup.

## Hardware Constraint (jangan berasumsi lebih)

- Laptop: Lenovo IdeaPad Slim 3 14IAH8
- CPU: Intel Core i5-12450H (4P+8E, 12 thread) — **tanpa GPU diskrit**
- RAM: 16 GB total (~15.7 GB usable). Budget model lokal maks ~8–10 GB.
- OS: Windows 11 Home Single Language (10.0.26200)
- Storage: ~475 GB SSD — bukan constraint

Model lokal harus tetap Q4-quantized, ~2B–12B parameter.

## Arsitektur (3 Lapis)

1. **Brain** — reasoning engine, dua tier:
   - *Local (default):* Ollama di `localhost:11434`. Model: `llama3.1:8b`.
   - *Cloud (fallback):* Claude API. Belum diimplementasi (Phase 3).
2. **Hands** — fungsi Python ("tools") yang menyentuh filesystem. LLM tidak
   pernah sentuh disk langsung; hanya bisa minta tool call, kode yang putuskan.
3. **Mouth** — chat interface. CLI dulu; desktop window nanti.

## Safety Rules File Operations (NON-NEGOTIABLE)

1. **Tidak ada penghapusan permanen.** "Delete" selalu berarti "pindah ke
   `_Quarantine/` dengan timestamp", bukan `os.remove()`.
2. **Log setiap aksi** ke `logs/actions.log` sebelum eksekusi: timestamp,
   action, source, destination, tier (local/cloud/rule).
3. **Tool baru default `dry_run=True`** sampai logikanya diverifikasi manual.
4. **Whitelist, bukan blacklist.** Hanya folder di `WATCHED_FOLDERS` yang
   boleh disentuh. Jangan asumsikan akses ke seluruh filesystem.
5. **Hard-block path sistem** apapun isi whitelist: `C:\Windows`,
   `C:\Program Files`, `C:\Program Files (x86)`, semua di bawah `AppData`
   kecuali ditambah eksplisit.
6. **Batch action butuh konfirmasi.** Move/rename lebih dari
   `BATCH_CONFIRM_THRESHOLD` file sekaligus butuh "yes" eksplisit dari user.
   LLM tidak bisa self-approve.
7. **Validasi sebelum eksekusi.** Jangan percaya argumen tool call LLM.
   Cek: path ada, di dalam folder yang diizinkan, tidak sedang dibuka.

## Coding Conventions

- Type hints di setiap signature fungsi.
- Docstring jelas di setiap tool — itu yang dibaca LLM sebagai deskripsi tool.
  Tulis untuk model, bukan cuma untuk manusia.
- Tool return `{success, message, data}`. Jangan biarkan exception lolos ke
  agent loop.
- Tidak ada hardcoded path, API key, atau nama model. Semua lewat `.env`.
- Tool kecil dan single-purpose. Komposisi perilaku di `core/`, bukan di tool.

## Tech Stack

- Python 3.11+
- Ollama (local inference), model default `llama3.1:8b`
- `requests` untuk HTTP ke Ollama
- `python-dotenv` untuk config
- `pytest` untuk tes
- Claude API (`anthropic` SDK) — Phase 3, belum dipakai
- `watchdog` — Phase 4, belum dipakai
- `python-docx`, `openpyxl` — Phase 5, belum dipakai

## Roadmap (ringkas)

- [x] Phase 1 — CLI: scan → classify → dry-run → execute
- [ ] Phase 2 — Chat loop + tool-calling (move/delete/rename/create per-file)
- [ ] Phase 3 — Routing lokal/cloud
- [ ] Phase 4 — `watchdog` background monitoring
- [ ] Phase 5 — Office helpers
- [ ] Phase 6 — Canva Connect API
- [ ] Phase 7 — Desktop shell / system tray

## Dokumen Detail

- Arsitektur: `docs/ARCHITECTURE.md`
- Roadmap + tracker + jurnal: `docs/ROADMAP.md`
- Devlog perjalanan: `docs/DEVLOG.md`
- Requirements Phase 2: `docs/PHASE_2.md`
- Checklist pemahaman komponen: `docs/COMPONENT_CHECKLIST.md`
- Rencana Phase 1 (selesai, arsip): `docs/archive/PHASE_1.md`
- Audit teknis Phase 1 (arsip): `docs/archive/AUDIT_REPORT.md`

## Catatan Ollama

- Ollama default context 4K. **Set `num_ctx` eksplisit (8192+)** di API call.
- Model kecil cenderung over-trigger tool call. System prompt harus bilang:
  hanya panggil tool kalau user minta aksi; jawab pertanyaan biasa dengan teks.
- Cek `ollama list` setelah pull untuk konfirmasi tag — tag bisa berubah.