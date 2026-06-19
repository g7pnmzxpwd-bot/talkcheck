**Comparison Target**

- Source visual truth: `/Users/yujaejun/Documents/New project 2/talkcheck/design/talkcheck-hybrid-reference.png`
- Implementation screenshot: `/Users/yujaejun/Documents/New project 2/talkcheck/design/talkcheck-hybrid-implementation.png`
- Full-view comparison evidence: `/Users/yujaejun/Documents/New project 2/talkcheck/design/talkcheck-hybrid-comparison.png`
- Viewport: 390 × 844
- State: default valid invoice draft, consent unchecked, no modal open
- Focused region comparison: not needed; the combined image preserves both complete 390 px-wide screens at readable 1× size, including type, icons, dividers, form controls, and action area.

**Findings**

- No actionable P0, P1, or P2 mismatches remain.
- [P3] Verification summary is slightly denser in the implementation.
  Location: pale green business verification section.
  Evidence: the source uses a little more vertical padding; the implementation keeps the same hierarchy, labels, values, source line, and visual grouping in a shorter block.
  Impact: minor rhythm difference only; scanning and tap behavior are unaffected.
  Follow-up: add roughly 20 px of total vertical space to the section if exact mock spacing becomes more important than keeping the complete default state inside one 844 px viewport.
- [P3] Primary action color is flatter than the generated source.
  Location: `발행 화면으로 이동` button.
  Evidence: the source image contains slight generated tonal variation, while the implementation uses the brief's solid Kakao-inspired yellow token.
  Impact: none; the implementation is more consistent and avoids an unrequested gradient.

**Required Fidelity Surfaces**

- Fonts and typography: passed. Bundled Noto Sans KR variable font matches the Korean product UI character; hierarchy, weights, line height, numeric emphasis, wrapping, and truncation are coherent at 390 px.
- Spacing and layout rhythm: passed. Header, intro, verification facts, invoice rows, consent, warning, and actions remain in the source order and fit without horizontal or vertical overflow at the target viewport.
- Colors and visual tokens: passed. Warm white, charcoal, muted gray, mint verification tint, semantic green, dividers, and solid yellow action map to the selected direction with accessible contrast.
- Image quality and asset fidelity: passed. The source contains no photography, illustration, logo artwork, or decorative raster assets to reproduce. Phosphor icons provide a consistent real icon set; no handcrafted SVG, CSS art, emoji, or placeholder imagery is used.
- Copy and content: passed. Business facts, invoice values, source attribution, consent language, and not-issued warning match the selected concept and do not imply safety scoring or automatic issuance.
- States and interactions: passed. Field editors, amount total, invalid email state, required consent error, local draft save, later action, and pre-issuance handoff confirmation were exercised in the browser. The new opaque-link create/load/update/prepare contract is additionally covered by ASGI integration tests, including the invariant that issuance remains `not_issued`.
- Responsiveness and accessibility: passed. The mobile surface has no horizontal overflow, desktop width is capped at 480 px, controls are semantic, focus styles are visible, and dialogs and errors expose accessible names and roles.

**Patches Made Since Previous QA Pass**

- Reduced vertical density so the complete default state fits a 390 × 844 viewport.
- Corrected a stale inline error message after a field is fixed and saved.
- Verified the handoff confirmation continues to state that no invoice has been issued.
- Replaced hard-coded screen values with an opaque handoff record while keeping the selected demo state visually unchanged.
- Added truthful loading, expired-link, unavailable-lookup, saving, and preparing states.
- Added a 30-minute in-memory handoff store and authenticated local create endpoint without putting business or invoice data in the URL.

**Implementation Checklist**

- [x] Match the selected verification-plus-invoice hierarchy.
- [x] Keep invoice issuance outside this screen.
- [x] Make every visible edit and action control functional.
- [x] Exercise default, validation, edit, saved, and handoff-ready states.
- [x] Confirm production build and existing backend tests.

**Follow-up Polish**

- Consider the two P3 spacing/color refinements only if later user feedback asks for pixel-level mock parity.

final result: passed
