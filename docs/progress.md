# SDD ledger — plan: ../ai-paper-agent-plan.md

Execution: native, user requested installation/development on 2026-10-30.
Spec: ../ai-paper-agent-design.md, user approved.
Pre-flight: Store refs shared by collection, conversion, reports and cleanup; all use P000001/v1 strings.
Ruling: use string refs and typed dictionary records rather than unused dataclass hierarchy — minimal shared API; validate trust boundaries.
Ruling: develop in a separate Git repo in writable artifact directory, deliver copy to D:/codex/projects/ai-paper-agent — avoid placing product in skills repo.
Task 1: hardware 15.9 GiB RAM, 4.4 GiB available; MX150 2 GiB VRAM. No suitable preinstalled Python beyond 3.8.
Task 1: isolated Python 3.11.18 installed with uv; CPU-only PyMuPDF4LLM 0.0.27 and PyMuPDF 1.26.7 chosen after 2.0 package had no importable module.
Ruling: avoid large GPU/OCR models on this machine; formulas, scanned PDFs and table fidelity require review. No claim of perfect conversion.
Model configuration pending user response; no online model call or document upload authorized.
Schedule installation deferred until time selected. No automatic collection or deletion.
