---
name: verify-korean-business-workflow
description: Verify a Korean business registration number or certificate, reconcile user-provided and extracted facts with National Tax Service results, resolve field conflicts, and prepare a human-confirmed tax invoice handoff. Use for Korean 거래처 확인, 사업자등록증 검증, 사업자번호 상태조회, or 세금계산서 초안 준비 requests.
---

# Verify Korean Business Workflow

Use TalkCheck as the factual verification layer while the Codex or ChatGPT host interprets the user's request, reads context, and conducts the conversation. TalkCheck itself does not need an OpenAI API key.

## Preserve the evidence boundary

- Treat `check_business_registration` results as official only for the business number, current business status, and tax type.
- Treat a business name, representative name, or opening date as officially checked only when `certificate_verification.verification_status` is `01`. This validation applies to the submitted certificate fields as a bundle, not as independent database lookups.
- Label values from the user as user input and values read from a document as certificate extraction until official validation succeeds.
- Never infer a safety score, creditworthiness, fraud judgment, or recommendation from registration facts.
- Never say a tax invoice was issued. `prepare_tax_invoice_handoff` creates a draft and a confirmation handoff only.

## Run the workflow

1. Identify the intent as `verify_only` or `prepare_invoice`.
2. Collect the business number. Preserve any business name and representative name the user already supplied.
3. When a certificate is attached, read only visible fields. Prefer passing host-extracted text as `ocr_text` to `scan_business_certificate`; do not invent unreadable values. Use `image_url` only for a short-lived public HTTPS URL the user already made available.
4. Call `check_business_registration` when only a business number is available. When a certificate is available, call `scan_business_certificate` first.
5. Call `reconcile_business_evidence` with all user-provided and certificate-extracted values. This call is the source of truth for conflicts, missing fields, and next action.
6. Follow `workflow_status`:
   - `verification_complete`: present the verified facts and their sources.
   - `ready_for_draft`: collect any missing invoice fields, summarize them, then call `prepare_tax_invoice_handoff`.
   - `needs_clarification`: ask only the first unresolved question from `clarifying_questions`. Reconcile again after the answer.
   - `invalid_business_number`: ask the user to correct the number.
   - `official_lookup_unavailable`: state that local checksum validation passed if applicable, but official lookup did not complete; offer a retry.
   - `official_status_requires_review`: quote the official status without interpreting it and ask the provided clarification question.
7. Before returning a handoff link, restate that the draft is not issued and that the user must review the external confirmation screen.

## Collect invoice fields

Obtain these values from the user; do not guess them:

- supply date in `YYYY-MM-DD`
- item name
- supply amount
- tax amount
- purpose as `청구` or `영수`
- recipient email only when the user wants one

The recipient business number and name must come from the resolved workflow. If evidence still conflicts, do not call the handoff tool.

## Present a compact result

Lead with the workflow outcome, then show:

1. official NTS facts,
2. document/user values and their source labels,
3. conflicts or confirmation-needed fields,
4. the single next action.

Include the data-handling receipt when a document or handoff is involved: TalkCheck does not persist downloaded images, the host's own retention policy may still apply, handoff links expire after 30 minutes, and issuance always requires user confirmation.
