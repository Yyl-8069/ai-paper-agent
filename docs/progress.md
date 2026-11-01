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

Frontend iteration 2026-11-01: adopted the generic Agency Frontend Developer role for read-only design and final source review; no other project business constraints imported. Light academic workspace implemented in the existing HTML/CSS/JS with real API counters and no added dependencies. Existing API bindings and permanent deletion preview/confirmation preserved. Full suite: 50 passed; node syntax check passed; HTML ID/binding checks passed. Live narrow viewport and library anchor verified; zero-file cleanup preview disables deletion and cancel hides preview. No actual collection, paid API request or deletion performed; desktop-wide visual and performance measurements not completed.

Translation iteration 2026-11-01: user approved full-text Chinese translation and five calendar ranges. Added dedicated prompt and model translation method, chunked workflow, authenticated background API, per-paper UI translate/view/download, existing Markdown artifact cleanup integration, C-drive storage guard and project-local runtime temp. Calendar month/year use Beijing time and clipped month-end; current HF candidate pool is date-filtered, not a historical ranking archive. New tests observed failing before implementation; orphan-output refusal also reproduced then fixed. Full suite 59 passed (one existing Starlette httpx deprecation warning); node syntax and git diff checks passed. No real paid translation; real semantic quality/cost not evaluated. A C-drive empty test database created while reproducing the old behavior was removed; final guard rejects before directory creation.
Live UI verification: five range choices present and year selection confirmed. Separate D-drive test library on temporary port 8001 showed per-paper translate button, translated download link and expanded local Chinese text. Test service stopped; production service restarted on 8000 and healthy, production library remained empty. No user papers or model key were used.

Keyword search iteration 2026-11-01: user approved historical title/abstract relevance search with editable OR alternatives and pagination, and requested faster response/clearer button feedback. Implemented related mode, default all-time UI, preserved latest/hot modes, isolated per-page collection snapshots, bounded 5-minute/100-entry cache, wait counter and disabled buttons, safe upstream timeout/error messages. Three initial regression tests observed failing; timeout reproduction also observed before adding handlers. Full suite 64 passed, node syntax and diff checks passed. Live harness query returned old papers (June/September 2026), totalResults 12416 from source (broad lexical matches, not AI-only relevance guarantee). Tool latency 1.05s; browser first page 1.1s, next page 1.0s, cached previous page 0.0s rounded. Temporary port 8001 used isolated D-drive library; no paid API or collection. Production terminal service not replaced by a background instance.

README focus correction 2026-11-01: user reaffirmed Markdown skill application as primary purpose. Audited collection/import, translation, brief and weekly call sites. README now leads with deterministic validation, shared rules, JSON fields, four integration points, architecture and limitations. Distinguishes PyMarkdown tool integration from full CrewAI execution or installed SKILL.md package. No runtime code changed.

README simplification 2026-11-01: user requested less prose and explicit Markdown check scope. Replaced long README with concise scope table, implementation entry, startup, file locations, verification and limits; detailed iteration history remains in this ledger. Documentation only.
