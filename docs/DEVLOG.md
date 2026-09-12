# FileMind — Project Journey (DEVLOG)

> **Catatan jujur di awal:** dokumen ini disusun dari dua sumber —
> riwayat percakapan (tanpa timestamp asli) dan artefak yang ada di repo.
> Urutan akurat. Sebagian tanggal direkonstruksi dari modified-date file
> (ditandai eksplisit); sisanya tidak bertanggal karena tidak bisa
> dipastikan tanpa mengarang.

**Periode:** awal Agustus 2026 – 10 September 2026
**Status akhir dokumen:** Phase 1 selesai & teraudit, Phase 2 berjalan

---

## 1. Ide awal

Bermula dari keinginan bikin "kloningan JARVIS level laptop" — agent pribadi
yang nempel di file explorer, punya chatbot, tugasnya beresin file manager
yang berantakan sekaligus bantu kerjaan Word/Excel/Canva. Dijelaskan konsep
tiga lapis (otak/tangan/mulut), dua opsi (pakai MCP di Claude Desktop yang
sudah jadi, atau bangun sendiri dari nol), dan roadmap kasar MVP mingguan.

## 2. Cek batas hardware

Spek laptop di-share: **IdeaPad Slim 3 14IAH8**, **i5-12450H**, **16GB RAM**
(15.7GB usable), **tanpa GPU diskrit**. Ini nentuin semua keputusan
sesudahnya: model lokal harus tetap di kelas 3B–9B parameter, quantized Q4.
Direkomendasikan strategi hybrid dari awal — model kecil lokal buat kerjaan
rutin, Claude API sebagai cadangan buat kasus yang butuh nalar lebih dalam.

## 3. Keputusan: lokal dulu, pakai Ollama + Claude Code

User sudah install Ollama, dan memutuskan pakai **Claude Code** buat bantu
proses pembuatan kodenya. Titik mulai: susun `CLAUDE.md` dulu sebagai project
brief yang bakal dibaca Claude Code otomatis.

## 4. CLAUDE.md versi pertama

Dibuat `CLAUDE.md` dan `.env.example` — arsitektur 3 lapis, hybrid routing,
tech stack, dan yang paling penting: **safety rules buat file operations**
(no permanent delete — selalu ke `_Quarantine/`, whitelist bukan blacklist,
audit log tiap aksi, batch action butuh konfirmasi eksplisit). Model default
yang direkomendasikan waktu itu: `gemma4:e4b`, hasil riset karena
disebut cocok untuk tool-calling di hardware terbatas.

## 5. Koreksi pertama — ternyata sudah ada model terpasang

*(diperbaiki: ditandai bahwa ini akan dikoreksi lagi di §7)*

User kasih tahu sudah pernah download `llama3.1:8b`, `qwen2.5`, dan `phi`.
CLAUDE.md direvisi: `qwen2.5` (diasumsikan versi 7B) jadi default baru,
`llama3.1:8b` jadi alternate, `phi` ditandai perlu dicek versinya (`phi3`?
`phi4-mini`? `phi4` 14B yang jauh lebih berat?). **Asumsi ini ternyata salah
— lihat §7.**

## 6. Pertanyaan soal storage vs RAM

User ragu apakah perlu download `gemma4` juga — takut kehabisan ruang.
Diklarifikasi: storage (474GB) dan RAM itu dua constraint yang beda total;
model yang cuma nongkrong di disk nggak makan RAM sama sekali, RAM cuma
relevan pas model itu benar-benar dijalankan. Kesimpulan: nggak perlu
download `gemma4`, apa yang sudah ada cukup.

## 7. Koreksi kedua — hasil `ollama list` yang sebenarnya

User jalanin `ollama list`, dan ternyata:

``` bash
qwen2.5:3b     1.9 GB
phi3:mini      2.2 GB
llama3.1:8b    4.9 GB
llama3.2:3b    2.0 GB
```

`qwen2.5` ternyata versi **3B**, bukan 7B — mengubah kalkulasi. `phi3:mini`
terkonfirmasi versi ringan (bukan `phi4` 14B). Ditemukan bonus:
`llama3.2:3b` yang belum disebut sebelumnya. Rekomendasi direvisi:
**`llama3.1:8b`** jadi default final (paling besar dan paling matang
tool-calling-nya dari yang tersedia), tiga model ~2GB lainnya disimpan
sebagai kandidat "fast triage tier" buat nanti. OS Windows juga otomatis
terkonfirmasi dari prompt terminal (`C:\Users\mirza>`).

**Pelajaran:** `gemma4:e4b` yang direkomendasikan di §4 ternyata bukan tag
Ollama yang nyata. Verifikasi dulu sebelum percaya rekomendasi — bahkan
rekomendasi yang datang dari sumber yang terlihat kredibel.

## 8. Klarifikasi soal workflow Claude Code

Muncul kesalahpahaman: "prompt" yang dimaksud user sejak awal ternyata
bukan system prompt agent, tapi prompt buat di-paste ke Claude Code. Riset
dokumentasi resmi Claude Code menghasilkan rekomendasi workflow
**Explore → Plan → Implement → Commit**, cara masuk plan mode
(`Shift+Tab`), pentingnya git (checkpoint Claude Code bukan pengganti git),
dan draft prompt kickoff pertama buat Phase 1.

## 9. Plan.md pertama — hasil eksplorasi Claude Code

User masuk plan mode, cuma ketik "start", dan Claude Code menghasilkan
`plan.md` yang jauh lebih matang dari dugaan — keputusan "rules first, LLM
second" buat classifier, idempotency guard, penanganan file locked ala
Windows, hallucination guard buat output LLM. Direview dan dipuji, tapi dua
hal ditandai perlu diverifikasi.

**Status verifikasi (diperbaiki dari devlog asli):**

1. *Apakah CLAUDE.md yang terbaca masih versi lama (`gemma4`)?* —
   **Terverifikasi.** CLAUDE.md di repo sekarang berisi `llama3.1:8b`,
   Windows 11, dan struktur repo yang benar. Revisi dilakukan sebelum
   Phase 1 dibangun.
2. *Apakah keputusan "subfolder di dalam watched folder" benar-benar
   dikonfirmasi user atau cuma asumsi?* — **Terverifikasi.** Di `docs/archive/PHASE_1.md`
   tercatat eksplisit: *"Confirmed with the user: ... organized files land in
   subfolders inside the watched folder, not a separate root."*

## 10. Sesi hilang, lalu dipulihkan

Terminal Claude Code sempat tertutup, sesi dikira hilang. Solusi: coba
`claude --continue` / `claude --resume` dulu sebelum mengulang dari nol —
Claude Code memang menyimpan sesi secara lokal. Sebagai jaga-jaga, `plan.md`
dibuat ulang sebagai backup dari isi yang sudah diupload sebelumnya. Prompt
kickoff baru disusun: bukan "explore dan susun plan," tapi "verifikasi plan
yang sudah ada, lalu jalankan" — supaya kerja yang sudah bagus nggak
terbuang percuma.

## 11. Phase 1 selesai dibangun

User upload `README.md` yang menandakan **Phase 1 selesai** dibangun.
Disusun **6 langkah verifikasi** berurutan: unit test → dry run ke Downloads
asli → execute di folder sandbox → cek idempotency → cek fallback saat
Ollama mati → baru execute ke Downloads asli. Ditambah tawaran review kode
manual buat tiga file paling kritis (`safety.py`, `organize_files.py`,
`llm.py`), dan saran commit git setelah semua lolos.

## 12. Troubleshooting — nyasar di Python REPL

Percobaan pertama gagal dengan `SyntaxError` — ternyata user nggak sengaja
masuk ke dalam interpreter Python (`>>>`) alih-alih shell biasa. Dijelaskan
perbedaannya dan cara keluar (`exit()`).

## 13. Troubleshooting — kebingungan nama folder

Percobaan kedua: user bikin folder fisik namanya persis **"WATCHED_FOLDERS"**
di dalam Downloads, mengira itu instruksi bikin folder — padahal maksudnya
update *nilai* variabel `WATCHED_FOLDERS` di `.env`. Diluruskan
kesalahpahamannya (salah penjelasan sebelumnya), dan output dry run-nya
sendiri dikonfirmasi sehat: 16 file terklasifikasi benar, nol perubahan disk.

## 14. Rekap lengkap 7 fase roadmap

User minta rekap semua fase yang direncanakan. Dijelaskan ketujuhnya dengan
target masing-masing: **Phase 1** (organizer inti — selesai, masih
verifikasi), **Phase 2** (chat loop + tool-calling), **Phase 3** (routing
lokal/cloud), **Phase 4** (`watchdog` background), **Phase 5** (Office
helpers), **Phase 6** (integrasi Canva), **Phase 7** (desktop shell/system
tray) — dibingkai sebagai satu alur besar: otak inti → jadi proaktif →
skill baru → jadi produk beneran.

## 15. Scoping ulang Phase 2

User mendeskripsikan Phase 2 versi lebih detail: chat looping, file
management umum (move/delete/add/rename), dan terminal interface yang rapi
seperti Claude Code. Ini lebih besar dari satu baris deskripsi awal, jadi
disusun `docs/PHASE_2.md` terpisah — tool baru yang dibutuhkan (Phase 1 cuma
punya satu operasi batch, Phase 2 butuh operasi per-file), rekomendasi
**Rich + prompt_toolkit** buat UI (dengan `Textual` sebagai opsi upgrade
nanti), safety carry-over dari Phase 1, dan tiga keputusan default biar
nggak nge-block progress. Roadmap di CLAUDE.md ikut di-update.

## 16. Phase 1 diverifikasi dan diaudit — 29 Agustus 2026 *(baru)*

Setelah Phase 1 selesai dibangun, dilakukan verifikasi lebih dalam dan
menghasilkan tiga artefak yang bertanggal **2026-08-29** (dikonfirmasi dari
modified-date file):

**`docs/ARCHITECTURE.md`** — diagram arsitektur **berdasarkan kode yang
benar-benar ada**, bukan yang direncanakan. Aturannya eksplisit: komponen
yang belum diimplementasi tidak digambar sebagai bagian arsitektur. Berisi
dua diagram Mermaid (overview + detail interaksi 24 koneksi antar-komponen),
tabel titik integrasi eksternal, dan daftar "yang belum terhubung" (routing
placeholder, `system_prompt.md`, chat loop, Claude API client).

**`docs/archive/AUDIT_REPORT.md`** — audit teknis 12 komponen Phase 1 dengan rubrik
kompleksitas tiga sumbu (LOC, branching, dependency internal). Hasilnya:
3 komponen `Simple`, 4 `Medium`, 4 `Complex`, 1 placeholder. Berisi juga
**9 observasi teknis** — termasuk temuan bahwa `plan_moves()` dan
`assert_allowed()` terdefinisi tapi tidak pernah dipanggil, `quarantine_folder`
dan `anthropic_api_key` dibaca dari `.env` tapi belum dikonsumsi, dan label
`tier="rule"` yang keliru pada file yang jatuh ke `Other`.

**`docs/COMPONENT_CHECKLIST.md`** — 12 komponen diurutkan berdasarkan prioritas
review (dari yang paling berisiko ke paling perifer). Tiap komponen punya
status pemahaman (Paham Penuh / Perlu Review / AI-generated) dan 1–2
pertanyaan reflektif yang harus dijawab **tanpa buka kode**. Kolom status
sengaja dikosongkan — diisi manual.

**Pelajaran:** audit yang jujur tidak nyaman. Menemukan bahwa dua fungsi
terdefinisi tapi tidak dipakai, dan satu label salah, lebih berguna daripada
audit yang bilang "semua bagus".

## 17. Rekonsiliasi dokumen — 10 September 2026 *(baru)*

Seiring bertambahnya dokumen (`PHASE 1`, `PHASE 2`, `MILESTONES_2026`,
`Roadmap_Tracker`, tiga artefak audit), muncul masalah baru: **dokumen-
dokumen mulai saling bertentangan**. Dua definisi September muncul
sekaligus — `MILESTONES_2026.md` bilang "Phase 2", `Roadmap_Tracker` bilang
"stabilisasi + dokumentasi" (yang sebenarnya isi Phase 1 dan sudah selesai).

Rekonsiliasi dilakukan dengan urutan:

1. Kumpulkan semua dokumen yang relevan (8 file)
2. Identifikasi konflik secara eksplisit (5 inkonsistensi ditemukan)
3. Tanyakan ambiguitas ke pemilik keputusan — tidak menebak
4. Baru tulis revisi

**Keputusan yang diambil:**

- `Roadmap_Tracker` jadi **acuan milestone tunggal**. `MILESTONES_2026.md`
  di-drop dari referensi aktif.
- September = **Phase 2 selesai + Phase 1 distabilkan sekaligus**. Dua jalur
  paralel: Jalur A (Build, sebelum Claude Code habis 9 Sep) dan Jalur B
  (Stabilkan, mandiri setelahnya).
- Fase 0 ditutup — item terakhir dicentang karena tabelnya sudah ada di
  `COMPONENT_CHECKLIST.md`.
- Buffer ditambahkan (27–30 Sep) sebagai ruang wrap-up.

**Pelajaran:** dua dokumen yang saling bertentangan lebih buruk daripada
satu dokumen yang tidak sempurna. Dan satu acuan tunggal lebih berharga
daripada banyak dokumen yang lengkap tapi tidak sinkron.

## 18. Sekarang — 10 September 2026 *(menggantikan §16 versi lama)*

*(ditulis ringkas, sesuai permintaan)*

Setelah Phase 2 requirements disusun, fokus pindah ke tiga hal:

1. **Verifikasi Phase 1** — menghasilkan `ARCHITECTURE.md`, `AUDIT_REPORT.md`,
   `COMPONENT_CHECKLIST.md` (§16).
2. **Rekonsiliasi roadmap** — menyelaraskan dokumen yang mulai bertentangan
   dan menetapkan `Roadmap_Tracker` sebagai acuan tunggal (§17).
3. **Persiapan stabilisasi** — memutuskan struktur repo dan cara
   mendokumentasikan perjalanan project untuk dibaca ulang di masa depan.

**Yang belum selesai dan perlu dikerjakan berikutnya:**

- Menjalankan ulang roadmap dengan September sebagai Phase 2 + stabilisasi
- Mengisi `COMPONENT_CHECKLIST.md` (kolom status + jawab pertanyaan reflektif)
- Rebuild 1 modul Phase 1 secara manual (prioritas: `organize_files.py` atau
  `safety.py`)
- Rapikan struktur repo untuk dibaca agent berikutnya
- Mengisi `DEVLOG.md` ini di bulan-bulan berikutnya

---

## Lampiran A — Artefak yang Ada di Repo

*(baru — untuk memudahkan pembaca berikutnya menemukan apa yang ada di mana)*

| File                     | Tanggal    | Isi                                                          |
| ------------------------ | ---------- | ------------------------------------------------------------ |
| `CLAUDE.md`              | —          | Project brief, safety rules, tech stack, roadmap 7 fase      |
| `docs/archive/PHASE_1.md`     | —          | Rencana teknis Phase 1 (scan → classify → dry-run → execute) |
| `docs/PHASE_2.md`             | —          | Requirements Phase 2 (chat agent, 4 tool baru, Rich UI)      |
| `docs/ARCHITECTURE.md`        | 2026-08-29 | Diagram arsitektur berdasarkan kode nyata Phase 1            |
| `docs/archive/AUDIT_REPORT.md`| 2026-08-29 | Audit teknis 12 komponen + 9 observasi                       |
| `docs/COMPONENT_CHECKLIST.md` | —          | Checklist review pemahaman per komponen                      |
| `docs/ROADMAP.md`             | 2026-09-10 | Penunjuk roadmap/tracker yang dikelola di Notion             |
| `MILESTONES_2026.md`     | —          | Timeline Agustus–Desember (di-drop, tidak jadi acuan)        |
| `docs/DEVLOG.md`          | 2026-09-10 | Dokumen ini                                                  |

## Lampiran B — Pelajaran yang Tercatat

*(baru — kumpulan pelajaran dari seluruh devlog, biar tidak tenggelam di narasi)*

1. **Verifikasi sebelum percaya rekomendasi.** `gemma4:e4b` bukan tag nyata;
   baru ketahuan setelah `ollama list`. (7)
2. **Dua constraint yang beda jangan dicampur.** Storage dan RAM tidak
   berhubungan langsung; model di disk tidak makan RAM. (6)
3. **Audit yang jujur tidak nyaman, tapi berguna.** Menemukan fungsi yang
   tidak dipakai dan label yang salah lebih berharga dari "semua bagus". (16)
4. **Satu acuan tunggal.** Dua dokumen yang bertentangan lebih buruk dari
   satu dokumen yang tidak sempurna. (17)
5. **Reverse engineering itu scaffolding, bukan tujuan.** Progres:
   AI membuat → aku memahami → aku memodifikasi → aku mendesain → aku
   membangun. (Prinsip dari `Roadmap_Tracker`)
---
