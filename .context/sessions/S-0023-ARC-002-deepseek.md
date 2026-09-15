# S-0023-ARC-001

session_id: S-0023-ARC-002
task_id: TASK-0023

role: architect
phase: planning

agent: DeepSeek
mode: ai-assisted

started_at: 2026-09-15

objective:
  Menyusun TASK-0023 rename_file(), prompt builder/evaluator/testing/
  documentation, dan ADR-004 sebagai freeze plan. Revisi dari rencana
  awal (Cursor) karena sesi Cursor terhenti.

context:
  phase: 2
  depends_on:
    - TASK-0021 (move_file, conditional_pass)
    - TASK-0022 (delete_file, conditional_pass; F-1..F-10)
  related_adr: ADR-003-quarantine-not-delete
  previous_session: S-0023-ARC-001 (plan Cursor, arsip)

inputs:
  - Project Context (ChatGPT).md
  - S-0022-EVAL-001-DeepSeek.md
  - TASK-0022-delete-file.md
  - Plan Cursor (paste, arsip)

actions:
  - Ekstrak pola task file & evaluasi dari TASK-0022 / S-0022-EVAL-001.
  - Freeze plan Cursor menjadi ADR-004.
  - Putuskan 3 pertanyaan terbuka Cursor.
  - Susun prompt builder, evaluator, testing, documentation.
  - Susun template prompt builder reusable.
  - Rekam sesi.

decisions:
  - rename_file() = rename in-place. Cross-dir → move_file().
  - Rename TIDAK menggunakan quarantine.
  - Collision → suffix "(1)", "(2)", dst. Case-only Windows bukan
    collision (pakai temp intermediate).
  - Dry-run default True. Contract: hanya audit yang ditulis, tidak
    menyentuh file user. Dipin dengan test.
  - Audit order: planned → attempt → ok/failed. Refusal → skipped
    hanya jika dry_run=False.
  - new_name bukan path → tidak validate_path(new_name).
  - src == dst → tolak (no-op).
  - new_name mengandung ".." di tengah → tolak.
  - new_name whitespace-only → tolak sebagai empty.
  - Task file dipindah ke .context/tasks/active/.
  - Builder = DeepSeek (free plan), bukan Cursor.

open_decisions:
  - none. Semua pertanyaan Cursor sudah diputuskan di ADR-004.

outputs:
  - .context/tasks/active/TASK-0023-rename-file.md
  - .context/decisions/ADR-004-rename-file-design.md
  - .context/prompts/S-0023-BLD-001-deepseek.txt
  - .context/prompts/S-0023-EVL-001-deepseek.txt
  - .context/prompts/S-0023-TST-001.txt
  - .context/prompts/S-0023-DOC-001.txt
  - .context/prompts/_TEMPLATE-builder-deepseek.txt
  - .context/sessions/S-0023-ARC-001-DeepSeek.md

workflow_4_sesi:
  - S-0023-BLD-001: Builder (DeepSeek)
  - S-0023-EVL-001: Evaluator (DeepSeek)
  - S-0023-TST-001: Testing (Human + DeepSeek)
  - S-0023-DOC-001: Documentation (Human + DeepSeek)

context_budget:
  builder:
    wajib:
      - AI_CONTEXT.md
      - current_state.md
      - TASK-0023-rename-file.md
      - ADR-004
      - safety.py
      - audit.py
      - move_file.py
      - delete_file.py
      - test_move_file.py
      - test_delete_file.py
    opsional:
      - config.py
      - tools/__init__.py
    jangan:
      - DEVLOG.md
      - ROADMAP.md
      - PHASE_1.md
      - PHASE_2.md
      - ARCHITECTURE.md
      - session notes lain
  evaluator:
    wajib:
      - TASK-0023-rename-file.md
      - ADR-004
      - rename_file.py
      - test_rename_file.py
      - output pytest
      - breadcrumb
      - session note builder
      - safety.py
      - audit.py
      - move_file.py
      - delete_file.py
  testing:
    - task file + ADR + source + test + output pytest + findings EVL
  documentation:
    - semua artefak 3 sesi sebelumnya + git log + draft lessons human

perubahan_dari_rencana_awal:
  - Builder: Cursor → DeepSeek (free plan). Output berupa blok teks,
    bukan file langsung. Human copy-paste.
  - Verifikasi pytest: otomatis → manual oleh human. Max 3 iterasi error.
  - "STOP. Tunggu approval." di prompt Cursor → dihapus, diganti
    "PLAN dulu, lalu output".
  - Evaluator: Cursor baca repo → human paste source + test + output.
  - Session note filename: Cursor → DeepSeek.
  - Plan Cursor di-freeze jadi ADR-004.

next:
  - S-0023-BLD-001 (Builder, DeepSeek) — jalankan prompt builder
  - S-0023-EVL-001 (Evaluator, DeepSeek)
  - S-0023-TST-001 (Testing, Human + DeepSeek)
  - S-0023-DOC-001 (Documentation, Human + DeepSeek)

notes:
  - Prompt builder sengaja tidak minta approval karena LLM stateless
    tidak punya state "menunggu". Approval dilakukan human di level
    keputusan: baca PLAN, kalau setuju lanjut.
  - Loop error manual dibatasi 3 iterasi untuk mencegah token waste.
  - Lessons Learned tetap milik human. LLM hanya editor.
  - Semua prompt berformat .txt agar mudah di-copy-paste dan
    tidak tercampur dengan markdown session note.