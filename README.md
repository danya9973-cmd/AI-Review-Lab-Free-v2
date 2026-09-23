# AI Review Lab — Free API Edition

Gemini, Groq, OpenRouter의 무료 API 경로만 사용하는 로컬 웹앱입니다. 세 공급자가 같은 질문을 **독립적으로 1회씩 분석**하고, 환경변수로 지정한 공급자가 **최종 종합 1회**를 수행합니다. 정상 기본 흐름은 총 4회 호출입니다.

> 무료 API도 사용량·속도·지역·계정별 제한이 있습니다. 무료 제공과 모델 가용성은 공급자 정책에 따라 바뀔 수 있습니다.

## 빠른 시작

macOS에서는 `start.command`, Windows에서는 `start-windows.bat`을 실행하면 가상환경 생성과 설치를 자동으로 진행합니다. 첫 실행에서 만들어지는 `.env`에 API 키 3개를 넣고 다시 실행하세요. macOS가 실행을 막으면 파일을 우클릭한 뒤 **열기**를 선택하면 됩니다.

직접 설치하려면 아래 순서를 사용합니다.

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

`.env`에 `GEMINI_API_KEY`, `GROQ_API_KEY`, `OPENROUTER_API_KEY`를 입력하고 실행합니다.

```bash
python app.py
```

브라우저에서 <http://127.0.0.1:5000>을 여세요. 외부 기기에서 접속되지 않도록 앱은 `127.0.0.1`에만 바인딩됩니다.

## 기본 모델

- Gemini: `gemini-2.5-flash-lite`
- Groq: `llama-3.1-8b-instant`
- OpenRouter: `openrouter/free`

모델명은 모두 `.env`에서 바꿀 수 있습니다. Groq 기본값은 공식 지원 모델 목록에 있는 빠른 프로덕션 모델을 선택했습니다. OpenRouter의 `openrouter/free`는 요청 조건에 맞는 무료 모델로 라우팅합니다. 공급자 정책이 바뀌면 각 공식 모델 목록을 확인하고 환경변수만 수정하세요.

## 진단

키를 외부로 보내지 않고 설정만 확인:

```bash
python diagnostics.py
```

세 공급자에 각각 짧은 실제 요청 1회씩 보내 연결 확인:

```bash
python diagnostics.py --live
```

한 공급자만 확인하거나 JSON 파일로 저장할 수 있습니다.

```bash
python diagnostics.py --live --provider groq --output diagnostics-groq.json
```

웹 화면의 각 공급자 카드에도 개별 **연결 테스트** 버튼이 있습니다. 오류가 나면 HTTP 상태, 공급자 오류 유형, 요청 ID, 안전하게 잘라낸 응답 일부와 조치 힌트를 표시합니다. API 키와 Authorization 헤더는 오류 응답에 포함하지 않습니다.

## 오프라인 테스트

실제 API를 호출하지 않는 테스트입니다.

```bash
python -m unittest discover -s tests -v
```

공급자 응답 파싱, 상세 오류 처리, 키 비노출, 정확히 4회 호출되는 기본 흐름을 검사합니다.

## 보안과 개인정보

- API 키는 `.env`에만 두며 브라우저 HTML/JavaScript나 `/api/status` 응답에 포함되지 않습니다.
- `.env`는 `.gitignore`에 포함됩니다.
- 서버는 `127.0.0.1` 또는 `localhost`만 허용합니다.
- 질문과 세 분석 결과는 최종 종합 공급자를 포함한 외부 AI 서버로 전송됩니다. 개인정보·회사 기밀·비밀번호·토큰을 입력하지 마세요.
- 이 앱은 결과를 데이터베이스나 브라우저 저장소에 저장하지 않으며 응답에 `no-store`를 설정합니다.
- 공개 서버로 배포하려면 인증, CSRF 방어, 요청 제한, 비밀 관리, 로그 삭제 정책을 별도로 설계해야 합니다.

## 문제 해결

- `401`: 키가 잘못되었거나 만료되었습니다.
- `403`: 프로젝트 또는 모델 권한을 확인하세요.
- `404`: `.env`의 모델명이 현재 공급자에서 유효한지 확인하세요.
- `429`: 무료 한도/속도 제한입니다. 기다린 뒤 다시 시도하세요.
- `5xx` 또는 네트워크 오류: 공급자 상태, 인터넷 연결, 방화벽을 확인하세요.

한 공급자를 잠시 숨기려면 `ENABLE_GEMINI=false`처럼 설정할 수 있습니다. 다만 기본 Council 실행은 세 공급자가 모두 준비된 경우에만 활성화되며, 그때 예상 호출 수는 4회입니다.

## 공식 참고자료 (2026-09-20 확인)

- Gemini 모델: https://ai.google.dev/gemini-api/docs/models
- Gemini 사용 한도: https://ai.google.dev/gemini-api/docs/rate-limits
- Groq 지원 모델: https://console.groq.com/docs/models
- Groq 무료 티어 안내: https://console.groq.com/docs/billing-faqs
- OpenRouter Free Router: https://openrouter.ai/openrouter/free

## 라이선스

개인 및 내부 업무용으로 자유롭게 수정해 사용할 수 있습니다. 각 모델과 API의 별도 이용약관은 해당 공급자 정책을 따릅니다.
