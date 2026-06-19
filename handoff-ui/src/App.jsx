import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowLeft,
  ArrowClockwise,
  CaretRight,
  Check,
  CheckCircle,
  CircleNotch,
  Info,
  PencilSimple,
  ShieldCheck,
  WarningCircle,
  X,
} from "@phosphor-icons/react";

const demoRecord = {
  draft: {
    recipient_business_number: "1234567890",
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
    formatted_business_number: "123-45-67890",
    official_lookup: {
      business_status: "계속사업자",
      tax_type: "부가가치세 일반과세자",
    },
    source: "국세청 조회",
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
  const match = window.location.pathname.match(/^\/handoff\/([^/]+)$/);
  return match && match[1] !== "demo" ? decodeURIComponent(match[1]) : "";
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
  const [loadState, setLoadState] = useState(referenceId ? "loading" : "ready");
  const [reloadKey, setReloadKey] = useState(0);
  const [actionState, setActionState] = useState("idle");
  const [editing, setEditing] = useState(null);
  const [editValue, setEditValue] = useState("");
  const [agreed, setAgreed] = useState(false);
  const [errors, setErrors] = useState({});
  const [toast, setToast] = useState("");
  const [handoffOpen, setHandoffOpen] = useState(false);
  const editorRef = useRef(null);
  const handoffRef = useRef(null);

  useEffect(() => {
    if (!referenceId) return undefined;
    let cancelled = false;
    setLoadState("loading");
    requestJson(`/api/handoffs/${encodeURIComponent(referenceId)}`)
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
    if (handoffOpen && handoffRef.current && !handoffRef.current.open) handoffRef.current.showModal();
  }, [handoffOpen]);

  function openEditor(field) {
    setEditing(field);
    setEditValue(draft[field]);
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
        await requestJson(`/api/handoffs/${encodeURIComponent(referenceId)}`, {
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
    const nextErrors = validate(draft, agreed);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) {
      window.setTimeout(() => document.querySelector("[data-error='true']")?.focus(), 0);
      return;
    }
    if (!referenceId) {
      setHandoffOpen(true);
      return;
    }
    setActionState("preparing");
    try {
      await requestJson(`/api/handoffs/${encodeURIComponent(referenceId)}/prepare`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ draft: apiDraft() }),
      });
      setHandoffOpen(true);
    } catch (error) {
      if (error.status === 404) setLoadState("missing");
      else setToast("발행 확인 화면을 준비하지 못했어요. 다시 시도해 주세요.");
    } finally {
      setActionState("idle");
    }
  }

  function closeHandoff() {
    handoffRef.current?.close();
    setHandoffOpen(false);
    setToast(referenceId ? "외부 발행 확인 전 단계까지 준비했어요." : "발행 확인 화면 연결 전 데모까지 완료했어요.");
  }

  const officialLookup = businessCheck.official_lookup || {};
  const verificationComplete = Boolean(officialLookup.business_status);
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
        <strong className="brand">톡체크</strong>
        {loadState === "ready" ? (
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
      ) : <form className="page" onSubmit={submitHandoff} noValidate>
        <section className="intro" aria-labelledby="page-title">
          <h1 id="page-title">확인하고 발행 준비하기</h1>
          <p>{verificationComplete ? "사업자 정보 확인을 완료했어요. 세금계산서 초안을 검토해 주세요." : "사업자 기본 정보를 불러왔어요. 조회 상태와 세금계산서 초안을 확인해 주세요."}</p>
        </section>

        <section className="verification" aria-labelledby="verification-title">
          <h2 id="verification-title">{verificationComplete ? <CheckCircle weight="fill" /> : <Info weight="fill" />}{verificationComplete ? "사업자 확인 완료" : "사업자 확인 결과"}</h2>
          <dl>
            <div><dt>상호</dt><dd>{businessName}</dd></div>
            <div><dt>사업자등록번호</dt><dd>{businessNumber}</dd></div>
            <div><dt>대표자명</dt><dd>{businessCheck.representative_name || "정보 없음"}</dd></div>
            <div><dt>사업자 상태</dt><dd>{officialLookup.business_status || "조회 미완료"}</dd></div>
            <div><dt>과세 유형</dt><dd>{officialLookup.tax_type || "조회 미완료"}</dd></div>
          </dl>
          <p className="source"><ShieldCheck weight="regular" />{verificationComplete ? `${businessCheck.source || "사업자 정보"} · 방금 전` : "국세청 조회를 완료하지 못했어요"}</p>
        </section>

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

        <section className="confirmation">
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
        </section>

        <footer className="actions">
          <button className="primary-button" type="submit" disabled={actionState !== "idle"}>
            {actionState === "preparing" ? "확인 화면 준비 중" : "발행 화면으로 이동"}
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

      <dialog className="sheet handoff-sheet" ref={handoffRef} onClose={() => setHandoffOpen(false)}>
        <div className="handoff-icon"><ShieldCheck weight="fill" /></div>
        <h2>발행 확인 화면을 준비했어요</h2>
        <p>실제 ASP 연동 후에는 암호화된 외부 화면에서 인증하고 최종 발행하게 됩니다.</p>
        <div className="handoff-summary"><span>최종 확인 금액</span><strong>{formatMoney(totalAmount)}</strong></div>
        <p className="demo-note"><Info />현재는 연동 전 데모로, 세금계산서가 발행되지 않습니다.</p>
        <button className="primary-button sheet-save" type="button" onClick={closeHandoff}>확인</button>
      </dialog>

      {toast && <div className="toast" role="status">{toast}</div>}
    </main>
  );
}
