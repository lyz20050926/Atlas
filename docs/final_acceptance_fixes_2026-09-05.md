# Final acceptance fixes — 5 September 2026

This release addresses three issues reproduced during the final live acceptance check.

## Changes

- Recognise coordinated English progress reports, including “I have only two hours this week and have read 30%.” Negative statements, future intentions, other people's reports and model-accuracy percentages are covered by regression tests.
- Require Chinese prose in the independent question auditor's explanations and rubrics. A final check detects English prose in visible question fields and permits one bounded translation repair. Option positions and the corresponding answer key are preserved and validated; failed repair falls back to explicitly labelled local exercises.
- Distinguish optional enrichment from actual learning requirements. A complete selection rejected by the first reviewer receives a bounded independent constraint audit. Blocking requirements must quote an actual goal field. Unavailable audits or fabricated quotes cannot approve a path. Explicit specialist-depth requests remain blocking when unsupported; missing book roles still produce an incomplete path. Non-blocking notes are labelled separately.

## Verification

- 387 automated tests passed in a clean copy of the submission source; lint, dependencies, compilation, selected secret-pattern scan and deterministic evaluation also passed.
- Windows isolated checks used Python 3.12.4 and the pinned runtime/development dependencies.
- Live checks used authorised AWS access in WSL, without copying credentials or production learner records into the package.
- Recommendation model: `us.anthropic.claude-haiku-4-5-20251001-v1:0`; teaching model: `us.anthropic.claude-sonnet-4-6`.
- English real catalogue search produced three selected books and a complete path. The real mentor response preserved 30% progress from the previously missed compound sentence, without replacing books or replanning against the user's instruction.
- Chinese practice generated three model-authored formats with Chinese explanations and rubric. Generation took about 27 seconds in this sample; English took about 23 seconds. Written-answer review and excerpt-based help successfully used the teaching model in both languages.
- With explicitly enabled labelled catalogue supplementation, the Chinese embodied-intelligence example returned three related books and passed the stated requirements. Without supplementation, the current live-only Chinese catalogue results still did not support a complete path; the application correctly reported that limitation.
- A fresh direct-title lookup for 斗罗大陆 returned a matching work by 唐家三少. A nonexistent test title returned no match rather than substituting another book. This identity check did not use a model.

These are bounded integration samples, not evidence of universally correct recommendations or top-tier pedagogical performance. Catalogue coverage, response quality and service availability can vary. The independent audit and language guard are safeguards, not guarantees of factual correctness. Existing historical reports retain their original timestamps; they must not be confused with this acceptance run.

The default launcher still starts the English demo experience. Genuine model interaction requires `--mode live` and the reviewer's own valid AWS configuration. Slides and a demonstration video remain separate submission deliverables.
