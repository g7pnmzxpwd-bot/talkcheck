# Devpost Submission Draft

## Project name

TalkCheck Verified Agent

## Tagline

AI reads. Government data verifies. A human decides.

## Track

Work & Productivity

## Short description

TalkCheck is a GPT‑5.6-powered Codex plugin for Korean finance operations. It reads a business
registration request, keeps user input, document extraction, and National Tax Service facts
separate, asks one precise question when they conflict, and prepares a human-confirmed tax invoice
handoff without automatic issuance.

## Inspiration

Small finance and operations teams often verify a new Korean vendor by copying details between a
chat, a business registration certificate, a government lookup, and an invoice system. The painful
part is not finding one field; it is knowing which source proved which fact and noticing when two
almost-identical values disagree. Generic AI can make this faster, but it can also collapse an
extracted value and an official fact into one confident sentence.

We built TalkCheck around a stricter idea: AI should read and converse, official data should verify,
and a person should decide before a financial action.

## What it does

- Accepts a Korean business number, user-provided identity details, or registration-certificate
  fields read by the GPT‑5.6 host.
- Checks number format/checksum and current NTS business status and tax type.
- Validates a certificate bundle when business number, opening date, and representative are
  available.
- Reconciles every field as claimed, extracted, officially verified, consistent, conflicting,
  missing, or unavailable.
- Returns the exact unresolved values and a single clarification question instead of a risk score.
- Prepares a 30-minute opaque tax-invoice confirmation handoff only after the workflow is resolved.
- Shows a privacy receipt and always states that the invoice has not been issued.

## How we built it

The product has two intentionally separate layers:

1. **GPT‑5.6 in Codex/ChatGPT** understands the user's Korean request, reads visible certificate
   fields, maps them into MCP arguments, and manages the clarification turn.
2. **TalkCheck MCP** performs deterministic reconciliation, calls NTS status/certificate providers,
   preserves provenance, and prepares a non-issuing handoff.

The backend uses Python, FastMCP, Starlette, httpx, Pillow, and optional Tesseract OCR. The mobile
confirmation experience uses React and Vite. The Codex plugin includes a manifest, remote MCP
configuration, and a workflow skill with explicit evidence and issuance boundaries.

No OpenAI API key is required: GPT‑5.6 runs in the user's subscription host. Official NTS access is
handled by the configured government-data provider or deployed registry service.

## How we used Codex

Codex audited the existing repository and helped identify the strongest Build Week extension:
turning raw verification utilities into an evidence-aware agent rather than adding a decorative AI
call. In the primary build task, Codex:

- traced the NTS provider contract and caught that status lookup cannot verify a name or
  representative independently;
- designed and implemented the deterministic evidence state model and fourth MCP tool;
- created the plugin and orchestration skill;
- added unit tests and updated PlayMCP compatibility checks;
- extended the mobile experience with matched/conflict scenarios and a blocked-handoff state;
- ran the UI in a real browser, inspected both flows, fixed the only console error, and validated
  the plugin/skill manifests;
- prepared the existing-project disclosure, demo script, and submission checklist.

The dated Build Week branch and `/feedback` Session ID provide the development evidence.

## Challenges

The hardest product decision was deciding what “verified” means. NTS status lookup returns status
and tax type, not a public name/representative lookup. We avoided the tempting but incorrect UX of
painting every extracted field green. Identity fields become officially verified only when the
submitted certificate bundle passes validation; otherwise they remain clearly labelled extraction
or user confirmation.

The second challenge was keeping the product useful while preserving a human boundary. The agent
can do the repetitive work and prepare a draft, but unresolved evidence blocks the handoff and the
handoff itself never issues an invoice.

## Accomplishments

- A working four-tool MCP server and installable Codex plugin.
- Deterministic, tested provenance and conflict handling rather than model-generated confidence.
- A coherent mobile flow that demonstrates both success and a safe stop condition.
- No additional OpenAI API billing or key management for users with Codex/ChatGPT access.
- Explicit privacy and issuance boundaries visible in both tool output and product UI.

## What we learned

Agent reliability improves when the model is not asked to be the database. GPT‑5.6 is most useful
here as the flexible interface between messy human input and a narrow deterministic tool. Keeping
source attribution in the data model—not only in the prompt—made the UI, tests, and guardrails much
clearer.

## What's next

- Measure extraction accuracy on a consented, redacted certificate test set.
- Add PDF input through the host attachment pipeline.
- Connect a licensed Korean e-tax-invoice ASP sandbox after the confirmation handoff.
- Add durable encrypted workflow storage and organization-level audit policies.
- Localize the plugin's judge/demo experience fully into English.

## Technologies

Codex, GPT‑5.6, MCP, Python, FastMCP, Starlette, httpx, React, Vite, Tesseract OCR, NTS/data.go.kr

## Testing instructions

1. Open `https://talkcheck-playmcp.playmcp-endpoint.kakaocloud.io/`.
2. Select **불일치 감지** to see the exact conflicting business names and blocked handoff.
3. Return to **일치**, review the evidence ledger, check the confirmation box, and continue.
4. Confirm the final screen says this is a demo and no invoice or NTS transmission occurred.

For plugin testing, follow the installation section in the repository README and start a new Codex
task with GPT‑5.6 selected.

## Existing work disclosure

TalkCheck existed before Build Week with number/status checks, certificate OCR/validation, three MCP
tools, a Kakao adapter, and a mobile invoice-handoff prototype. During Build Week we added the Codex
plugin, GPT‑5.6 orchestration skill, evidence reconciliation tool/state model, exact conflict
questions, blocked conflict UI, privacy receipt, dual demo scenarios, new tests, browser validation,
and submission documentation. `BUILD_WEEK.md` contains the dated before/after evidence.

## Links to complete

- Repository: https://github.com/g7pnmzxpwd-bot/talkcheck
- Live demo: https://talkcheck-playmcp.playmcp-endpoint.kakaocloud.io/
- Public YouTube demo: **ADD URL**
- Primary Codex `/feedback` Session ID: **ADD ID**
