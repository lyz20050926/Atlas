# NexMind Atlas

**Atlas helps a learner choose books, work through difficult ideas and adjust a reading plan as they learn.** NexMind is the project brand; the agent is called Atlas.

This is a bilingual, locally runnable hackathon proof of concept. Its bounded LangGraph workflow combines catalogue retrieval, book-identity checks, suitability assessment, learner feedback and explicit plan changes. It is not an unrestricted autonomous research agent or a production multi-user service.

## Start here: no AWS required

Prerequisites: **Python 3.11 or newer**, a modern browser, and internet access for the initial dependency installation. Open a terminal in the extracted project directory. No developer credentials, saved profile or database is needed.

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

Open the local URL printed by the launcher (normally `http://localhost:8501`). **The default is demo mode**, using bundled catalogue examples and local, non-LLM behaviour. It does not require AWS. Demo answers must not be presented as live Bedrock output or as evidence of model quality. External book images/source links may still need internet access.

The launcher does not install packages, rewrite `.env` or overwrite an existing learning profile. Stop it with **Ctrl+C**. If the default port is occupied, add `--port 8502`. Use `--no-browser` to suppress automatic browser opening, or `--check` to validate prerequisites without starting the server.

After installation, the convenience wrappers are `powershell -File start.ps1` on Windows and `sh start.sh` on macOS/Linux/WSL. They prefer the project virtual environment. For an existing uv installation, `uv sync --frozen` followed by `uv run python launch.py` is an alternative using `uv.lock`.

## What to try

| Step | Action | What to check |
| --- | --- | --- |
| 1. Set a direction | Create a learning profile. Enter your topic, background, intended outcome and optional **detailed interests and requirements** in free text. | Specific subfields and exclusions can be recorded; another profile's progress is not overwritten. |
| 2. Inspect the route | Generate a reading path and open each stage. | Books, catalogue identity, source links, reasons, time estimates and any unmet requirements are visible. Sample data is labelled. |
| 3. Check a book | Use the title/ISBN search after creating a route. | Atlas assesses an identified book; a missing or unrelated match should not be silently substituted. Demo lookup is limited to bundled examples. |
| 4. Read and ask | Open a book's conversation, then the learning tools. | Book-specific discussion is distinct from whole-path study coaching. Live mode is needed to evaluate open-ended model answers. |
| 5. Practise | Generate a knowledge check, answer a single-choice item, a true/false item and a short question. | Choices are not preselected. Unanswered items are not scored as mistakes. Objective answers can be checked locally; semantic short-answer review needs the live model. |
| 6. Follow through | Record progress or complete a reading session; inspect the follow-up. | Saved progress, a question/practice invitation and the next stage stay tied to the current book and plan. |
| 7. Adapt and return | Change available time or request a book replacement; inspect **History**. | A plan change creates a version; historical plans and saved progress remain available. |
| 8. Check both languages | Switch the interface in **Settings** and repeat with a separate profile. | Interface language, book-language preference and language-specific saved work remain distinct. |

For the quickest demo, click **Use example learning goals / 填入演示学习需求**, then generate the path. The example uses **Embodied intelligence / 具身智能**, an electrical-engineering background with Python and basic machine learning, six weeks and four hours per week. You can edit it before submitting. Bundled examples cover a limited set of topics, not every specialised request.

## Live catalogue and model mode

Use this only with your own authorised service access. Requests can incur model charges and send relevant goals, background, questions and excerpts to the configured provider.

1. Copy `.env.example` to `.env` **only if `.env` does not already exist**. Do not send or commit this file.
2. Set `LLM_PROVIDER=bedrock`, `AWS_REGION` and a permitted `BEDROCK_MODEL_ID`. Set `BEDROCK_LEARNING_MODEL_ID` if using a separate tutoring model; otherwise it uses the main model.
3. Supply AWS credentials through the standard environment or a local AWS profile; set `AWS_PROFILE` only when using that profile. The project does not provide credentials or model access. Refresh expired credentials through your own provider workflow.
4. Optionally set a Google Books API key restricted to that service in `GOOGLE_BOOKS_API_KEY`; shared unauthenticated quota may be unavailable.
5. Run the same virtual-environment Python with:

```bash
python launch.py --mode live
```

Here and in the commands below, `python` means the interpreter from the virtual environment created above. Live mode requires access to the configured external services; a launch configuration check is not proof that a model invocation will succeed.

Demo uses `data/demo.db`; live mode defaults to `data/nexmind_atlas.db`, or the explicitly configured `DATABASE_PATH`. These are local runtime files, not files supplied in the submission archive. Save personal data only on a trusted machine. See `.env.example` for timeout, retry, search-cap and cache settings.

## Behaviour and limits

- **Controlled agent workflow:** fixed planning/retrieval/validation/selection nodes, with at most three search passes. Limited cache supplementation is not open-ended model reflection. Book replacement and plan changes require an explicit learner action.
- **Sources are not full-book access:** catalogue identity and descriptions do not establish complete chapter coverage or perfect relevance. Atlas uses short supplied excerpts for passage-specific help; it does not scrape full books or bypass paywalls.
- **Practice remains fallible:** live questions undergo editorial and independent-answer checks with bounded repair. When these fail, Atlas labels general foundational exercises as a fallback. A correct selection score only confirms agreement with the stored answer key; it does not prove that the key is correct.
- **Model failure is visible:** local actions and objective checking can continue, but unavailable semantic review must not masquerade as genuine model assessment. Highly specialised or Chinese-language question generation can be slow or fall back; the dated QA notes describe observed failures.
- **Local prototype, not authenticated hosting:** a learning-profile ID is not a login or security boundary. Do not expose private profiles on a public server. There is no production authentication, backup service or uptime guarantee.
- **Reminder boundary:** checks and session follow-ups work in the app; closing the app does not leave an always-on agent sending email or operating-system reminders.
- **No validated learning-gain claim:** deterministic tests and small live samples are not an external educational-effectiveness study. Provider-specific privacy terms apply to live model inputs.

## Verify the delivered source

Install the separate locked test/development dependencies before running checks (`uv sync --frozen` already includes them):

```bash
python -m pip install -r requirements-dev.txt
python launch.py --check
python -m pytest
python -m ruff check .
python -m scripts.preflight
```

The local preflight checks lint, tests, compilation, selected secret patterns and deterministic evaluation without calling Bedrock. It produces `evaluation_results/preflight_latest.json`. Read its timestamp and individual outcomes; do not substitute an older green report for a final-source run.

The optional **billable** integration check is separate:

```bash
python -m scripts.run_live_evaluation --confirm-live-cost
```

`evaluation_results/latest.json` contains fixture-based deterministic results. `live_latest.json`, if included, is a **dated historical sample**, not a fresh result for the final archive. It does not imply human-validated relevance. Broader external-review guidance is in `docs/human_evaluation_protocol.md`.

## Project map

| Path | Purpose |
| --- | --- |
| `launch.py`, `start.ps1`, `start.sh` | Cross-platform demo/live launch and local checks. |
| `app.py`, `src/ui.py`, `src/hero_book.py`, `src/quiz_ui.py` | Bilingual application and interface components. |
| `src/graph.py`, `src/services/` | Bounded recommendation pipeline, matching, suitability and plan construction. |
| `src/learning_review.py`, `src/diagnostic.py` | Mixed practice, model review and labelled local fallback. |
| `src/tools/`, `src/llm/` | Catalogue clients and structured model-provider interfaces. |
| `src/database.py` | Local profiles, plans, progress, conversations and cache. |
| `data/*.json`, `data/fixtures/` | Demonstration/evaluation inputs and documented catalogue examples. |
| `tests/`, `scripts/`, `evaluation_results/` | Reproducible checks, evaluation entry points and dated reports. |
| `docs/SUBMISSION_GUIDE.md`, `docs/architecture.md` | Handoff checklist, review route and implementation boundaries. |

The stack is Python, Streamlit, LangGraph, Pydantic, httpx, boto3/Bedrock and SQLite. Exact runtime installation versions are supplied in `requirements.txt` and `uv.lock`; `requirements-dev.txt` adds the pinned test/lint tools.

The code package is separate from the slide deck and video. Their starting materials are `docs/deck_outline.md` and `docs/demo_script.md`; a script or outline is not a completed presentation deliverable.
