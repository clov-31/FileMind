# AUDIT_REPORT.md — FileMind

Audit teknis struktur codebase. Laporan ini **hanya fakta teknis dari kode** —
tidak ada penilaian atas pemahaman pemilik codebase (kolom *Pemahaman Saya*
sengaja dikosongkan untuk diisi sendiri).

- **Tanggal audit:** 2026-08-29
- **Cakupan:** seluruh source di `agent/` dan `tests/`, plus file konfigurasi root
  (`requirements.txt`, `env.example`, `README.md`, `CLAUDE.md`).
- **Dikecualikan:** `.venv/` dan `.git/` (bukan kode proyek).
- **Fase proyek:** Phase 1 selesai (CLI: scan → classify → dry-run → execute). Phase 2–7 belum ada kode.

---

## Rubrik Kompleksitas

Dinilai per tiga sumbu (sesuai permintaan: jumlah baris, branching, jumlah
dependency internal). Tiap sumbu diberi Rendah / Sedang / Tinggi:

| Sumbu | Rendah | Sedang | Tinggi |
|---|---|---|---|
| Baris kode (LOC) | < 80 | 80–150 | > 150 |
| Branching (titik keputusan: `if`/`for`/`try`) | ≤ 3 | 4–8 | > 8 |
| Dependency internal (modul `agent.*` yang dipakai) | ≤ 1 | 2 | ≥ 3 |

**Penilaian akhir:** `Simple` bila ≥ 2 sumbu Rendah · `Complex` bila ≥ 2 sumbu
Tinggi · selain itu `Medium`. Diterapkan mekanis, bukan berdasarkan seberapa
mudah kode dibaca.

---

## Inventaris Komponen

Kolom *Dep. Internal* dipecah dua arah — **→** = komponen yang ia panggil,
**←** = komponen yang memanggilnya.

| Komponen                     | Lokasi                                                           | Fungsi Utama                                                                                                                                   | Dep. Eksternal                                                                | Dep. Internal                                                                                              | Kompleksitas                                        | Pemahaman Saya |
| ---------------------------- | ---------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- | --------------------------------------------------- | -------------- |
| **Entry Point**              | `agent/__main__.py` (8 LOC)                                      | Titik masuk `python -m agent`; hanya memanggil `cli.main()` dan mengembalikan exit code.                                                       | — (stdlib `sys`)                                                              | → `core.cli`<br>← dijalankan user                                                                          | **Simple**<br>(LOC↓ · cabang↓ · dep↓)               | Paham Penuh    |
| **CLI Orchestrator**         | `agent/core/cli.py` (161 LOC)                                    | Merangkai seluruh pipeline Phase 1: parse argumen, panggil scan → classify → organize, cetak proposal, minta konfirmasi batch.                 | — (stdlib `argparse`, `sys`, `collections`, `pathlib`)                        | → `audit`, `classify`, `config`, `organize_files`, `scan_folder`<br>← `__main__`                           | **Complex**<br>(LOC↑ · cabang↑ ~14 · dep↑ 5)        | AI Generated   |
| **Configuration**            | `agent/core/config.py` (115 LOC)                                 | Membaca & memvalidasi `.env` menjadi objek `Config` immutable; gagal keras (bukan pakai default) untuk hal yang menyangkut keamanan.           | **python-dotenv** (stdlib `os`, `dataclasses`, `pathlib`)                     | → tidak ada<br>← `cli`, `llm`, `classify`, `safety`, `scan_folder`, `organize_files`                       | **Medium**<br>(LOC→ · cabang↑ ~11 validasi · dep 0) |                |
| **LLM Client (Ollama)**      | `agent/core/llm.py` (160 LOC)                                    | Klien HTTP ke Ollama; kirim batch nama file untuk klasifikasi, parse & validasi JSON balikan model, degrade diam-diam bila Ollama mati.        | **requests** + **Ollama HTTP API** (`localhost:11434`) (stdlib `json`, `sys`) | → `config`, prompt `classify_files.md`<br>← `classify` (lazy import), `tests`                              | **Complex**<br>(LOC↑ · cabang↑ ~15 · dep↓ 1)        |                |
| **Classification**           | `agent/core/classify.py` (96 LOC)                                | Klasifikasi file: peta ekstensi dulu (deterministik), sisanya baru dieskalasi ke model lokal; yang gagal jatuh ke `Other`.                     | — (stdlib `pathlib`, `typing`)                                                | → `config` (TYPE_CHECKING), `llm` (lazy import)<br>← `cli`, `scan_folder`, `tests`                         | **Medium**<br>(LOC→ · cabang→ ~7 · dep 2)           |                |
| **Safety / Path Validation** | `agent/core/safety.py` (103 LOC)                                 | Gerbang terakhir sebelum menyentuh disk: whitelist `WATCHED_FOLDERS`, hard-block path sistem, resolusi `..`/symlink sebelum cek.               | — (stdlib `pathlib`)                                                          | → `config`<br>← `scan_folder`, `organize_files`, `tests`                                                   | **Medium**<br>(LOC→ · cabang↑ ~9 guard · dep↓ 1)    |                |
| **Audit Log**                | `agent/core/audit.py` (78 LOC)                                   | Menulis jejak audit append-only (satu objek JSON per baris); `planned` sebelum aksi, `ok`/`failed` sesudah. Tak pernah melempar exception.     | — (stdlib `json`, `threading`, `datetime`)                                    | → tidak ada<br>← `cli`, `organize_files`, `tests`                                                          | **Simple**<br>(LOC↓ · cabang↓ ~3 · dep 0)           |                |
| **Scan Folder (tool)**       | `agent/tools/scan_folder.py` (103 LOC)                           | Read-only: mendata file lepas di top-level folder, melewati direktori, folder buatan agen, download berjalan, dan file tersembunyi.            | — (stdlib `pathlib`, `typing`, `stat`)                                        | → `classify` (`CATEGORY_NAMES`), `config`, `safety`<br>← `cli`, `tests`                                    | **Complex**<br>(LOC→ · cabang↑ ~9 · dep↑ 3)         |                |
| **Organize Files (tool)**    | `agent/tools/organize_files.py` (171 LOC)                        | Satu-satunya tool yang menulis ke disk: memindah file ke subfolder kategori, `dry_run` default, anti-timpa (`(1)`), isolasi error per-file.    | — (stdlib `shutil`, `dataclasses`, `pathlib`)                                 | → `audit`, `config`, `safety`<br>← `cli`, `tests`                                                          | **Complex**<br>(LOC↑ · cabang↑ ~12 · dep↑ 3)        |                |
| **Prompts**                  | `agent/prompts/` (`classify_files.md` 25, `system_prompt.md` 36) | Teks prompt berversi. `classify_files.md` = instruksi klasifikasi JSON. `system_prompt.md` = persona/aturan tool untuk chat loop.              | — (data teks)                                                                 | → `classify_files.md` dibaca `llm`<br>`system_prompt.md` belum dibaca kode mana pun                        | — (data)                                            |                |
| **Routing (placeholder)**    | `agent/routing/__init__.py`                                      | Paket kosong; logika keputusan lokal-vs-cloud direncanakan Phase 3. Belum ada kode yang berjalan.                                              | —                                                                             | → tidak ada · ← tidak ada                                                                                  | — (placeholder)                                     |                |
| **Test Suite**               | `tests/` (conftest + 4 modul, ~350 LOC)                          | Uji unit untuk `safety`, `scan_folder`, `classify`+parser LLM, dan `organize_files`; semua berjalan dalam `tmp_path`, tak menyentuh file asli. | **pytest**                                                                    | → `config`, `safety`, `scan_folder`, `classify`, `llm`, `organize_files`, `audit`<br>← dijalankan `pytest` | **Medium**                                          |                |
### **3 Level Pemahaman (Framework)**

| Level                            | Kriteria                                                                                                         | Tanda-tandanya                                                                                     |
| -------------------------------- | ---------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| **Paham Penuh**                  | Bisa jelaskan alur lengkap + alasan desain **tanpa buka kode**, bisa prediksi efek perubahan                     | Kamu bisa cerita ke teman: "ini kerjanya begini, dan didesain begini karena..." tanpa nge-blank    |
| **Perlu Review**                 | Tahu _apa_ yang dilakukan komponen, tapi tidak yakin _kenapa_ didesain begitu atau ada edge case yang bikin ragu | Kamu bisa summary fungsinya, tapi kalau ditanya "kenapa bukan pendekatan lain?" kamu mulai menebak |
| **AI-generated, belum dipahami** | Cuma tahu "ini melakukan X" secara permukaan, tidak bisa jelaskan mekanisme internal                             | kamu harus buka kode dulu dan agak bingung mulai dari mana                                         |

---

## Ringkasan Dependency Eksternal

| Dependency | Jenis | Dipakai di | Status |
|---|---|---|---|
| `python-dotenv>=1.0` | Library (PyPI) | `config.py` | Aktif, tidak deprecated |
| `requests>=2.31` | Library (PyPI) | `llm.py` | Aktif, tidak deprecated |
| `pytest>=8.0` | Library (PyPI, dev) | `tests/` | Aktif, tidak deprecated |
| Ollama HTTP API | Service lokal (`localhost:11434`) | `llm.py` | Diakses via `requests`, opsional (run degrade bila mati) |
| Claude API (`ANTHROPIC_API_KEY`) | API eksternal | Dirujuk `config.py` (`env.example`) | **Belum dipakai kode mana pun** — cadangan Phase 3 |

---

## Observasi Teknis

Catatan objektif dari kode. Bukan penilaian; bukan daftar perintah refactor.

### 1. Kode/config yang terdeklarasi tapi belum punya konsumen
Beberapa hal sudah dibuat tapi belum dipanggil di mana pun (sebagian jelas
cadangan untuk fase berikut):

- `plan_moves()` — `organize_files.py:62` — tidak pernah dipanggil. `cli.py:89-93`
  membangun daftar `Move` secara inline. **Catatan:** logika keduanya tumpang
  tindih, dan `plan_moves` **tidak** mengisi field `tier` sedangkan versi inline
  di `cli.py` mengisinya — jadi bila nanti `plan_moves` dipakai, `tier` akan
  hilang.
- `assert_allowed()` — `safety.py:93` — terdefinisi, tidak pernah dipanggil.
- `quarantine_folder` — `config.py:39,111` — dibaca dari `.env` tapi tidak
  dikonsumsi kode mana pun (Phase 1 memang tidak punya fitur delete/quarantine;
  dikomentari sebagai "reserved").
- `anthropic_api_key` — `config.py:42,104` — dimuat tapi belum dipakai (cadangan
  tier cloud Phase 3).
- `system_prompt.md` — `agent/prompts/` — hanya `classify_files.md` yang dibaca
  (`llm.py:133`); `system_prompt.md` belum dibaca kode mana pun (untuk chat loop
  Phase 2).

### 2. Pelabelan `tier` pada file yang tak terklasifikasi
`classify.py:94` memberi `tier="rule"` pada file yang jatuh ke `Other` — padahal
justru **tidak ada rule yang cocok** untuk file itu (ekstensi tak dikenal, dan/
atau model gagal/mati). Label `"rule"` ini ikut merambat ke field `tier` di audit
log ketika file tersebut dipindah.

### 3. Dua pola impor `Config` yang berbeda dalam satu paket
`classify.py:15-16` mengimpor `Config` di bawah `TYPE_CHECKING` (anotasi string),
sedangkan `safety.py:13`, `scan_folder.py:14`, `organize_files.py:21`, dan
`llm.py:18` mengimpornya sebagai impor runtime biasa. Dependency yang sama, dua
gaya penulisan.

### 4. Dua idiom penentuan path dasar
`config.py:15` memakai `Path(__file__).resolve().parents[2]` untuk `REPO_ROOT`,
sementara `llm.py:20` memakai `Path(__file__).resolve().parent.parent / "prompts"`
untuk `PROMPTS_DIR`. Sama-sama menghitung lokasi relatif terhadap file, tapi
dengan konvensi berbeda.

### 5. Coupling antar-layer: tool bergantung pada taksonomi core
`scan_folder.py:13` (layer `tools/`) mengimpor `CATEGORY_NAMES` dari
`core/classify.py` untuk menyusun daftar folder yang dilewati. Artinya perilaku
scanner ikut berubah otomatis begitu kategori di `classify.py` ditamb/dikurangi —
keterkaitan yang tidak langsung terlihat.

### 6. Uji menembus nama privat lintas-modul
`tests/test_classify.py:6` mengimpor `_parse_batch_response` (fungsi privat,
prefiks `_`) dari `agent.core.llm`. Parser JSON milik `llm.py` diuji lewat
`test_classify.py`, bukan modul tesnya sendiri, dan lewat nama privat.

### 7. State global mutable di klien LLM
`llm.py:27` memakai flag modul-level `_warned_unreachable` agar peringatan
"Ollama mati" hanya tampil sekali. Cocok untuk proses CLI sekali-jalan; perlu
diperhatikan untuk Phase 2 (chat loop berumur panjang), karena flag tidak
ter-reset selama proses hidup.

### 8. Dependency deprecated — tidak ditemukan
Diperiksa secara khusus (permintaan audit): `python-dotenv`, `requests`, dan
`pytest` semuanya versi aktif, bukan paket usang. `audit.py:50` juga sudah
memakai `datetime.now().astimezone()` — bukan `datetime.utcnow()` yang sudah
deprecated di Python 3.12+.

### 9. Cakupan tes
Ada tes untuk `safety`, `scan_folder`, `classify` (termasuk parser LLM), dan
`organize_files`. Belum ada tes langsung untuk `cli.py` (orkestrator),
`config.load_config()` (pembacaan `.env`), dan `audit.py` (diuji tidak langsung
lewat `test_organize_files.py`). Ini catatan cakupan, bukan indikasi bug.
