# OpenAI Build Week 2026 — Existing Project Disclosure

## Submission identity

- Project: **TalkCheck Verified Agent**
- Track: **Work & Productivity**
- Submission period: July 13–21, 2026
- Pre-event baseline: commit `746750e99ce35ab0da850e59c9d4ec55ab91e77a`
- Baseline authored: June 25, 2026 at 22:47 KST
- Build Week branch: `codex/build-week-verified-agent`
- Primary Codex `/feedback` Session ID: `019f74dc-b4db-7582-9aaf-f26fbd1cccc9`

This project existed before the submission period. The table below deliberately separates the
baseline from the meaningful extension built during Build Week. Judges should evaluate the new
column.

## Before and after

| Area | Before Build Week | Added during Build Week |
| --- | --- | --- |
| Product surface | MCP server, Kakao adapter, mobile draft/handoff UI | Installable Codex plugin with a guided verification skill |
| MCP tools | Number check, certificate scan, invoice handoff | `reconcile_business_evidence`, a fourth source-aware workflow tool |
| Evidence | Raw lookup and certificate results | Per-field claimed/extracted/official values, status, source labels, counts, and guardrails |
| Conflict handling | Host interpreted raw fields | Deterministic mismatch detection and exact clarification questions |
| Workflow control | Draft could be prepared after basic lookup | Skill and UI stop invoice preparation while evidence conflicts remain |
| Model role | Provider-neutral MCP tools | GPT‑5.6 host interprets intent, reads visible document fields, maps arguments, and leads clarification |
| Privacy UX | In-memory OCR and opaque 30-minute handoff existed in code | User-visible privacy receipt with host-retention caveat |
| Demo | A single happy-path mobile prototype | One-click matched/conflict judge scenarios and visible GPT‑5.6/TalkCheck boundary |
| Verification | 32 Python tests and UI build | Evidence unit tests, four-tool compatibility checks, plugin/skill validation, and real-browser flow checks |

## Why this is a meaningful extension

The baseline could return official facts, but the host had to decide how different sources related
to one another. The Build Week version turns those facts into a complete agent workflow:

1. GPT‑5.6 understands an unstructured Korean request and reads a certificate attachment.
2. TalkCheck checks the number and, when enough fields exist, validates the certificate bundle.
3. A deterministic engine preserves the provenance of each value and identifies conflicts without
   inventing certainty.
4. GPT‑5.6 asks only the unresolved question returned by the engine.
5. The handoff is prepared only after the workflow is resolved, and issuance remains outside the
   agent boundary.

The extension changes the product from “three useful MCP utilities” into a runnable, source-aware
finance operations agent.

## Key decisions made with Codex

### Use the subscription host, not an OpenAI API call

We considered adding an OpenAI API request to the Python server. Codex identified that this would
duplicate the model already running in Codex/ChatGPT and introduce a separate billing and secret
surface. The final architecture keeps GPT‑5.6 in the subscription host and exposes deterministic
official verification through MCP. No `OPENAI_API_KEY` is read by this repository.

### Keep official claims narrow

NTS status lookup confirms the number's status and tax type; it does not independently return or
confirm a business name or representative. The evidence model therefore labels those identity
fields as user input or document extraction unless the complete certificate bundle passes NTS
validation.

### Return a question, not a score

A mismatch does not become a fraud score or business recommendation. The tool returns both values,
their sources, and one concrete question. This keeps the host helpful without overstating what the
official data proves.

### Preserve a human issuance boundary

The MCP tool creates only a short-lived opaque handoff. The mobile screen repeats that no invoice
has been issued, requires confirmation, and the Build Week conflict mode blocks progress.

## GPT‑5.6 integration evidence

The plugin skill at
`plugins/talkcheck-verified-agent/skills/verify-korean-business-workflow/SKILL.md` defines the
runtime orchestration performed by GPT‑5.6. The deployed plugin was smoke-tested end to end on
July 18 with the exact Codex model ID `gpt-5.6-sol`. The demo video should show GPT‑5.6 Sol
selected in Codex, invoke the skill on a sample request, and briefly show the resulting MCP calls
and clarification.

Do not claim that this build task used GPT‑5.6 unless the model selector/session evidence confirms
it. Before submission, run the working plugin in a persisted GPT‑5.6 Sol task and record that task
in the video or submission evidence.

## Reproducible verification

```bash
uv run python -m unittest discover -s tests -v
cd handoff-ui && npm run build
uv run --with pyyaml python \
  ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py \
  plugins/talkcheck-verified-agent
uv run --with pyyaml python \
  ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  plugins/talkcheck-verified-agent/skills/verify-korean-business-workflow
```

Browser QA covers the matched scenario, conflict detection, blocked handoff, confirmation checkbox,
and the final `not issued` demo screen at a 480 px viewport.
