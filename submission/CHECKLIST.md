# OpenAI Build Week Submission Checklist

Official deadline: **July 21, 2026 at 5:00 PM PDT** (**July 22 at 9:00 AM KST**). Do not plan to
submit at the deadline; target July 21 KST.

## Product and deployment

- [x] Push the dated Build Week commit(s) to `codex/build-week-verified-agent`.
- [x] Deploy the branch used for judging.
- [x] Confirm `GET /health` returns `{"status":"ok"}`.
- [x] Confirm the remote MCP lists four tools, including `reconcile_business_evidence`.
- [x] Confirm the live root URL shows the matched/conflict scenario switch.
- [x] Run the Python suite, UI build, plugin validator, and skill validator from `BUILD_WEEK.md`.
- [x] Re-run the 480 px browser flow after deployment with zero console errors.
- [x] Use only simulated or consented/redacted certificate data in the demo.

## GPT‑5.6 and Codex evidence

- [x] Start a new product-demo task with GPT‑5.6 Sol (`gpt-5.6-sol`) explicitly selected.
- [x] Install/enable `talkcheck-verified-agent` and invoke the workflow skill.
- [ ] Capture a real `reconcile_business_evidence` tool call and clarification turn.
- [x] Run `/feedback` in this primary build task and copy the Session ID.
- [x] Replace every `ADD ID` placeholder in the README/submission materials.
- [x] Preserve dated commits after July 13 and keep the June 25 baseline visible.

## Repository access

The repository is public under the MIT License.

- [x] Make the repository public with the MIT License.
- [x] Verify the exact submitted repository URL is accessible without authentication.
- [x] Ensure `.env`, API keys, tokens, private certificates, browser sessions, and local screenshots
  containing personal data are not committed.
- [x] Confirm README setup, sample/demo path, supported platforms, and plugin installation are clear.

## Demo video

- [x] Follow `submission/DEMO_SCRIPT.md` and keep the final cut under 3:00.
- [x] Include clear audio explaining the product, Codex workflow, and GPT‑5.6 runtime role.
- [x] Show the working agent, live UI, conflict stop, resolved handoff, and no-issuance boundary.
- [x] Show Codex or the dated Build Week evidence briefly.
- [x] Use English narration or provide a complete English translation.
- [x] Remove copyrighted music, unauthorized trademarks/assets, secrets, and private data.
- [x] Upload to YouTube as **Public**, not Unlisted or Private.
- [ ] Open the YouTube URL in a logged-out/private window and verify playback and audio.
- [x] Replace `ADD URL` in `submission/DEVPOST.md`.

## Devpost form

- [x] Register/join the OpenAI Build Week challenge.
- [x] Select **Work & Productivity** as the only track.
- [x] Paste and proofread the English copy from `submission/DEVPOST.md`.
- [x] Add the working live demo URL.
- [x] Add the exact repository URL and confirm access instructions.
- [x] Add the public YouTube URL.
- [x] Add the primary `/feedback` Codex Session ID.
- [x] Explicitly disclose the pre-existing baseline and Build Week additions.
- [x] Confirm all team members and eligibility details are correct.
- [x] Save a draft and inspect the public preview before final submission.
- [x] Submit before the deadline and save the confirmation URL:
  <https://devpost.com/software/talkcheck-verified-agent>

## Final audit

- [x] Every claim in the video matches the deployed build.
- [x] No screen says an invoice was issued.
- [x] Name/representative fields are not labelled official unless certificate-bundle validation passed.
- [ ] The demo instance remains available free of charge through the judging period ending August 7.
- [ ] No submission materials need changes after the deadline; Devpost locks edits then.
