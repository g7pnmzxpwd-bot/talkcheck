import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowLeft,
  ArrowClockwise,
  CaretRight,
  Check,
  CheckCircle,
  CircleNotch,
  Database,
  FileText,
  Info,
  LockKey,
  PencilSimple,
  ShieldCheck,
  Sparkle,
  WarningCircle,
  X,
} from "@phosphor-icons/react";

const demoFieldResults = [
  {
    field: "business_number",
    label: "사업자등록번호",
    status: "verified",
    claimed: "123-45-67891",
    extracted: "123-45-67891",
    official: "123-45-67891",
    sources: ["workflow_input", "certificate_extraction", "nts_status_lookup"],
    message: "국세청 상태조회에서 이 번호의 현재 상태가 반환되었습니다.",
  },
  {
    field: "business_name",
    label: "상호",
    status: "verified",
    claimed: "주식회사 모노랩",
    extracted: "주식회사 모노랩",
    official: "주식회사 모노랩",
    sources: ["user_input", "certificate_extraction", "nts_certificate_validation"],
    message: "국세청 증명서 진위확인에 제출된 정보 묶음 안에서 확인되었습니다.",
  },
  {
    field: "representative_name",
    label: "대표자명",
    status: "verified",
    claimed: "김민수",
    extracted: "김민수",
    official: "김민수",
    sources: ["user_input", "certificate_extraction", "nts_certificate_validation"],
    message: "국세청 증명서 진위확인에 제출된 정보 묶음 안에서 확인되었습니다.",
  },
];

const demoRecord = {
  draft: {
    recipient_business_number: "1234567891",
    recipient_name: "주식회사 모노랩",
    supply_date: "2026-06-18",
    item_name: "디자인 용역",
    supply_amount: 1000000,
    tax_amount: 100000,
    purpose: "청구",
    recipient_email: "billing@monolab.kr",
  },
  business_check: {
    business_name: "주식회사 모노랩",
    representative_name: "김민수",
    formatted_business_number: "123-45-67891",
    official_lookup: {
      business_status: "계속사업자",
      tax_type: "부가가치세 일반과세자",
    },
    source: "Build Week 데모 · 국세청 응답 형식 시뮬레이션",
    workflow_status: "ready_for_draft",
    field_results: demoFieldResults,
    evidence_summary: {
      officially_verified: 5,
      cross_source_consistent: 0,
      conflicts: 0,
      needs_confirmation: 0,
      official_lookup_available: true,
      certificate_bundle_verified: true,
    },
    clarifying_questions: [],
    data_handling: {
      downloaded_image_storage: "TalkCheck processes downloaded images in memory and does not persist them",
      handoff_ttl_minutes: 30,
    },
  },
};

const conflictDemoRecord = {
  draft: demoRecord.draft,
  business_check: {
    ...demoRecord.business_check,
    workflow_status: "needs_clarification",
    field_results: demoFieldResults.map((item) => (
      item.field === "business_name"
        ? {
          ...item,
          status: "conflict",
          claimed: "주식회사 모노랩",
          extracted: "모노랩 스튜디오",
          official: null,
          sources: ["user_input", "certificate_extraction"],
          message: "상호의 사용자 입력값과 증명서 추출값이 다릅니다.",
        }
        : item
    )),
    evidence_summary: {
      ...demoRecord.business_check.evidence_summary,
      officially_verified: 4,
      conflicts: 1,
    },
    clarifying_questions: [
      "사용자 입력(상호: 주식회사 모노랩)과 증명서 추출(상호: 모노랩 스튜디오) 중 어느 값이 맞나요?",
    ],
  },
};

const fieldMeta = {
  supplyDate: { label: "작성일", type: "date", inputMode: undefined },
  itemName: { label: "품목", type: "text", inputMode: undefined },
  supplyAmount: { label: "공급가액", type: "text", inputMode: "numeric" },
  taxAmount: { label: "세액", type: "text", inputMode: "numeric" },
  recipientEmail: { label: "수신 이메일", type: "email", inputMode: "email" },
};

const currency = new Intl.NumberFormat("ko-KR");
const appBasePath = new URL(import.meta.env.BASE_URL, window.location.origin).pathname.replace(/\/$/, "");

const evidenceStatusMeta = {
  verified: { label: "공식 확인", tone: "verified" },
  consistent: { label: "교차 일치", tone: "consistent" },
  conflict: { label: "불일치", tone: "conflict" },
  needs_confirmation: { label: "확인 필요", tone: "pending" },
  extracted: { label: "문서 추출", tone: "pending" },
  unavailable: { label: "조회 미완료", tone: "pending" },
  invalid: { label: "번호 오류", tone: "conflict" },
  missing: { label: "정보 없음", tone: "muted" },
};

const sourceLabels = {
  workflow_input: "요청 정보",
  user_input: "사용자 입력",
  certificate_extraction: "AI 문서 추출",
  nts_status_lookup: "국세청 상태조회",
  nts_certificate_validation: "국세청 진위확인",
};

function appUrl(path) {
  return `${appBasePath}${path}`;
}

function draftFromRecord(record) {
  return {
    supplyDate: record.draft.supply_date,
    itemName: record.draft.item_name,
    supplyAmount: String(record.draft.supply_amount),
    taxAmount: String(record.draft.tax_amount),
    recipientEmail: record.draft.recipient_email || "",
  };
}

function invoiceContextFromRecord(record) {
  return {
    recipientBusinessNumber: record.draft.recipient_business_number,
    recipientName: record.draft.recipient_name,
    purpose: record.draft.purpose,
  };
}

function getReferenceId() {
  const prefix = `${appBasePath}/handoff/`;
  if (!window.location.pathname.startsWith(prefix)) return "";
  const referenceId = window.location.pathname.slice(prefix.length);
  return referenceId && !referenceId.includes("/") && referenceId !== "demo"
    ? decodeURIComponent(referenceId)
    : "";
}

async function requestJson(url, options) {
  const response = await fetch(url, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(payload.message || "요청을 완료하지 못했습니다.");
    error.status = response.status;
    throw error;
  }
  return payload;
}

function formatMoney(value) {
  const amount = Number(value);
  return `${currency.format(Number.isFinite(amount) ? amount : 0)}원`;
}

function formatDate(value) {
  const [year, month, day] = value.split("-");
  return year && month && day ? `${year}. ${month}. ${day}` : value;
}

function validate(draft, agreed) {
  const next = {};
  if (!/^\d{4}-\d{2}-\d{2}$/.test(draft.supplyDate)) next.supplyDate = "작성일을 확인해 주세요.";
  if (!draft.itemName.trim()) next.itemName = "품목을 입력해 주세요.";
  if (!/^\d+$/.test(draft.supplyAmount) || Number(draft.supplyAmount) <= 0) {
    next.supplyAmount = "공급가액은 1원 이상이어야 해요.";
  }
  if (!/^\d+$/.test(draft.taxAmount) || Number(draft.taxAmount) < 0) {
    next.taxAmount = "세액은 0원 이상이어야 해요.";
  }
  if (draft.recipientEmail && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(draft.recipientEmail)) {
    next.recipientEmail = "이메일 형식을 확인해 주세요.";
  }
  if (!agreed) next.agreed = "다음 화면으로 이동하려면 내용을 확인해 주세요.";
  return next;
}

export function App() {
  const [referenceId] = useState(getReferenceId);
  const [draft, setDraft] = useState(() => draftFromRecord(demoRecord));
  const [invoiceContext, setInvoiceContext] = useState(() => invoiceContextFromRecord(demoRecord));
  const [businessCheck, setBusinessCheck] = useState(demoRecord.business_check);
  const [demoScenario, setDemoScenario] = useState("verified");
  const [loadState, setLoadState] = useState(referenceId ? "loading" : "ready");
  const [reloadKey, setReloadKey] = useState(0);
  const [actionState, setActionState] = useState("idle");
  const [editing, setEditing] = useState(null);
  const [editValue, setEditValue] = useState("");
  const [agreed, setAgreed] = useState(false);
  const [errors, setErrors] = useState({});
  const [toast, setToast] = useState("");
  const [showIssueDemo, setShowIssueDemo] = useState(window.location.hash === "#issue-demo");
  const editorRef = useRef(null);

  useEffect(() => {
    if (!referenceId) return undefined;
    let cancelled = false;
    setLoadState("loading");
    requestJson(appUrl(`/api/handoffs/${encodeURIComponent(referenceId)}`))
      .then((record) => {
        if (cancelled) return;
        setDraft(draftFromRecord(record));
        setInvoiceContext(invoiceContextFromRecord(record));
        setBusinessCheck(record.business_check || {});
        setLoadState("ready");
      })
      .catch((error) => {
        if (cancelled) return;
        setLoadState(error.status === 404 ? "missing" : "error");
      });
    return () => {
      cancelled = true;
    };
  }, [referenceId, reloadKey]);

  const totalAmount = useMemo(
    () => Number(draft.supplyAmount || 0) + Number(draft.taxAmount || 0),
    [draft.supplyAmount, draft.taxAmount],
  );

  useEffect(() => {
    if (!toast) return undefined;
    const timer = window.setTimeout(() => setToast(""), 2200);
    return () => window.clearTimeout(timer);
  }, [toast]);

  useEffect(() => {
    if (editing && editorRef.current && !editorRef.current.open) editorRef.current.showModal();
  }, [editing]);

  useEffect(() => {
    const handleHashChange = () => setShowIssueDemo(window.location.hash === "#issue-demo");
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  function openEditor(field) {
    setEditing(field);
    setEditValue(draft[field]);
  }

  function selectDemoScenario(scenario) {
    const record = scenario === "conflict" ? conflictDemoRecord : demoRecord;
    setDemoScenario(scenario);
    setDraft(draftFromRecord(record));
    setInvoiceContext(invoiceContextFromRecord(record));
    setBusinessCheck(record.business_check);
    setAgreed(false);
    setErrors({});
    setToast(scenario === "conflict" ? "AI가 상호 불일치 1건을 찾았어요." : "모든 핵심 정보가 일치해요.");
  }

  function closeEditor() {
    editorRef.current?.close();
    setEditing(null);
  }

  function saveEditor(event) {
    event.preventDefault();
    const value = editing === "supplyAmount" || editing === "taxAmount"
      ? editValue.replace(/[^0-9]/g, "")
      : editValue;
    const nextDraft = { ...draft, [editing]: value };
    const nextErrors = validate(nextDraft, true);
    if (nextErrors[editing]) {
      setErrors((current) => ({ ...current, [editing]: nextErrors[editing] }));
      return;
    }
    setDraft(nextDraft);
    setErrors((current) => ({ ...current, [editing]: undefined }));
    closeEditor();
  }

  function apiDraft() {
    return {
      recipient_business_number: invoiceContext.recipientBusinessNumber,
      recipient_name: invoiceContext.recipientName,
      supply_date: draft.supplyDate,
      item_name: draft.itemName,
      supply_amount: Number(draft.supplyAmount),
      tax_amount: Number(draft.taxAmount),
      purpose: invoiceContext.purpose,
      recipient_email: draft.recipientEmail || null,
    };
  }

  async function persistDraft(successMessage) {
    if (actionState !== "idle") return false;
    setActionState("saving");
    try {
      if (referenceId) {
        await requestJson(appUrl(`/api/handoffs/${encodeURIComponent(referenceId)}`), {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ draft: apiDraft() }),
        });
      } else {
        window.localStorage.setItem("talkcheck.invoiceDraft", JSON.stringify(draft));
      }
      setToast(successMessage);
      return true;
    } catch (error) {
      if (error.status === 404) setLoadState("missing");
      else setToast("저장하지 못했어요. 잠시 후 다시 시도해 주세요.");
      return false;
    } finally {
      setActionState("idle");
    }
  }

  function saveDraft() {
    persistDraft(referenceId ? "서버에 초안을 저장했어요." : "초안을 이 기기에 저장했어요.");
  }

  function leaveForLater() {
    persistDraft("초안을 저장했어요. 채팅방에서 다시 열 수 있어요.");
  }

  async function submitHandoff(event) {
    event.preventDefault();
    if ((businessCheck.evidence_summary?.conflicts || 0) > 0) {
      setToast(businessCheck.clarifying_questions?.[0] || "불일치 정보를 먼저 확인해 주세요.");
      return;
    }
    const nextErrors = validate(draft, agreed);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) {
      window.setTimeout(() => document.querySelector("[data-error='true']")?.focus(), 0);
      return;
    }
    if (!referenceId) {
      window.location.hash = "issue-demo";
      return;
    }
    setActionState("preparing");
    try {
      await requestJson(appUrl(`/api/handoffs/${encodeURIComponent(referenceId)}/prepare`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ draft: apiDraft() }),
      });
      window.location.hash = "issue-demo";
    } catch (error) {
      if (error.status === 404) setLoadState("missing");
      else setToast("발행 확인 화면을 준비하지 못했어요. 다시 시도해 주세요.");
    } finally {
      setActionState("idle");
    }
  }

  const officialLookup = businessCheck.official_lookup || {};
  const verificationComplete = Boolean(officialLookup.business_status);
  const evidenceFields = Array.isArray(businessCheck.field_results)
    ? businessCheck.field_results.filter((item) => (
      ["business_number", "business_name", "representative_name"].includes(item.field)
    ))
    : [
      {
        field: "business_number",
        label: "사업자등록번호",
        status: verificationComplete ? "verified" : "unavailable",
        official: businessCheck.formatted_business_number,
        sources: verificationComplete ? ["nts_status_lookup"] : [],
      },
      {
        field: "business_name",
        label: "상호",
        status: "needs_confirmation",
        claimed: businessCheck.business_name || invoiceContext.recipientName,
        sources: ["user_input"],
      },
      {
        field: "representative_name",
        label: "대표자명",
        status: businessCheck.representative_name ? "needs_confirmation" : "missing",
        claimed: businessCheck.representative_name,
        sources: businessCheck.representative_name ? ["user_input"] : [],
      },
    ];
  const evidenceConflictCount = businessCheck.evidence_summary?.conflicts
    ?? evidenceFields.filter((item) => item.status === "conflict").length;
  const evidenceBlocked = evidenceConflictCount > 0
    || businessCheck.workflow_status === "invalid_business_number";
  const businessName = businessCheck.business_name || invoiceContext.recipientName;
  const businessNumber = businessCheck.formatted_business_number
    || invoiceContext.recipientBusinessNumber.replace(/^(\d{3})(\d{2})(\d{5})$/, "$1-$2-$3");

  const rows = [
    ["supplyDate", formatDate(draft.supplyDate)],
    ["itemName", draft.itemName],
    ["supplyAmount", formatMoney(draft.supplyAmount)],
    ["taxAmount", formatMoney(draft.taxAmount)],
  ];

  return (
    <main className="app-shell">
      <header className="topbar">
        <button className="icon-button" type="button" aria-label="뒤로 가기" onClick={() => window.history.back()}>
          <ArrowLeft weight="regular" />
        </button>
        <strong className="brand">사업자 확인 도우미</strong>
        {loadState === "ready" && !showIssueDemo ? (
          <button className="top-action" type="button" disabled={actionState !== "idle"} onClick={saveDraft}>
            {actionState === "saving" ? "저장 중" : "임시저장"}
          </button>
        ) : <span />}
      </header>

      {loadState !== "ready" ? (
        <section className="status-page" aria-live="polite">
          {loadState === "loading" ? <CircleNotch className="loading-icon" /> : <WarningCircle />}
          <h1>{loadState === "loading" ? "확인 정보를 불러오는 중이에요" : loadState === "missing" ? "링크가 만료되었어요" : "정보를 불러오지 못했어요"}</h1>
          <p>{loadState === "loading" ? "잠시만 기다려 주세요." : loadState === "missing" ? "채팅방에서 세금계산서 발행 준비를 다시 요청해 주세요." : "네트워크 상태를 확인한 뒤 다시 시도해 주세요."}</p>
          {loadState === "error" && (
            <button className="retry-button" type="button" onClick={() => setReloadKey((value) => value + 1)}>
              <ArrowClockwise />다시 시도
            </button>
          )}
        </section>
      ) : showIssueDemo ? (
        <section className="issue-demo" aria-labelledby="issue-demo-title">
          <span className="demo-badge">DEMO</span>
          <div className="handoff-icon"><ShieldCheck weight="fill" /></div>
          <h1 id="issue-demo-title">세금계산서 발행 전 최종 확인</h1>
          <p className="issue-demo-lead">실제 발행 시스템을 연결했을 때 마지막으로 확인하는 단계예요.</p>
          <dl className="issue-demo-document">
            <div><dt>공급받는자</dt><dd>{invoiceContext.recipientName}</dd></div>
            <div><dt>사업자등록번호</dt><dd>{businessNumber}</dd></div>
            <div><dt>품목</dt><dd>{draft.itemName}</dd></div>
            <div><dt>작성일</dt><dd>{formatDate(draft.supplyDate)}</dd></div>
            <div className="issue-demo-total"><dt>최종 확인 금액</dt><dd>{formatMoney(totalAmount)}</dd></div>
          </dl>
          <p className="demo-note"><Info />현재는 연동 전 데모로, 실제 발행이나 국세청 전송은 이루어지지 않습니다.</p>
          <button className="primary-button" type="button" onClick={() => window.history.back()}>초안으로 돌아가기</button>
        </section>
      ) : <form className="page" onSubmit={submitHandoff} noValidate>
        {!referenceId && (
          <nav className="demo-switch" aria-label="Build Week 데모 시나리오">
            <span><Sparkle weight="fill" />LIVE DEMO</span>
            <div>
              <button
                aria-pressed={demoScenario === "verified"}
                type="button"
                onClick={() => selectDemoScenario("verified")}
              >일치</button>
              <button
                aria-pressed={demoScenario === "conflict"}
                type="button"
                onClick={() => selectDemoScenario("conflict")}
              >불일치 감지</button>
            </div>
          </nav>
        )}
        <section className="intro" aria-labelledby="page-title">
          <h1 id="page-title">확인하고 발행 준비하기</h1>
          <p>{evidenceConflictCount > 0 ? `AI가 서로 다른 정보 ${evidenceConflictCount}건을 찾았어요. 원본을 확인한 뒤 진행해 주세요.` : verificationComplete ? "사업자 정보 확인을 완료했어요. 세금계산서 초안을 검토해 주세요." : "사업자 기본 정보를 불러왔어요. 조회 상태와 세금계산서 초안을 확인해 주세요."}</p>
        </section>

        <section className={evidenceConflictCount > 0 ? "verification verification-alert" : "verification"} aria-labelledby="verification-title">
          <h2 id="verification-title">{evidenceConflictCount > 0 ? <WarningCircle weight="fill" /> : verificationComplete ? <CheckCircle weight="fill" /> : <Info weight="fill" />}{evidenceConflictCount > 0 ? "정보 불일치 확인 필요" : verificationComplete ? "사업자 확인 완료" : "사업자 확인 결과"}</h2>
          <dl>
            <div><dt>상호</dt><dd>{businessName}</dd></div>
            <div><dt>사업자등록번호</dt><dd>{businessNumber}</dd></div>
            <div><dt>대표자명</dt><dd>{businessCheck.representative_name || "정보 없음"}</dd></div>
            <div><dt>사업자 상태</dt><dd>{officialLookup.business_status || "조회 미완료"}</dd></div>
            <div><dt>과세 유형</dt><dd>{officialLookup.tax_type || "조회 미완료"}</dd></div>
          </dl>
          <p className="source"><ShieldCheck weight="regular" />{verificationComplete ? `${businessCheck.source || "사업자 정보"} · 방금 전` : "국세청 조회를 완료하지 못했어요"}</p>
        </section>

        <section className={evidenceConflictCount > 0 ? "evidence evidence-alert" : "evidence"} aria-labelledby="evidence-title">
          <div className="evidence-heading">
            <div>
              <span className="evidence-kicker"><Sparkle weight="fill" />GPT‑5.6 + TalkCheck</span>
              <h2 id="evidence-title">필드별 검증 근거</h2>
            </div>
            <span className={evidenceConflictCount > 0 ? "evidence-count evidence-count-alert" : "evidence-count"}>
              {evidenceConflictCount > 0 ? `불일치 ${evidenceConflictCount}` : "충돌 없음"}
            </span>
          </div>
          <p className="evidence-lead">AI가 읽은 값과 공식 조회 결과를 섞지 않고 출처별로 보여줘요.</p>
          <div className="evidence-rows">
            {evidenceFields.map((item) => {
              const status = evidenceStatusMeta[item.status] || evidenceStatusMeta.missing;
              const value = item.status === "conflict"
                ? `${item.claimed || "없음"} ↔ ${item.extracted || "없음"}`
                : item.official || item.extracted || item.claimed || "정보 없음";
              return (
                <div className="evidence-row" data-status={status.tone} key={item.field}>
                  <div className="evidence-row-icon">
                    {item.sources?.some((source) => source.startsWith("nts_")) ? <Database /> : <FileText />}
                  </div>
                  <div className="evidence-row-body">
                    <span>{item.label}</span>
                    <strong>{value}</strong>
                    <small>{(item.sources || []).map((source) => sourceLabels[source] || source).join(" · ") || "출처 없음"}</small>
                  </div>
                  <span className="evidence-status">{status.label}</span>
                </div>
              );
            })}
          </div>
          {evidenceConflictCount > 0 && businessCheck.clarifying_questions?.[0] && (
            <p className="evidence-question"><WarningCircle weight="fill" />{businessCheck.clarifying_questions[0]}</p>
          )}
        </section>

        <aside className="data-receipt" aria-label="데이터 처리 내역">
          <LockKey weight="fill" />
          <div>
            <strong>데이터 처리 내역</strong>
            <span>이미지 미보관 · 링크 30분 후 만료 · 발행 전 사용자 최종 확인</span>
          </div>
        </aside>

        <section className="invoice" aria-labelledby="invoice-title">
          <h2 id="invoice-title">세금계산서 초안</h2>
          <div className="invoice-rows">
            {rows.map(([field, value]) => (
              <button
                className="invoice-row"
                data-error={Boolean(errors[field])}
                key={field}
                type="button"
                onClick={() => openEditor(field)}
              >
                <span>{fieldMeta[field].label}</span>
                <strong>{value}</strong>
                {field === "itemName" ? <CaretRight /> : <PencilSimple />}
              </button>
            ))}
            <div className="total-row">
              <span>합계</span>
              <strong>{formatMoney(totalAmount)}</strong>
            </div>
            <button
              className="invoice-row email-row"
              data-error={Boolean(errors.recipientEmail)}
              type="button"
              onClick={() => openEditor("recipientEmail")}
            >
              <span>수신 이메일</span>
              <strong>{draft.recipientEmail || "입력 안 함"}</strong>
              <PencilSimple />
            </button>
          </div>
          {Object.entries(errors).some(([field, message]) => field !== "agreed" && Boolean(message)) && (
            <p className="inline-error" role="alert">빨간색으로 표시된 항목을 확인해 주세요.</p>
          )}
        </section>

        {!evidenceBlocked ? <section className="confirmation">
          <label className="check-row" data-error={Boolean(errors.agreed)} tabIndex={errors.agreed ? -1 : undefined}>
            <input
              type="checkbox"
              checked={agreed}
              onChange={(event) => {
                setAgreed(event.target.checked);
                if (event.target.checked) setErrors((current) => ({ ...current, agreed: undefined }));
              }}
            />
            <span className="check-control" aria-hidden="true"><Check weight="bold" /></span>
            <span>위 정보를 확인했으며, 다음 보안 화면에서 세금계산서 발행을 최종 진행합니다.</span>
          </label>
          {errors.agreed && <p className="consent-error" role="alert">{errors.agreed}</p>}
          <p className="not-issued"><Info weight="regular" />아직 세금계산서가 발행되지 않았어요</p>
        </section> : (
          <section className="blocked-handoff" role="status">
            <WarningCircle weight="fill" />
            <p><strong>발행 준비를 잠시 멈췄어요</strong><span>불일치 값을 확인하면 초안 검토를 이어갈 수 있어요.</span></p>
          </section>
        )}

        <footer className="actions">
          <button
            className={evidenceBlocked ? "primary-button review-button" : "primary-button"}
            type={evidenceBlocked ? "button" : "submit"}
            disabled={actionState !== "idle"}
            onClick={evidenceBlocked ? () => {
              if (referenceId) window.history.back();
              else setToast(businessCheck.clarifying_questions?.[0] || "불일치 정보를 먼저 확인해 주세요.");
            } : undefined}
          >
            {evidenceBlocked ? "채팅에서 불일치 확인" : actionState === "preparing" ? "확인 화면 준비 중" : "발행 화면으로 이동"}
          </button>
          <button className="secondary-button" type="button" disabled={actionState !== "idle"} onClick={leaveForLater}>나중에 하기</button>
        </footer>
      </form>}

      <dialog className="sheet" ref={editorRef} onClose={() => setEditing(null)}>
        {editing && (
          <form onSubmit={saveEditor} noValidate>
            <div className="sheet-header">
              <h2>{fieldMeta[editing].label} 수정</h2>
              <button className="icon-button" type="button" aria-label="닫기" onClick={closeEditor}><X /></button>
            </div>
            <label className="field-label" htmlFor="editor-input">{fieldMeta[editing].label}</label>
            <input
              autoFocus
              className={errors[editing] ? "field-input field-input-error" : "field-input"}
              id="editor-input"
              inputMode={fieldMeta[editing].inputMode}
              type={fieldMeta[editing].type}
              value={editValue}
              onChange={(event) => setEditValue(event.target.value)}
            />
            {errors[editing] && <p className="field-error" role="alert">{errors[editing]}</p>}
            <button className="primary-button sheet-save" type="submit">변경사항 저장</button>
          </form>
        )}
      </dialog>

      {toast && <div className="toast" role="status">{toast}</div>}
    </main>
  );
}
