# OpenAI Build Week Submission Checklist

Official deadline: **July 21, 2026 at 5:00 PM PDT** (**July 22 at 9:00 AM KST**). Do not plan to
submit at the deadline; target July 21 KST.

## Product and deployment

- [ ] Push the dated Build Week commit(s) to `codex/build-week-verified-agent`.
- [ ] Deploy the branch used for judging.
- [ ] Confirm `GET /health` returns `{"status":"ok"}`.
- [ ] Confirm the remote MCP lists four tools, including `reconcile_business_evidence`.
- [ ] Confirm the live root URL shows the matched/conflict scenario switch.
- [ ] Run the Python suite, UI build, plugin validator, and skill validator from `BUILD_WEEK.md`.
- [ ] Re-run the 480 px browser flow after deployment with zero console errors.
- [ ] Use only simulated or consented/redacted certificate data in the demo.

## GPT‑5.6 and Codex evidence

- [ ] Start a new product-demo task with GPT‑5.6 explicitly selected.
- [ ] Install/enable `talkcheck-verified-agent` and invoke the workflow skill.
- [ ] Capture a real `reconcile_business_evidence` tool call and clarification turn.
- [ ] Run `/feedback` in this primary build task and copy the Session ID.
- [ ] Replace every `ADD ID` placeholder in the README/submission materials.
- [ ] Preserve dated commits after July 13 and keep the June 25 baseline visible.

## Repository access

The repository is currently private.

- [ ] Either make it public with an appropriate license, or keep it private and grant access to
  `testing@devpost.com` and `build-week-event@openai.com`.
- [ ] Verify both judging accounts can access the exact submitted repository URL.
- [ ] Ensure `.env`, API keys, tokens, private certificates, browser sessions, and local screenshots
  containing personal data are not committed.
- [ ] Confirm README setup, sample/demo path, supported platforms, and plugin installation are clear.

## Demo video

- [ ] Follow `submission/DEMO_SCRIPT.md` and keep the final cut under 3:00.
- [ ] Include clear audio explaining the product, Codex workflow, and GPT‑5.6 runtime role.
- [ ] Show the working agent, live UI, conflict stop, resolved handoff, and no-issuance boundary.
- [ ] Show Codex or the dated Build Week evidence briefly.
- [ ] Use English narration or provide a complete English translation.
- [ ] Remove copyrighted music, unauthorized trademarks/assets, secrets, and private data.
- [ ] Upload to YouTube as **Public**, not Unlisted or Private.
- [ ] Open the YouTube URL in a logged-out/private window and verify playback and audio.
- [ ] Replace `ADD URL` in `submission/DEVPOST.md`.

## Devpost form

- [ ] Register/join the OpenAI Build Week challenge.
- [ ] Select **Work & Productivity** as the only track.
- [ ] Paste and proofread the English copy from `submission/DEVPOST.md`.
- [ ] Add the working live demo URL.
- [ ] Add the exact repository URL and confirm access instructions.
- [ ] Add the public YouTube URL.
- [ ] Add the primary `/feedback` Codex Session ID.
- [ ] Explicitly disclose the pre-existing baseline and Build Week additions.
- [ ] Confirm all team members and eligibility details are correct.
- [ ] Save a draft and inspect the public preview before final submission.
- [ ] Submit before the deadline and save the confirmation URL/screenshot.

## Final audit

- [ ] Every claim in the video matches the deployed build.
- [ ] No screen says an invoice was issued.
- [ ] Name/representative fields are not labelled official unless certificate-bundle validation passed.
- [ ] The demo instance remains available free of charge through the judging period ending August 7.
- [ ] No submission materials need changes after the deadline; Devpost locks edits then.
