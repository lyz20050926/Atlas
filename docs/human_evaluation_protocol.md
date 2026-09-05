# Blind answer-fidelity and usefulness review

Use this protocol before claiming that Atlas recommendations are human validated.

## Sample

- At least 12 goals covering three or more subject areas; include English and Chinese cases.
- Two reviewers per case who understand the subject but did not build Atlas.
- Hide product/model identity and randomize Atlas output beside a one-shot baseline.
- Give both systems the same learner profile, time budget and requested perspectives.

## Reviewer rubric

Score each item from 1 (poor) to 5 (excellent):

1. The recommended books genuinely address the stated learning goal.
2. The three stages are complementary rather than repetitive.
3. The explanation is supported by the displayed metadata and sources.
4. The path is feasible within the stated time and prior knowledge.
5. The next action is clear enough for the learner to follow without extra help.

Also record any fabricated book identity, unsupported claim, unsafe advice or severe language problem
as a binary critical error.

## Reporting

Report sample size, reviewer count, mean and median per dimension, critical-error rate, Atlas-versus-
baseline preference and inter-reviewer agreement. Preserve raw anonymized ratings. Do not combine
these ratings with deterministic pass rates or the two-case live smoke test.

## Success threshold for the hackathon claim

Use the conservative statement “reviewers preferred Atlas on this evaluation set” only if Atlas wins
more than half of paired cases, median relevance is at least 4/5, no fabricated identity reaches the
final path and the full raw scoring sheet is available to judges.
