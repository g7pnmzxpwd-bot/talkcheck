# 톡체크

카카오톡 안에서 받은 사업자등록번호·사업자등록증을 공식 데이터로 확인하고,
전자세금계산서 발행 확인 화면으로 넘길 초안을 준비하는 MCP 서버 골격입니다.

## 현재 범위

- 사업자번호 형식 및 체크섬 확인
- 국세청 사업자 상태·과세유형 조회
- HTTPS 이미지 또는 OCR 텍스트에서 사업자등록증 기본 필드 추출
- 국세청 사업자등록정보 진위확인
- 정발행 세금계산서 초안 검증
- 외부 ASP 발행 확인 화면 연동 경계
- 별도 발행확인 백엔드에 초안을 POST하고 opaque 링크만 받는 연결 규격
- 사업자 확인 결과와 세금계산서 초안을 함께 검토하는 모바일 확인 화면 프로토타입
- 카카오채널 Skill 요청에서 사업자번호·보안전송 이미지를 감지하는 대화 어댑터
- 사업자 확인 뒤 세금계산서 필수 항목을 한 항목씩 받는 30분 임시 대화 세션

다음 기능은 아직 구현하지 않았습니다.

- 전자세금계산서 ASP 연동
- PDF 등록증 업로드
- 카카오 AI 챗봇 콜백
- 실제 세금계산서 발행·전송

톡체크는 안전 여부를 판단하거나 점수를 만들지 않습니다. 조회 결과와 출처만
반환하며, 세금계산서는 외부 화면에서 사용자가 최종 확인한 뒤 발행하도록 설계합니다.

## 도구

### `check_business_registration`

사업자번호의 형식·체크섬과 국세청 상태를 조회합니다.

### `scan_business_certificate`

사업자등록증 이미지 URL 또는 이미 추출된 OCR 텍스트를 받아 기본 정보를 추출하고
상태·진위확인 결과를 반환합니다. Docker 실행 시 한국어 Tesseract OCR을 사용합니다.
이미지는 메모리에서만 처리하며, HTTPS 공개 URL·8MB 이하 이미지로 제한합니다.

### `prepare_tax_invoice_handoff`

공급받는자와 거래정보로 정발행 초안을 만들고 외부 확인 화면 이관을 준비합니다.
이 도구는 세금계산서를 발행하지 않습니다.

## 카카오채널 Skill

챗봇 관리자센터의 Skill URL을 `POST /kakao/skill`로 연결합니다. 어댑터는
카카오 Skill payload의 `userRequest.utterance`, `action.clientExtra`, 이미지
보안전송 플러그인의 `action.params.secureimage`를 처리합니다.

- 사업자번호는 즉시 조회하지 않고 `조회하기` 확인을 먼저 받습니다.
- 등록증 사진은 이미지 제공 동의가 확인된 경우에만 OCR을 실행합니다.
- 세금계산서는 상호·품목·공급가액·작성일·이메일·청구/영수를 순서대로 받은 뒤
  발행 확인 링크를 반환합니다.
- 대화 상태는 프로세스 메모리에 30분간만 유지됩니다.

카카오 Skill 서버는 공중망 HTTPS 주소가 필요하므로 로컬 URL은 챗봇 관리자센터에
직접 등록할 수 없습니다. 이미지 보안전송 플러그인의 파라미터명은
`secureimage`로 설정합니다.

## 실행

```bash
cp .env.example .env
uv sync
uv run talkcheck
```

MCP 엔드포인트는 기본적으로 `http://localhost:8000/mcp`입니다.

```bash
npx -y @modelcontextprotocol/inspector
```

발행 확인 화면 프로토타입은 별도로 실행합니다.

```bash
cd handoff-ui
npm install
npm run dev
```

프로토타입은 입력 수정·검증·임시저장·동의·발행 화면 이관 전 확인 상태를
동작으로 보여주며, 실제 세금계산서를 발행하지 않습니다.

MCP와 확인 화면을 로컬에서 함께 시험하려면 프런트엔드를 빌드하고 short-lived
handoff 모드로 서버를 실행합니다. 생성된 opaque 링크는 30분 뒤 만료되고 서버를
재시작하면 사라집니다.

```bash
cd handoff-ui
npm run build
cd ..
TAX_INVOICE_HANDOFF_MODE=local uv run talkcheck
```

운영 환경에서는 `TAX_INVOICE_HANDOFF_API_URL`과
`TAX_INVOICE_HANDOFF_API_TOKEN`으로 HTTPS 발행확인 백엔드를 연결합니다.

## Render 배포

저장소 루트의 `render.yaml` Blueprint는 Python 서버와 확인 화면을 하나의 Docker
웹 서비스로 배포합니다. 서울과 가까운 Singapore 리전과 무료 플랜을 기본으로
사용하며 `/health`를 상태 확인 경로로 설정합니다.

Render가 제공하는 `RENDER_EXTERNAL_URL`을 확인 화면의 공개 주소로 자동 사용합니다.
Blueprint 적용 시 `DATA_GO_KR_API_KEY`만 비밀 환경변수로 입력하면 됩니다.

## Agentic Player 10 예선 제출

공모전 제출 경로는 카카오채널 Skill이 아니라 PlayMCP의 Remote MCP 연결입니다.
제출용 서버는 PlayMCP in KC에서 이 저장소의 `Dockerfile`을 Git 소스 빌드하고,
발급된 Endpoint의 `/mcp` 주소를 PlayMCP 개발자 콘솔에 등록합니다.

1. PlayMCP in KC에서 비공개 Git 저장소 URL과 branch/ref를 입력합니다.
2. 저장소 루트의 `Dockerfile`로 서버를 빌드합니다.
3. 발급된 Endpoint URL 뒤에 `/mcp`를 붙여 PlayMCP에서 정보를 불러옵니다.
4. 먼저 임시 등록하고 AI 채팅에서 도구 선택과 인자 연결을 시험합니다.
5. 테스트 완료 후 심사를 요청하고, 승인되면 전체 공개로 전환합니다.

도구 호출은 `PLAYMCP_TOOL_TIMEOUT_SECONDS`로 제한하며 기본값은 2.8초입니다.
모든 도구는 PlayMCP 필수 annotations를 명시하고 실제 발행 없이 조회와 초안
준비만 수행합니다. 실제 세금계산서 발행과 Kakao Tools Widget은 예선 범위에
포함하지 않습니다.

PlayMCP in KC 공개 가이드에는 런타임 비밀 환경변수 입력 방법이 명시되어 있지
않습니다. `DATA_GO_KR_API_KEY`를 이미지나 Git 저장소에 포함하지 말고, 배포 화면의
비밀 환경변수 지원 여부를 확인한 뒤 입력해야 합니다.

## 테스트

```bash
uv run python -m unittest discover -s tests -v
```

## 다음 연동 순서

1. PlayMCP 임시 등록에서 첨부 이미지 URL 전달을 검증합니다.
2. 실제 사업자등록증 사진으로 OCR 정확도 샘플을 측정합니다.
3. 전자세금계산서 ASP 테스트 계정을 연결해 opaque handoff URL 다음 단계를 완성합니다.
4. Kakao Tools 전용 위젯을 구현합니다.
