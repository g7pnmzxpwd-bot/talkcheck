# Demo Video Script — Final 2:31 Cut

The submission video must be public on YouTube, include audio, and stay under three minutes. Record
the narration in English. Korean filming notes are included after each segment.

The rendered submission artifact is `submission/assets/talkcheck-build-week-demo.mp4` (2:31,
1280×720, H.264/AAC). Its exact narration is in
`submission/assets/talkcheck-demo-narration.txt`, and the four reproducible title/evidence slides
are in `submission/assets/video-slides.html`.

## 0:00–0:18 — Problem

**Screen:** Title card, then a Korean business certificate/request in Codex.

**Narration:**

“A Korean finance operator verifying a new vendor has to compare chat messages, a registration
certificate, government data, and an invoice draft. One copied character can send an invoice to the
wrong record. TalkCheck makes that workflow conversational without pretending that AI extraction is
an official fact.”

촬영: 프로젝트 이름과 한 줄 문구를 2초 보여준 뒤 Codex 요청 화면으로 전환한다.

## 0:18–0:43 — Architecture and GPT‑5.6

**Screen:** Codex with GPT‑5.6 Sol selected; briefly show the TalkCheck plugin/skill chip or tool list.

**Narration:**

“GPT‑5.6 runs here in my Codex subscription. It understands the Korean request, reads visible
certificate fields, maps them to tools, and handles clarification. The TalkCheck MCP server does the
deterministic work: checksum validation, National Tax Service calls, and source reconciliation. No
OpenAI API key is required.”

촬영: 모델 선택기에서 GPT‑5.6 Sol임을 보이고 플러그인이 연결된 상태를 보여준다.

## 0:43–1:18 — Working agent and conflict

**Screen:** Ask the plugin to compare a claimed name “주식회사 모노랩” with a certificate value
“모노랩 스튜디오.” Show the `reconcile_business_evidence` call/result and the agent's one question.

**Narration:**

“Here the business number is valid and the official status is active, but the name typed by the user
differs from the document. TalkCheck preserves both values and their sources. It does not generate a
risk score. GPT‑5.6 asks the exact unresolved question returned by the tool, and invoice preparation
stops.”

촬영: 도구 결과의 `workflow_status: needs_clarification`, 두 상호, 질문 한 개를 확대한다.

## 1:18–1:48 — Product UI stop condition

**Screen:** Open the live demo, select **불일치 감지**, scroll through the orange evidence row, and
press **채팅에서 불일치 확인**.

**Narration:**

“The same evidence model drives the mobile handoff. The operator sees which value came from user
input, AI document extraction, or NTS validation. The disputed field is visible, and the financial
workflow is fail-closed until it is resolved.”

촬영: 불일치 필드, 출처, 차단 안내, CTA를 한 화면에 보여준다.

## 1:48–2:15 — Resolved handoff

**Screen:** Switch to **일치**, show the green evidence ledger and privacy receipt, check the box,
and continue to the final demo screen.

**Narration:**

“After the values agree, TalkCheck prepares a short-lived opaque handoff. Images are not persisted
by TalkCheck, the link expires after thirty minutes, and a person still has to review the external
confirmation. Even this final screen explicitly says no invoice or NTS transmission occurred.”

촬영: 체크박스 후 최종 화면의 ‘실제 발행 없음’ 문구를 확대한다.

## 2:15–2:39 — How Codex built it

**Screen:** Briefly show this primary Codex build task, the Build Week commit diff, and passing tests.

**Narration:**

“This was an existing MCP prototype. During Build Week, Codex helped me audit its real provider
limits, choose the subscription-hosted architecture, implement the evidence engine and plugin,
iterate on the mobile design, run browser checks, and prepare the submission. The dated branch and
primary feedback Session ID document that work.”

촬영: `BUILD_WEEK.md` before/after 표, Git commit 날짜, 테스트 통과 화면을 빠르게 보여준다.

## 2:39–2:50 — Close

**Screen:** Project name and live demo URL.

**Narration:**

“TalkCheck Verified Agent: AI reads, government data verifies, and a human decides.”

촬영: 음악 없이 또는 사용 권한이 명확한 음원만 사용한다.

## Recording checklist

- Keep the final edit at 2:50 or shorter.
- Show a real GPT‑5.6 Sol model selection and real TalkCheck tool invocation.
- Show Codex development evidence, not only the product UI.
- Use English narration, or attach a complete English translation.
- Remove credentials, private certificate data, email notifications, and unrelated browser tabs.
- Do not use copyrighted music or unlicensed third-party footage.
