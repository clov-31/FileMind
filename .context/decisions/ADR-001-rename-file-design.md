```markdown
# ADR-001 — rename_file() Design Freeze

**Status:** ACCEPTED
**Date:** 2026-09-15
**Supersedes:** —
**Related:** TASK-0021, TASK-0022

---

## Context

TASK-0023 (rename_file) direncanakan pada sesi arsitek sebelumnya
dengan agent Cursor. Plan tersebut dihasilkan sebelum builder session
dimulai, namun sesi Cursor terhenti karena limit. Plan sudah detail dan
layak dijadikan keputusan arsitektur, bukan sekadar draft sementara.

Karena builder selanjutnya adalah LLM stateless (DeepSeek free plan)
yang tidak bisa membaca repo atau menjalankan test, plan ini perlu
di-freeze sebagai ADR agar tidak di-redesign oleh builder.

---

## Decision

### Signature

```python
rename_file(path, new_name, config, *, dry_run=True, audit=None, tier="local") -> dict
```

Return dict mengikuti pola `move_file()` dan `delete_file()`:
`{success, message, data}`.

### Refusal List (Final)

`rename_file()` menolak operasi jika:

1. `path` invalid (gagal `validate_path`)
2. `path` out-of-root
3. `path` tidak ada
4. `path` bukan file reguler (directory, device, dll)
5. `path` berada di dalam quarantine dir
6. `path` adalah symlink yang menunjuk keluar root
7. `new_name` kosong setelah `.strip()`
8. `new_name` == `"."` atau `".."`
9. `new_name` mengandung `/` atau `\`
10. `new_name` mengandung `".."` di mana pun (termasuk di tengah,
    contoh: `foo..bar.txt` → TOLAK)
11. `src.name == new_name` (no-op, case-sensitive)

### Collision Strategy

- Target exists → resolve dengan suffix `(1)`, `(2)`, dst — sama seperti
  `move_file()`.
- **Case-only rename di Windows** BUKAN collision. Deteksi: nama beda
  case, parent sama. Implementasi: rename ke temp unique name di parent,
  lalu rename ke nama final.

### Dry-Run Contract

- `dry_run=True` (default).
- Tidak `rename` / `link` / `unlink` file user.
- Tidak `mkdir` user dir.
- Audit tetap ditulis: `planned` → `ok` dengan `detail="dry_run"`.
- Side effect FS: hanya tulis audit (+ `AuditLog` boleh `mkdir` parent
  log). Ini **keputusan eksplisit**, bukan ambiguitas. Harus dipin
  dengan test.

### Audit Order

- Execute: `planned` → `attempt` → `ok` / `failed`.
- Case-only rename: dua tahap, masing-masing dengan `planned` sendiri.
- Refusal: `skipped` hanya jika `dry_run=False`. Konsisten dengan
  `move_file()` dan `delete_file()`.

### Target Path Validation

- `new_name` bukan path → **tidak** `validate_path(new_name)`.
- `dst = parent / new_name`.
- `temp` divalidasi dengan `must_exist=False`.
- **Tidak ada exemption.** Semua path yang masuk `validate_path` memang
  harus lewat `validate_path`.

### Filesystem Primitives

- **Tidak** pakai `os.rename`, `os.replace`, atau `shutil.move` ke
  user path.
- Claim nama via `os.link` lalu `os.unlink` source.
- Sama dengan `_move_without_overwrite` di `move_file.py`.

---

## Keputusan atas Pertanyaan Terbuka dari Plan Cursor

| Pertanyaan | Keputusan | Alasan |
|---|---|---|
| Task file di `planned/` atau `active/`? | **`active/`** | Konsistensi struktur `.context/tasks/`. |
| `new_name` berisi `..` di tengah? | **TOLAK** (literal contains `..`) | Sederhana, aman, tidak ada false negative berbahaya. |
| `new_name` hanya whitespace? | **TOLAK sebagai empty** setelah `.strip()` | Whitespace-only filename tidak valid di FS modern. |

---

## Consequences

### Positif
- Builder LLM tidak perlu mendesain ulang. Tinggal implementasi.
- Evaluator punya baseline konkret untuk menilai deviasi.
- Konsisten dengan pola `move_file()` dan `delete_file()`.

### Negatif
- Kalau ada edge case baru di runtime, harus buka ADR baru atau
  amend ADR ini, bukan improvisasi di builder session.
- Case-only rename di Windows menambah kompleksitas (dua tahap rename).

### Netral
- `RenameResult` di task file dipetakan ke `dict` (pola `move_file`).
  Ini konsisten, bukan deviasi.

---

## Lessons From TASK-0022 (Binding)

Builder **wajib** menerapkan:

- **F-1:** Test symlink-out-of-root eksplisit (skipif Windows tanpa
  privilege).
- **F-2:** Collision test harus memaksa collision (monkeypatch datetime
  atau pre-create exact candidate). Tidak boleh assertion vacuous.
- **F-3:** Dry-run side-effect contract sudah diputuskan di atas. Pin
  dengan test.
- **F-4:** Kalau ada infra dir creation, log `planned` dulu ATAU
  dokumentasikan bahwa infra-dir creation di luar audited operation.
  Pin dengan test.
- **F-5:** Tidak ada exemption `validate_path`. Dokumentasikan di
  `current_state.md`.

---

## References

- `.context/tasks/active/TASK-0023-rename-file.md`
- `agent/tools/move_file.py`
- `agent/tools/delete_file.py`
- `S-0022-EVAL-001-DeepSeek.md`
- Plan Cursor (S-0023-ARC-001, arsip)