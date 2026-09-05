# Topic 4: implementation and delivery cross-check

Reference: `IGNITE Agentic AI Hackathon Functional Training Session 3`, Topic 4. This document maps the prototype to the training concepts. It does not replace the organiser's latest submission instructions, award a score, or convert useful engineering practice into an official requirement.

## Agent patterns and actual implementation

| Training concept | What Atlas implements | Important limit |
| --- | --- | --- |
| Specialist responsibilities | Separate concept, retrieval, identity, selection, tutoring and adaptation modules. | These are programmed responsibilities, not a society of independently autonomous agents. |
| Feedback and reflection | Learner progress, practice feedback and explicit requests inform suggested next steps and new plan versions. | The recommendation graph has fixed nodes and a capped retry/fallback branch. It does not perform open-ended self-reflection or continuous autonomous research. |
| Human in the loop | Explicit learner requests/confirmation govern book replacement and plan changes; previous versions remain inspectable. | A model suggestion alone does not establish its factual correctness. |
| Escalation and fallback | Retrieval/model failures are surfaced; permitted cached records and foundational exercises are labelled. | Fallback output may not satisfy a highly specific learning request and is not live model evidence. |

Bibliographic source links and identity checks are product design choices supporting trust. They are **not presented here as a separate official “evidence-chain” scoring criterion**.

## Digital-agent measurement

| Metric discussed in training | Available evidence | What it does not prove |
| --- | --- | --- |
| First-attempt schema validation | Provider request, initial validation and retry counters. | Correct schema does not imply correct content. |
| Tool-call success | Catalogue operation, cache, result and failure telemetry. | A cache hit is not a fresh network response; small samples do not establish uptime. |
| Task completion | Machine checks of a three-stage route and declared constraints. | Rule/proxy checks do not establish that every selected book meets the learner's real needs. |
| Token usage/cost | Model input/output/cache token counts in opted-in live runs. | Deterministic tests use no model tokens. Currency cost requires the actual account/model pricing. |
| Loop discipline | Search-pass limits and completion within the cap. | This is bounded execution, not evidence of general autonomous planning ability. |
| Answer fidelity | Labelled deterministic proxies and dated live-quality samples. | Neither replaces an external subject-matter review. |

See `docs/evaluation.md` for metric definitions and `docs/qa-learning-focus-mixed-practice-2026-09-05.md` for concrete findings and failures. Keep report timestamps and test scope visible; do not merge different modes into a single accuracy claim.

## Deliverable check

| Deliverable | Prepared within this code handoff | Separate action |
| --- | --- | --- |
| Runnable proof of concept; code package no larger than 5 GB | Python application, dependencies, launcher, README and source/test material. | Validate the extracted final archive and its size. |
| Setup and file documentation | README, architecture and `SUBMISSION_GUIDE.md`. | Follow the launch instructions in a clean environment. |
| Presentation of at most ten slides | Existing `docs/deck_outline.md` is a starting point only. | Create the actual slide deck separately. |
| Video of at most five minutes | Existing `docs/demo_script.md` is a starting point only. | Record, time and submit the actual video separately. |

For the judging themes of benefit, originality, effectiveness, technical quality and presentation, demonstrate working behaviour and state the limits. Do not promise production authentication, universal relevance, validated learning gains or a completed blind study. A runnable code package does not by itself mean the entire competition submission is complete.
