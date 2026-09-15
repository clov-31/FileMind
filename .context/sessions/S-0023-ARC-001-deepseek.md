# S-0023-ARC-001

session_id: S-0023-ARC-001
task_id: TASK-0023

role: architect
phase: planning

agent: DeepSeek
mode: ai-assisted

started_at: 2026-09-15

objective:
  Menyusun TASK-0023 rename_file() dan prompt Cursor builder
  dengan prinsip token efficiency & context budget.

context:
  phase: 2
  depends_on:
    - TASK-0021 (move_file, conditional_pass)
    - TASK-0022 (delete_file, conditional_pass; F-1..F-10)
  related_adr: ADR-003-quarantine-not-delete (tidak berlaku untuk rename)

inputs:
  - Project Context (ChatGPT).md
  - S-0022-EVAL-001-DeepSeek.md
  - TASK-0022-delete-file.md

actions:
  - Ekstrak pola task file & evaluasi dari TASK-0022 / S-0022-EVAL-001.
  - Tetapkan scope rename_file() = rename in-place (bukan move).
  - Susun Acceptance Criteria, Edge Cases, Lessons From TASK-0022.
  - Susun prompt Cursor .txt dengan Context Budget eksplisit.
  - Rekam sesi.

decisions:
  - rename_file() TIDAK memindahkan antar folder. Cross-dir → move_file().
  - Rename TIDAK menggunakan quarantine (bukan destructive).
  - Rename TIDAK overwrite. Collision → suffix "(1)", "(2)", dst.
  - Dry-run default True. Contract side-effect harus diputuskan Builder
    dan dipin dengan test (menutup celah F-3 dari TASK-0022).
  - src == dst → tolak (no-op).
  - Case-only rename di Windows → support via temp intermediate.
  - Symlink-out-of-root → tolak lewat validate_path, dengan test eksplisit
    (menutup celah F-1 dari TASK-0022).

open_decisions:
  - Apakah dry_run=True boleh menyentuh FS via AuditLog init?
    (Builder putuskan, dokumentasikan, pin dengan test.)
  - Apakah infra-dir creation di-log "planned" dulu, atau dinyatakan
    di luar audited operation?
  - Apakah new_name perlu validasi terpisah dari validate_path,
    atau validate_path cukup?

outputs:
  - .context/tasks/active/TASK-0023-rename-file.md
  - .context/prompts/S-0023-BLD-001-cursor.txt
  - .context/sessions/S-0023-ARC-001-DeepSeek.md

next:
  - S-0023-BLD-001 (Builder, Cursor)
  - S-0023-EVL-001 (Evaluator, Cursor)
  - S-0023-TST-001 (Testing, Human + LLM)
  - S-0023-DOC-001 (Documentation, Human + LLM)

notes:
  - Prompt Cursor sengaja pakai blok "STOP. Tunggu approval."
    untuk mematuhi Breadcrumb Protocol (plan → approval → implement).
  - Context Budget di prompt adalah kontrak: kalau Cursor butuh
    file di luar daftar, dia harus minta dulu ke user.