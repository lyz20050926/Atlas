# Hackathon delivery readiness

This is a project checklist, **not an official score or a claim that every judging criterion has been satisfied**. The organiser's current submission instructions take precedence. The code proof of concept and its final presentation materials are separate deliverables.

## Code handoff checks

- Source package is no larger than the organiser's 5 GB limit.
- README identifies prerequisites, dependencies, an unambiguous local launch route, demo/live modes and a short feature-verification route.
- A fresh environment can install the supplied dependencies and launch without a developer's `.env`, credentials, virtual environment or personal database.
- No private credentials, personal learning database, QA database, logs or local environment are included in the submission archive. `.gitignore` alone does not sanitize a ZIP.
- The final code passes `scripts/preflight.py`; the generated report date and exact source/package must correspond. A historical test count is not the final release result.
- If submitting a repository link, confirm that the final files have actually been committed and are accessible to the intended reviewers. An untracked local directory is not a published repository.

See [SUBMISSION_GUIDE.md](SUBMISSION_GUIDE.md) for the handoff route. Final validation results are supplied by the release report rather than prefilled in this checklist.

## What can be demonstrated

| Area | Demonstrable prototype behaviour | Evidence boundary |
| --- | --- | --- |
| Learner benefit | A learner supplies a detailed goal, receives a reading route, records progress and asks for changes. | Time saved and learning gains need external learner studies. |
| Agent workflow | A bounded LangGraph pipeline retrieves records, checks identities, selects complementary roles and checks constraints. | Fixed orchestration and limited fallback retries, not an unrestricted autonomous reflection loop. |
| Learning support | Book-specific and whole-path conversations, mixed practice, supplied-excerpt explanation and reading-session follow-up. | Model questions and explanations can be wrong; specialised Chinese practice can fall back to general exercises. |
| Technical implementation | Typed models, request limits, cache, persistence, state separation, tests and visible failure states. | No production authentication, hosted service guarantee, backup programme or security certification. |
| Presentation | Bilingual UI, architecture notes, deck outline and timed demo script. | An outline/script is not the finished slide deck/video. |

## Presentation materials prepared separately

- Produce the slide deck from `docs/deck_outline.md`, keeping it within ten slides.
- Record the demonstration from `docs/demo_script.md`, keeping it within five minutes.
- Label footage and reports as live, cached or simulated. Never describe a fixture-based run as current retrieval or a live model response.
- Test any submitted URL from a separate machine. Localhost is only available on the computer running Atlas.

## Claims to avoid

- “Perfect recommendations”, “top-tier teaching accuracy” or “proven learning gains” without a corresponding external evaluation.
- “Fully autonomous self-reflection” when describing the current fixed graph and user-triggered adaptation.
- “Human validated” based on deterministic scores or two live smoke-test cases.
- “Production secure” or “private multi-user workspace” based on profile IDs and local SQLite separation.
- A passing preflight or live result from an earlier source version presented as a fresh acceptance run.

Blind relevance/usefulness review is an advisable **quality-evidence step**, not an extra submission requirement invented by this project. The proposed protocol is in `docs/human_evaluation_protocol.md`. If it is not run, simply state that it is pending.
