# AI use log: HA04-aca-compare

This log records AI-assisted sessions, author work and how AI outputs were reviewed. It supports the AI use disclosure in [PAPER.md](PAPER.md). This log is incomplete because the AI-use tracking in this format was only developed at the end of the work on the paper.

## Definitions

Session time is the elapsed time of a chat session with the author actively directing and reviewing. It is not AI compute time.

Requests and words are the author's content-related prompts in the session. Words are whitespace-delimited tokens. Pasted Markdown table rows, attachments, automatic context and notifications are excluded. Requests about this disclosure or metric are excluded from the totals.

Verification levels, from weakest to strongest:

| Level | Name | Meaning |
|:---|:---|:---|
| V1 | Plausibility | Final outputs looked at for whether they seem reasonable. |
| V2 | Code shape | Code structure and flow checked against expectations, not line by line. |
| V3 | Intermediate inspection | Intermediate outputs generated and inspected against expectations. |
| V4 | Cross-check | Results compared with an independent or prior calculation, and differences explained. |
| V5 | Line review | Code read line by line, in enough detail to find bugs. |
| V6 | Independent reproduction | Result reproduced by separate code or method. |

## Summary

| # | Date | Model | Session (hr) | Requests | Words | Verification |
|:---|:---|:---|---:|---:|---:|:---|
| P | 2026-10-17 | GPT-6.1 Sol | Unknown | Unknown | Unknown | To confirm |
| 1 | 2026-10-17 | GPT-6.1 Sol | 1.4 | 16 | 1,544 | To confirm |
| 2 | 2026-10-17 | Claude Opus 5.5 | 2.2 | 2 | 672 | Results V1 to V4 (to confirm), text reviewed |
| 3 | 2026-10-18 | GPT-6.1 Sol | 2.4 | 34 | 1,308 | Code explained and questioned, point results V3, text reviewed |
| 4 | 2026-10-20 | Claude Opus 5.5 | 2.1 | 8 | 718 | Code V2, results V4, text reviewed |
| | | **Total (excl. P)** | **8.1** | **60** | **4,242** | |

On 20 October 2026 the paper contained 6,073 prose words before the AI disclosure (headings and table rows excluded). The author input from sessions 1 to 4 was about 70% of this. This ratio describes text volume only. It is not a measure of authorship or intellectual contribution.

## Sessions

### P. Prototype accuracy assessment, HA04-accuracy-1 (2026-10-17, GPT-6.1 Sol)
- AI did: Developed the prototype accuracy assessment of the habitat and geomorphic mapping, documented in `../deprecated/HA04-accuracy-1/FINDINGS.md`. Session 4 adapted this prototype for the calibration check.
- Author did: Described the problem to be investigated.
- Review: Indirectly cross-checked in session 4, where the calibration results were compared with this prototype and the differences investigated. Other review to confirm.

### 1. Initial investigation and draft (2026-10-17, GPT-6.1 Sol, 1.4 hr)

- AI did: Initial investigation, analysis code, computational checks and the first draft of the paper.
- Author did: Formulated the research question and directed the methods across 16 requests (1,544 words). The requests included technical guidance, questions, corrections and operational instructions.

### 2. Review and extension (2026-10-17, Claude Opus 5.5, 2.2 hr)

- AI did: Reviewed and extended the analysis and revised the paper.
- Author did: Gave 661 words of numbered review feedback on ACA coverage gaps, class alignment, the Shark Bay exclusion, rocky reefs and the buffer definitions.
- Review: The feedback came from the author's review of the session 1 outputs. Review of this session's own outputs is to be confirmed.

### 3. Explanatory code review and revision (2026-10-18, GPT-6.1 Sol, 2.4 hr)

- AI did: Explained the code and methods, added explanatory comments, separated publication and working outputs, wrote table captions and revised the methods and results.
- Author did: Questioned how the calculations worked, set the publication-output policy and directed revisions towards clearer statements of the main findings.
- Review: The AI explained the code, and the author questioned the calculations. Point results were reviewed in QGIS (V3). All text was reviewed and revised.
- Residual risk: Errors in code paths that were not covered by the explanations or by the inspected points.

### 4. Calibration check (2026-10-20, Claude Opus 5.5, 2.1 hr)

- AI did: Implemented the calibration check analysis (`calibration_check.py`), adapted from the HA04-accuracy-1 prototype. Drafted the associated text.
- Author did: Specified the task from the prior prototype. Clarified the written text, with AI assistance.
- Review: Compared the calibration results with the similar HA04-accuracy-1 calculation, then investigated whether the differences were justified (V4). Reviewed the code structure and flow, but not in enough detail to find bugs (V2). Reviewed and revised all text.
- Residual risk: Bugs in the code that do not change results enough to show up in the comparison with HA04-accuracy-1.


