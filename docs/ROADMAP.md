# FileMind — Roadmap

# FileMind — Roadmap, Tracker & Jurnal Belajar

**Goal:** Jadi AI Engineer, mulai apply internship/junior/entry-level akhir 2026.  
**Proyek utama:** FileMind — chatbot terintegrasi file explorer, dikembangkan evolusioner (simple → RAG → agent → security → evaluation → observability → production → deploy).  
**Update terakhir:** 10 September 2026

---

## Cara pakai dokumen ini

Dokumen ini punya 4 fungsi sekaligus:

1. **Planning** — tahu apa yang dikerjakan tiap minggu/bulan, tanpa mikir ulang tiap kali mulai.
2. **Progress tracker** — checklist `[ ]` di tiap minggu, tinggal centang. Kalau di-import ke Notion, ini otomatis jadi to-do block.
3. **Evaluasi** — tiap bulan ada bagian “Self-assessment” untuk cek kejujuran: kamu paham komponennya atau cuma AI yang bikin.
4. **Pembelajaran** — tiap bulan ada “Learning Log” kosong untuk diisi setelah selesai: keputusan yang diambil, kesalahan, hal baru yang dipelajari. Ini bagian yang paling bikin portfolio kredibel nanti.

Isi checklist dan learning log-nya di Notion langsung, jangan ditunda sampai “sempat nulis rapi”.

---

## Prinsip Pegangan

- Ide → Problem Decomposition → Architecture → Implementation — ini tahap yang paling dilatih, bukan cuma “belajar lebih banyak”.
- Reverse engineering itu scaffolding, bukan tujuan akhir. Progres: **AI membuat → aku memahami → aku memodifikasi → aku mendesain → aku mampu membangun.**
- AI boleh mempercepat tangan, keputusan teknis tetap milik aku. Yang dijaga: **ownership of understanding.**
- Filter tiap teknologi baru: **“Apakah ini menyelesaikan masalah nyata di FileMind?”** Kalau tidak, jangan dipaksakan.
- Satu living project lebih baik dari 10 proyek setengah jadi.
- Apply akhir 2026 bukan menunggu 100% siap — targetnya “cukup kompeten, punya bukti, siap belajar dari feedback pasar”.

---

## Ringkasan Status Bulanan

|Bulan|Outcome Besar|Status|
|---|---|---|
|Fase 0 (sisa Agustus)|FileMind v1 punya scope & arsitektur jelas di atas kertas|_✅ selesai_|
|September|Phase 2 selesai (chat agent: move/delete/rename/create via bahasa natural) + Phase 1 distabilkan (komponen inti dipahami, bukan cuma jalan)|_🟨 in progress_|
|Oktober|FileMind punya RAG yang bisa dievaluasi|⬜ Belum mulai|
|November|FileMind punya lapisan production (API, security, testing, observability)|⬜ Belum mulai|
|Desember|FileMind live, portfolio siap, mulai apply|⬜ Belum mulai|

_(Ganti ⬜ jadi 🟨 in progress / ✅ selesai / 🟥 terhambat — kalau di Notion, ini enak dijadikan kolom Status di database.)_

---

## Fase 0 — Baseline (24–31 Agustus 2026)

**Outcome:** FileMind v1 punya scope & arsitektur yang jelas di atas kertas, sebelum masuk siklus bulanan.

- [x] Tentukan versi FileMind yang ingin dicapai akhir September (tulis 1 kalimat)
- [x] Buat architecture diagram FileMind versi sekarang (boleh kasar)
- [x] Tuliskan daftar semua komponen yang sudah ada
- [x] Tandai tiap komponen: **paham** vs **AI-generated / perlu reverse-engineer**  
    → tabelnya ada di `COMPONENT_CHECKLIST.md` (12 komponen, urut prioritas).  
    Kolom "Status Pemahaman" diisi Minggu 3 September, bukan di Fase 0.

**Learning log:** _(isi setelah selesai — apa yang baru kamu sadari soal arsitektur FileMind saat ini?)_

---

## September — Phase 2 (Chat Agent) + Stabilisasi Phase 1

**Outcome besar:** _"FileMind bisa diajak ngobrol bahasa natural untuk  
move/delete/rename/create file, dengan safety rules Phase 1 tetap berlaku —  
dan komponen inti Phase 1 sudah dipahami sendiri, bukan cuma jalan."_

Dua jalur paralel bulan ini:

- **Jalur A (Build):** selesaikan Phase 2 — 4 tool baru + chat loop + UI.
- **Jalur B (Stabilkan):** pastikan Phase 1 benar-benar dipahami, bukan  
    AI-generated yang jalan kebetulan.

> **Deadline internal:** Claude Code tersedia sampai 9 September. Jalur A  
> diprioritaskan di Minggu 1–2 selagi akselerator masih ada. Jalur B  
> (reverse-engineer, rebuild manual) justru dijadwalkan setelah 9 Sep —  
> memang harus mandiri.

### Minggu 1 — 29 Agu s/d 5 Sep: Design + Build Intensif (Jalur A)

- [ ] Rencana teknis Phase 2 (file baru, fungsi, signature) — via plan mode
- [ ] `move_file(src, dst)` + tes unit
- [ ] `delete_file(path)` → selalu ke `_Quarantine/`, tidak pernah `os.remove()` + tes
- [ ] `rename_file(path, new_name)` + tes
- [ ] `create_folder(path)` (opsional `create_file` kosong) + tes
- **Catatan:** pakai Claude Code semaksimal mungkin minggu ini.

### Minggu 2 — 6 s/d 9 Sep (dipendekkan, Claude Code habis 9 Sep)

- [ ] Selesaikan sisa Build Minggu 1 yang belum kelar
- [ ] Chat loop dasar (Ollama + tool calling, reuse `core/llm.py`)
- [ ] UI dasar (Rich styling; `prompt_toolkit` history boleh menyusul)
- [ ] Testing manual 4 tool baru
- [ ] Generate scaffold self-assessment Phase 2 (pola `AUDIT_REPORT` +  
    `COMPONENT_CHECKLIST` Phase 1)

### Minggu 3 — 10 s/d 19 Sep: Test & Reverse Engineer (Mandiri, Jalur B)

- [ ] Isi `COMPONENT_CHECKLIST.md` Phase 1 — kolom _Status Pemahaman_ +  
    jawab pertanyaan reflektif **tanpa buka kode**
- [ ] Rebuild 1 modul Phase 1 secara manual tanpa lihat kode AI  
    (prioritas: `organize_files.py` atau `safety.py` — lihat urutan  
    prioritas di `COMPONENT_CHECKLIST.md`)
- [ ] Testing lebih dalam untuk Phase 2: debugging, edge case tool baru
- **Catatan:** tidak ada Claude Code. Pakai dokumentasi resmi library,  
    free tier chat kalau benar-benar stuck, atau komunitas.

### Minggu 4 — 20 s/d 26 Sep: Polish & Document

- [ ] Refactor berdasarkan temuan Minggu 3
- [ ] Update `ARCHITECTURE.md` untuk mencerminkan Phase 2
- [ ] Tulis README Phase 2 (pakai template README portfolio di dokumen ini)
- [ ] Demo Phase 2 (screenshot/video singkat)

**Acceptance criteria bulan ini:**

- [ ] 4 tool baru (`move_file`, `delete_file`, `rename_file`,  
    `create_folder`) jalan via chat, semua lewat `validate_path` yang sama  
    dengan Phase 1
- [ ] Chat loop bisa: terima pesan → panggil tool → balas bahasa natural
- [ ] `delete_file` terbukti selalu ke `_Quarantine/`, tidak ada `os.remove()`
- [ ] `COMPONENT_CHECKLIST.md` Phase 1 terisi penuh, minimal 4 komponen  
    teratas ditandai **Paham Penuh**
- [ ] Minimal 1 modul Phase 1 di-rebuild manual, bisa dijelaskan tanpa buka catatan
- [ ] `ARCHITECTURE.md` + README Phase 2 sudah mencerminkan kode Phase 2

**Self-assessment:**

- Komponen Phase 1 yang sudah benar-benar kupahami: _______________
- Komponen Phase 1 yang masih perlu di-reverse-engineer Oktober: _______________
- Bagian Phase 2 yang paling kupahami cara kerjanya: _______________
- Bagian Phase 2 yang masih blackbox: _______________

**Learning log:** _(keputusan desain apa yang paling sulit bulan ini? apa yang  
ditemukan saat rebuild manual? apa yang paling susah waktu mengubah CLI  
satu-perintah jadi chat loop?)_

### Buffer — 27 s/d 30 Sep

- [ ] Wrap-up, review milestone September
- [ ] Siapkan catatan transisi ke Oktober (RAG + evaluation)

---

## Oktober — RAG + Evaluasi Dasar

**Outcome besar:** _“FileMind punya RAG yang bisa dievaluasi, bukan cuma jalan.”_

### Minggu 1 — Design

- [ ] Desain arsitektur retrieval (indexing + retrieval)
- [ ] Desain tools/agent dasar, **hanya kalau memang dibutuhkan**

### Minggu 2 — Build

- [ ] Implementasi indexing + retrieval

### Minggu 3 — Test & Reverse Engineer

- [ ] Buat dataset evaluasi kecil
- [ ] Ukur retrieval quality (precision/recall sederhana cukup)

### Minggu 4 — Polish & Document

- [ ] Dokumentasikan trade-off desain RAG di README

**Stretch (opsional, hanya kalau minggu 1–4 sudah beres):**

- [ ] Eksperimen quantization model lokal — catat hasilnya, jangan dipaksakan kalau tidak menyelesaikan masalah nyata

**Acceptance criteria bulan ini:**

- [ ] RAG jalan end-to-end
- [ ] Ada metric evaluasi awal, bukan cuma “kelihatannya jawab dengan benar”

**Self-assessment:**

- Bagian retrieval yang paling kupahami cara kerjanya: _______________
- Bagian yang masih blackbox buatku: _______________

**Learning log:** _(apa yang bikin retrieval quality naik/turun? trade-off apa yang dipilih dan kenapa?)_

---

## November — Production Engineering

**Outcome besar:** _“FileMind punya lapisan production: API, security, testing, observability dasar.”_

> Catatan penting: FileMind membaca isi file pengguna. Itu berarti dia juga “membaca” konten yang bisa berisi instruksi tersembunyi (prompt injection lewat isi file), belum lagi risiko path traversal. Jangan anggap ini checkbox terakhir — masukkan ke desain sejak minggu 1.

### Minggu 1 — Design

- [ ] Threat model untuk FileMind (apa yang bisa disalahgunakan lewat akses file?)
- [ ] Desain API + auth

### Minggu 2 — Build

- [ ] Implementasi API, auth, input sanitization

### Minggu 3 — Test & Reverse Engineer

- [ ] Testing, load test kecil
- [ ] Cari & perbaiki bug lewat debugging manual

### Minggu 4 — Polish & Document

- [ ] Logging + observability dashboard sederhana (latency, error, cost)

**Stretch (opsional):**

- [ ] Eksperimen multi-agent / specialized agent, hanya kalau benar-benar relevan dengan masalah nyata FileMind

**Acceptance criteria bulan ini:**

- [ ] Test suite dasar ada dan jalan
- [ ] Bisa melihat latency/error/cost secara langsung, bukan tebak-tebakan

**Self-assessment:**

- Keputusan security yang paling kupahami alasannya: _______________
- Bagian yang masih perlu belajar lebih dalam: _______________

**Learning log:** _(bug apa yang paling susah dicari? apa yang berubah dari cara berpikirmu soal security setelah bulan ini?)_

---

## Desember — Deploy & Apply

**Outcome besar:** _“FileMind live, portfolio siap, mulai apply.”_

### Minggu 1 — Deploy

- [ ] Deployment (cloud atau self-hosted)

### Minggu 2 — Polish

- [ ] Final polish
- [ ] Demo (video/screenshot)

### Minggu 3 — Portfolio

- [ ] README final
- [ ] GitHub cleanup
- [ ] LinkedIn update
- [ ] Resume update

### Minggu 4 — Apply

- [ ] Mulai apply Jalur A/B/C (minimal 3 jalur paralel)

**Evaluasi akhir — cek sebelum dianggap “selesai”:**

Recruiter yang lihat FileMind idealnya bisa jawab:

- [ ] Masalah apa yang diselesaikan?
- [ ] Mengapa arsitekturnya seperti itu?
- [ ] Bagaimana LLM digunakan?
- [ ] Bagaimana retrieval dilakukan?
- [ ] Bagaimana security ditangani?
- [ ] Bagaimana kualitas jawaban dievaluasi?
- [ ] Bagaimana sistem dimonitor?
- [ ] Bagaimana sistem dideploy?
- [ ] Apa trade-off yang ditemukan?
- [ ] Apa yang akan diperbaiki di versi berikutnya?

**Learning log (refleksi akhir tahun):** _(dari Agustus ke Desember, perubahan terbesar apa dalam cara berpikirmu soal system design? apa yang akan kamu lakukan beda kalau mulai dari nol lagi?)_

---

## Track Paralel (jalan terus, tidak terikat bulan tertentu)

- [ ] Dokumentasikan progress proyek organisasi kampus (R&D lead) — cicil tiap bulan, jangan numpuk di Desember
- [ ] Kumpulkan contoh lowongan AI Engineer/internship untuk skill-gap mapping
- [ ] Buat format README portfolio standar (sekali dibuat, dipakai berulang untuk semua repo)

---

## Template README Portfolio (checklist tiap proyek)

- [ ] Problem statement
- [ ] Goals
- [ ] Architecture diagram
- [ ] Tech stack
- [ ] How it works
- [ ] Key design decisions
- [ ] Trade-offs
- [ ] Evaluation / testing
- [ ] Screenshots atau demo
- [ ] Cara menjalankan proyek
- [ ] Lessons learned

Fokus utama: dokumentasikan **mengapa**, bukan hanya **apa**.

---

## Strategi Apply (Desember)

|Jalur|Isi|
|---|---|
|**A — Dream**|International companies, overseas, remote, global startup|
|**B — Experience Builder**|Local startup, internship, junior role|
|**C — Alternative Entry**|Software Engineer, Backend Engineer, ML/AI Engineer Intern, LLM Engineer Intern|

Tidak perlu 100% requirement terpenuhi sebelum apply — cek kemampuan inti + bukti lewat proyek.

---

## Hal yang Perlu Dihindari

- Mengejar tiap tren AI baru tanpa validasi
- Membuat terlalu banyak project kecil
- Menunggu merasa “sudah siap”
- Menyalin hasil AI tanpa memahami implementasinya
- Menghabiskan waktu mempercantik project tapi abai fundamental
- Mengukur kemampuan hanya dari persentase job description yang terpenuhi

---

## Kalimat Pegangan

> “Aku tidak harus bisa membangun semuanya sendirian sekarang. Aku harus mampu memahami sistem yang kubangun, mengambil keputusan teknis dengan sadar, dan terus meningkatkan kemampuan dari satu proyek ke proyek berikutnya.”
