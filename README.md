<p align="center">
  <img src="./assets/atlas-mark.svg" width="72" alt="Atlas" />
</p>

<h1 align="center">Atlas</h1>

<p align="center">
  An agentic reading companion that builds personalized learning paths,<br>
  verifies book information, supports active study, and adapts from learner feedback.
</p>

<p align="center">
  <sub>Python · LangGraph · Streamlit · AWS Bedrock · SQLite</sub>
</p>

---

## What Atlas does

Most reading tools stop at a recommendation. Atlas keeps the learning loop going.

**Understand your goals → Find & verify books → Read & practise → Review & adapt**

- **Personalized paths** — builds a staged reading route from a learner's topic, background, outcome, time and constraints.
- **Book verification** — checks catalogue identity and keeps source information visible instead of silently substituting titles.
- **Interactive learning** — supports book-specific questions, study coaching and mixed-format knowledge checks.
- **Adaptive planning** — preserves progress while allowing time changes, book replacements and versioned plan updates.
- **Bilingual workflow** — supports English and Chinese interfaces with language-specific saved work.

Atlas was built by **NexMind** as a hackathon proof of concept. It is a bounded agent workflow, not an unrestricted autonomous research agent or a production multi-user service.

## Quick start

Prerequisites: **Python 3.11+**, a modern browser, and internet access for the initial dependency installation.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe launch.py
```

### macOS, Linux or WSL

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python launch.py
```

Open the local URL printed by the launcher, normally `http://localhost:8501`.

The default is **demo mode**: it uses bundled catalogue examples and local, non-LLM behaviour, so no AWS credentials are required. External book images and source links may still require internet access.

The launcher does not install packages, rewrite `.env`, or overwrite an existing learning profile. Stop it with **Ctrl+C**. Use `--port 8502` if the default port is occupied, `--no-browser` to suppress automatic browser opening, or `--check` to validate prerequisites without starting the app.

Convenience wrappers are available as `powershell -File start.ps1` on Windows and `sh start.sh` on macOS/Linux/WSL. If `uv` is already installed, `uv sync --frozen` followed by `uv run python launch.py` is also supported.

## Demo flow

For the quickest walkthrough, choose **Use example learning goals / 填入演示学习需求** and generate a path. The bundled example uses embodied intelligence, an electrical-engineering background with Python and basic machine learning, six weeks, and four hours per week.

A useful end-to-end flow is:

1. **Set a direction** — create a learning profile with topic, background, target outcome, time and optional requirements.
2. **Inspect the route** — generate a reading path and review books, source links, reasons and time estimates.
3. **Check a book** — search by title or ISBN and inspect Atlas's suitability assessment.
4. **Read and ask** — use book-specific discussion and learning tools.
5. **Practise** — generate single-choice, true/false and short-answer knowledge checks.
6. **Record progress** — save reading progress and continue from the current book and plan.
7. **Adapt** — change available time or replace a book while keeping historical plan versions.
8. **Switch languages** — repeat with a separate English or Chinese profile.

Bundled demo data covers a limited set of topics and should not be treated as evidence of live-model quality.

## Live catalogue and model mode

Live mode uses your own authorised service access. Requests can incur model charges and send relevant goals, background, questions and excerpts to the configured provider.

1. Copy `.env.example` to `.env` **only if `.env` does not already exist**. Do not commit this file.
2. Set `LLM_PROVIDER=bedrock`, `AWS_REGION` and a permitted `BEDROCK_MODEL_ID`.
3. Optionally set `BEDROCK_LEARNING_MODEL_ID` for a separate tutoring model.
4. Supply AWS credentials through the standard environment or a local AWS profile.
5. Optionally set a Google Books API key in `GOOGLE_BOOKS_API_KEY`.
6. Launch with:

```bash
python launch.py --mode live
```

Demo mode uses `data/demo.db`. Live mode defaults to `data/nexmind_atlas.db`, or the path configured through `DATABASE_PATH`.

## Architecture

Atlas uses a bounded LangGraph workflow rather than open-ended autonomous reflection. The recommendation pipeline has explicit planning, retrieval, validation, selection and adaptation stages, with at most three search passes.

```text
Learner profile
      ↓
Goal + constraints
      ↓
Catalogue retrieval → identity checks → suitability assessment
      ↓
Personalized reading path
      ↓
Reading + questions + practice
      ↓
Progress and feedback
      └──────────────→ plan update / replacement / next step
```

The stack is **Python, Streamlit, LangGraph, Pydantic, httpx, boto3 / Amazon Bedrock and SQLite**. Exact runtime versions are pinned in `requirements.txt` and `uv.lock`; `requirements-dev.txt` contains test and lint dependencies.

## Behaviour and limits

- **Controlled agent workflow:** planning, retrieval, validation and selection are bounded; plan changes require an explicit learner action.
- **Catalogue sources are not full-book access:** descriptions and metadata do not establish complete chapter coverage or perfect relevance.
- **Practice can be fallible:** objective questions can be checked locally, while semantic short-answer review requires the live model.
- **Model failure stays visible:** unavailable semantic review is not presented as genuine model assessment.
- **Local prototype:** a learning-profile ID is not a login or security boundary; do not expose private profiles on a public server.
- **No background reminder service:** session follow-ups work inside the app; closing the app does not leave an always-on agent running.
- **No validated learning-gain claim:** deterministic tests and small live samples are engineering checks, not an external educational-effectiveness study.

## Verification

Install development dependencies before running the checks below (`uv sync --frozen` already includes them):

```bash
python -m pip install -r requirements-dev.txt
python launch.py --check
python -m pytest
python -m ruff check .
python -m scripts.preflight
```

The local preflight checks lint, tests, compilation, selected secret patterns and deterministic evaluation without calling Bedrock. Results are written to `evaluation_results/preflight_latest.json`.

An optional billable live integration check is available separately:

```bash
python -m scripts.run_live_evaluation --confirm-live-cost
```

`evaluation_results/latest.json` contains fixture-based deterministic results. `live_latest.json`, when present, is a dated historical sample rather than proof of current model quality. Broader external-review guidance is documented in `docs/human_evaluation_protocol.md`.

## Project map

| Path | Purpose |
| --- | --- |
| `launch.py`, `start.ps1`, `start.sh` | Cross-platform demo/live launch and local checks |
| `app.py`, `src/ui.py`, `src/hero_book.py`, `src/quiz_ui.py` | Bilingual application and interface components |
| `src/graph.py`, `src/services/` | Recommendation pipeline, matching, suitability and plan construction |
| `src/learning_review.py`, `src/diagnostic.py` | Practice, model review and labelled local fallback |
| `src/tools/`, `src/llm/` | Catalogue clients and structured model-provider interfaces |
| `src/database.py` | Local profiles, plans, progress, conversations and cache |
| `data/*.json`, `data/fixtures/` | Demonstration and evaluation inputs |
| `tests/`, `scripts/`, `evaluation_results/` | Reproducible checks and evaluation outputs |
| `docs/` | Architecture, handoff, QA and evaluation notes |

The final acceptance notes are in [`docs/final_acceptance_fixes_2026-09-05.md`](docs/final_acceptance_fixes_2026-09-05.md). The code package is separate from the slide deck and demo video; their starting materials are `docs/deck_outline.md` and `docs/demo_script.md`.
