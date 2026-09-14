# AI_RULES.md

> File pegangan pribadi untuk kolaborasi dengan AI di project FileMind.
> Ini BUKAN untuk AI baca otomatis. Ini untuk SAYA baca sebelum sesi AI.
> Kalau ada konflik antara file ini dengan kebiasaan, file ini yang menang.

---

## 0. Prinsip Utama

1. **Repository = memory. AI = reasoning engine.**
   Jangan biarkan AI jadi tempat menyimpan konteks project.

2. **Satu task = satu breadcrumb.**
   Jangan satu chat mengerjakan banyak fitur.

3. **Satu AI session = satu tujuan.**
   Architect / Builder / Evaluator / Portfolio — jangan campur.

4. **Context dipull, bukan dipush.**
   AI hanya menerima file yang relevan. Bukan seluruh repo.

5. **Keputusan teknis milik saya.**
   AI memberi opsi dan implementasi. Saya yang approve.

6. **Evidence sebelum "selesai".**
   Task selesai kalau ada: implementasi + test + verifikasi + breadcrumb update + commit.

7. **Lessons Learned milik saya.**
   AI boleh bantu refleksi, tapi narasi final dari saya.

---

## 1. Aturan Commit

- **Saya** yang menjalankan `git commit` dan `git push`.
- AI **boleh** draft commit message. Saya finalisasi.
- AI **tidak boleh** menjalankan `git add .` atau `git commit` tanpa saya minta eksplisit.
- Format: Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`).
- Setiap commit harus:
  - Lulus `pytest`
  - Tidak mengandung `.env`, `.venv/`, `__pycache__/`, `logs/*.log`
  - Merujuk task ID kalau relevan (`Closes TASK-0021`)

---

## 2. Aturan Context

Sebelum setiap sesi AI, saya tentukan file yang boleh dibaca.

**Default (selalu):**
- `AI_CONTEXT.md`
- `.context/current_state.md`

**Per task:**
- 1 file task (`.context/tasks/active/TASK-XXXX.md`)
- 1-3 file source yang relevan
- 1-2 file test yang relevan

**Hanya kalau perlu:**
- ADR terkait
- `ARCHITECTURE.md`
- Breadcrumb sebelumnya

**Tidak pernah default:**
- `DEVLOG.md` lengkap
- `ROADMAP.md` lengkap
- Semua source code
- Semua test
- Semua historical session

Kalau AI minta "baca semuanya", saya tolak dan saya persempit.

---

## 3. Aturan Sesi AI

| Sesi | Tujuan | Chat baru? | Output |
|---|---|---|---|
| Architect | Design task baru | Ya | Plan, ADR, task file |
| Builder | Implement 1 task | Ya | Code, test, test result |
| Evaluator | Verifikasi 1 task | Ya | Findings, edge case, risk |
| Portfolio | Dokumentasi mingguan | Ya | Summary (bukan Lessons) |

**Aturan keras:**
- Jangan pakai chat yang sama untuk 2 sesi berbeda.
- Jangan minta Builder "sekaligus evaluasi".
- Jangan minta Evaluator "sekaligus refactor".
- Kalau chat jadi panjang (>20 turn), tutup dan buka baru dengan context ringkas.

---

## 4. Aturan Keputusan

**AI wajib dilibatkan:**
- Perubahan arsitektur
- Keputusan keamanan
- Kontrak API / tool interface
- Pemilihan model / tool / library
- Trade-off yang tidak obvious

**AI opsional:**
- Naming
- Formatting
- Refactor trivial
- Unit test yang jelas
- Typo dokumentasi

**Saya putuskan sendiri:**
- Personal preference
- Scope project
- Narasi portfolio
- Lessons Learned
- Final acceptance

---

## 5. Aturan Time Tracking

- Saya isi `metrics/time_log.csv` sendiri.
- Saya catat `start` dan `end` per sesi kerja.
- Saya tidak menunda.
- Saya tidak minta AI menebak durasi.
- Kolom `mode`: `human` / `ai-assisted` / `ai-generated`.

---

## 6. Aturan Keamanan

- `.env` tidak pernah masuk Git.
- `logs/*.log` tidak pernah masuk Git.
- Sebelum commit, cek `git status` dan `git diff --cached --stat`.
- Kalau AI Agent mau menjalankan shell command yang destruktif (`rm -rf`, `git reset --hard`), saya tolak dan jalankan sendiri.

---

## 7. Aturan Debugging

Kalau ada bug:

1. Saya reproduksi dulu sendiri.
2. Saya tulis ekspektasi vs aktual.
3. Baru saya bawa ke AI dengan:
   - File terkait
   - Error message lengkap
   - Langkah reproduksi
4. AI usul hipotesis.
5. Saya tes hipotesis.
6. Saya yang putuskan fix.

Jangan: "Ada error, tolong perbaiki." tanpa konteks.

---

## 8. Aturan Selesai Task

Task dianggap selesai HANYA kalau:

- [ ] Kode terimplementasi
- [ ] Test lulus (`pytest`)
- [ ] Edge case terverifikasi
- [ ] Breadcrumb diupdate (Result, Tests, Changes)
- [ ] `current_state.md` diupdate
- [ ] Commit dibuat
- [ ] Task dipindah ke `completed/`

Kalau salah satu belum, task belum selesai. Titik.

---

## 9. Aturan Lessons Learned

- Ditulis **oleh saya**, bukan AI.
- AI boleh ditanya: "Apa pertanyaan reflektif yang sebaiknya saya jawab?"
- AI **tidak boleh** menulis paragraf Lessons Learned.
- Kalau saya stuck, saya tulis dulu versi jelek, baru refine sendiri.

---

## 10. Kalau Saya Melanggar Aturan Ini

Saya berhenti. Saya baca ulang file ini. Saya perbaiki.

Aturan ini ada bukan untuk membatasi, tapi supaya saya tetap jadi engineer, bukan operator AI.