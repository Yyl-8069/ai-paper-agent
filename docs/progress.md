# SDD ledger — plan: docs/plan.md

Spec: docs/design.md. User approved design and requested installation/development.
Execution: native, separate repository, feat/ai-paper-agent; no existing base branch or remote to integrate.
User correction: all product source, runtime, environment, caches and library on D. Migrated to D:/codex/projects/ai-paper-agent, repaired virtual environment, removed this task's C project copy.
User decision: DeepSeek API for summaries; local PDF extraction. API key not supplied or printed.
User decision: Sunday 21:00 Beijing weekly summary.

Pre-flight: Store refs shared by collection, conversion, reports and cleanup; all use P000001/v1 strings.
Ruling: use dictionary records and string refs rather than unused dataclass hierarchy; validation at input boundaries.
Ruling: single model for summaries, explicit workflow instead of adding CrewAI dependency; reuse original sample's real PyMarkdownApi scanner.
Ruling: user chooses candidates in menu; current source sorting is date or observed community votes, not an unverified AI hot ranking.
Task 1: hardware 15.9 GiB RAM; MX150 2 GiB VRAM. Isolated Python 3.11.18 installed.
Task 1: PyMuPDF4LLM 2.0 package had no importable module; pinned tested 0.0.27 with PyMuPDF 1.26.7. No large OCR/GPU model.
Task 2: store/version/path/concurrency tests RED then GREEN; root commit 0436a68.
Task 3: source/download tests RED then GREEN; real arXiv and HF API results 2 each.
Task 4: real PDF conversion and scan tests RED then GREEN; 15page arXiv 1706.03762v1 actually downloaded and converted.
Ruling: MD022 reports heading line 1, not following paragraph line 2; inspected actual API result before correcting test expectation.
Task 5: report/DeepSeek schema/reference tests RED then GREEN. Real paid API and research-quality evaluation not run because no key supplied.
Task 6: weekly boundary, late collection and deleted-report tests RED then GREEN; scheduling scripts written. OS denied task installation, task NOT active.
Ruling: Sunday 21:00 report is explicitly a current-week snapshot; later same-week collections trigger a supplementary report next run, old version retained.
Task 7: four cleanup modes, changed-file rejection, partial failure, shared report tests RED then GREEN. No user data deleted.
Final fresh reviewer: 4 findings: shared dependency syntax/report coverage, dependency recheck, PDF restore, historical report suppression.
Final fix pass: added 6 failing regression cases, repaired all 4 findings; full suite 38 passed.
Ruling: conservative filename matching preserves images referenced by retained Markdown/HTML/reports, including encoded filenames; may keep extra assets with identical names.
Schedule installation requires user administrator action; code includes install-weekly.cmd and records exact Windows denial.
No main branch, remote, push, deployment or automatic collection/deletion created.

FastAPI continuation 2026-10-31: local web/API implemented; 50 tests pass. Actual localhost endpoints and browser arXiv search verified. Single-instance OS lock prevents false interrupted status on duplicate startup; public errors never persist raw exceptions. Service running on127.0.0.1:8000; no paid model calls.
