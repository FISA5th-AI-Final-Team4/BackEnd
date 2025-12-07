# 챗봇의 정석 BackEnd 

| 소개 | 관련 링크 |
| ------ | ------ |
| 챗봇의 정석의 고객과 소통하는 **백엔드 서버 원격 저장소**입니다.<br>FastAPI를 기반으로 로그인·페르소나 관리, LLM서버 응답 파싱 등의 **REST API**를 제공합니다.<br>`/api/chat/ws` WebSocket 엔드포인트를 통해 실시간 채팅을 처리하고, LLM 서버·MCP 서버와 연동하여 **카드 추천, FAQ/용어 검색 등 도메인 툴 호출 결과를 클라이언트에 전달**합니다.<br>PostgreSQL 기반으로 채팅 로그 및 QnA 데이터를 관리하며, Docker·Jenkins·ALB+EC2 환경에서 운영될 수 있도록 설계되었습니다. | 🔗[챗봇의 정석 프로젝트 설명 페이지](https://github.com/FISA5th-AI-Final-Team4) <br>🔗[FrontEnd 원격 저장소](https://github.com/FISA5th-AI-Final-Team4/FrontEnd) <br>🔗[LLM서버 원격 저장소](https://github.com/FISA5th-AI-Final-Team4/LLMServer) <br>🔗[MCP서버 원격 저장소](https://github.com/FISA5th-AI-Final-Team4/MCPServer) <br>🔗[DB서버 원격 저장소](https://github.com/FISA5th-AI-Final-Team4/LocalDbSetup) |

## 🧾 API 명세

토글을 열어 사용가능한 HTTP 및 WebSocket 엔드포인트의 요약 정보를 확인하세요.

<details>
<summary><strong>Health (<code>/api/health</code>)</strong></summary>

### Health

|엔드포인트|메서드|설명|요청|성공 응답|주요 오류|
|---|---|---|---|---|---|
|`/api/health`|GET|애플리케이션 상태 점검|요청 본문/파라미터 없음|`200 OK`<br>`{"status": "ok"}`|없음|

</details>

---

<details>
<summary><strong>Chat (<code>/api/chat</code>)</strong></summary>

### Chat (`/api/chat`)

|엔드포인트|메서드|설명|요청|성공 응답|주요 오류|
|---|---|---|---|---|---|
|`/api/chat/feedback`|POST|챗봇 응답(툴 호출 포함)에 대한 유용성 피드백 저장|JSON Body (`FeedbackRequest`)<br>`{ "message_id": "<uuid>", "is_helpful": true\|false\|null }`<br>(`message_id`는 사용자의 프롬프트 메시지 ID)|`200 OK`<br>`{ "status": "success", "message_id": "<uuid>", "feedback_received": true\|false\|null }`|`500`: DB 오류|

</details>

---

<details>
<summary><strong>Login (<code>/api/login</code>)</strong></summary>

### Login (`/api/login`)

|엔드포인트|메서드|설명|요청|성공 응답|주요 오류|
|---|---|---|---|---|---|
|`/api/login/`|POST|WebSocket 세션과 페르소나를 매핑하고 MCP 추천 툴 호출|JSON Body (`LoginRequest`)<br>`{ "session_id": "<uuid>", "persona_id": int }`|`200 OK` (본문 없음). 성공 시 내부적으로 MCP `consumption_recommend` 툴 호출 후 WebSocket으로 카드/추천 응답 전송|`422`: 잘못된/누락된 `session_id`<br>`404`: ConnectionManager에 세션 없음<br>`502`: MCP 호출 실패<br>`500`: DB 또는 기타 서버 오류|
|`/api/login/personas`|GET|페르소나 목록 (로그인 화면 용) 조회|없음|`200 OK`<br>`{"personas": [...]}` (`/chat/personas`와 동일)|`500`: DB/서버 오류|
|`/api/login/persona_id`|POST|주어진 세션에 연결된 페르소나 확인|JSON Body (`PersonaRequest`)<br>`{ "session_id": "<uuid>" }`|`200 OK`<br>`{ "persona_id": int\|null }`|`422`: 잘못된 세션 ID 형식<br>`404`: 세션 미존재|

</details>

---

<details>
<summary><strong>QnA (<code>/api/qna</code>)</strong></summary>

### QnA (`/api/qna`)

|엔드포인트|메서드|설명|요청|성공 응답|주요 오류|
|---|---|---|---|---|---|
|`/api/qna/faq`|GET|조회수가 높은 FAQ 상위 K건 조회 및 캐시|Query Param `top_k` (기본 3)|`200 OK`<br>`[ { "faq_id": int, "question": str, "answer": str, "views": int }, ... ]`| `500`: DB/서버 오류|
|`/api/qna/terms`|GET|조회수가 높은 금융 용어 상위 K건 조회 및 캐시|Query Param `top_k` (기본 6)|`200 OK`<br>`[ { "term_id": int, "term": str, "definition": str }, ... ]`| `500`: DB/서버 오류|

> **참고**: `faq_cache`와 `terms_cache`는 `/api/qna` 엔드포인트 호출 시 메모리에 저장되며, 이후 `/api/chat/ws`에서 FAQ·용어 질문과 정확히 일치하는 입력이 들어오면 DB 호출 대신 캐시된 답변을 즉시 반환합니다.

</details>

---

<details>
<summary><strong>WebSocket (<code>/api/chat/ws</code>)</strong></summary>

### WebSocket (`/api/chat/ws`)

|항목|내용|
|---|---|
|URL|`/api/chat/ws`|
|핸드셰이크|클라이언트가 연결하면 서버가 임의의 `session_id`를 생성하고 `{"session_id": "<uuid>"}` JSON을 즉시 전송. 이후 REST `/api/login/`을 통해 세션과 사용자 페르소나 ID를 매핑해야 개인 소비데이터 기반 카드 추천 기능 사용 가능|
|클라이언트 → 서버 메시지|JSON 문자열이어야 하며 최소 `message_id`(UUID), `message`(str)가 필요. JSON 형식 오류 시 서버가 `{"error": "Invalid JSON format"}` 전송 후 다음 메시지를 대기|
|서버 → 클라이언트 기본 응답|`{ "sender": "bot", "timestamp": "<ISO8601>", "message_id": "<uuid>", "login_required": false, "message": "<answer>", "card_list": [...?], "related_questions": [...?], "tool_name": "..." }` (`card_list`, `related_questions`, `tool_name`은 툴 호출 시에만 존재)|
|동작 흐름|1) 사용자 메시지를 DB `Chat` 테이블에 저장 → 2) FAQ/용어 캐시 히트 여부 확인 → 3) 미스일 경우 MCP Router (`LLMSERVER_URL/llm/mcp-router/dispatch`) 호출 → 4) 응답을 WebSocket으로 전송하고 `ChatbotResponse`에 툴 메타데이터 저장|
|에러 처리|LLM 호출 실패 시 `"message"`에 에러 설명을 포함한 봇 응답 전송. 기타 예외 발생 시 `{"error": "Internal Server Error: ... "}` 메시지가 내려가며 연결이 종료될 수 있음. 클라이언트가 연결 해제하면 `WebSocketDisconnect`를 기록하고 매핑을 제거|

</details>


## ⚒️ 기술 스택
- FastAPI, SQLModel/SQLAlchemy, asyncpg

  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=FastAPI&logoColor=white"/> <img src="https://img.shields.io/badge/SQLAlchemy-D71F00?style=for-the-badge&logo=SQLAlchemy&logoColor=black"> <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=PostgreSQL&logoColor=white"/> 

- uvicorn + Docker + Jenkins

    <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=Docker&logoColor=white"> <img src="https://img.shields.io/badge/uvicorn-E4CCFF?style=for-the-badge"> <img src="https://img.shields.io/badge/Jenkins-D24939?style=for-the-badge&logo=Jenkins&logoColor=FFFFFF">

- ALB + EC2

  <img src="https://img.shields.io/badge/AWS ALB-F58536?style=for-the-badge"/> <img src="https://img.shields.io/badge/AWS EC2-F58536?style=for-the-badge"/>


## 📁 프로젝트 구조

```bash
.
├── Dockerfile                     # 컨테이너 이미지를 만들기 위한 Docker 빌드 설정
├── Jenkinsfile                    # Jenkins CI/CD 파이프라인 설정
├── api                            # FastAPI 라우터 및 엔드포인트 정의
│   ├── router.py                  # 공통 APIRouter 설정 및 라우터 등록
│   └── routes                     # 개별 기능별 라우트 모듈
│       ├── chat.py                # 채팅 관련 REST API 엔드포인트
│       ├── health.py              # 헬스체크 엔드포인트
│       ├── login.py               # 로그인/세션 관련 엔드포인트
│       ├── qna.py                 # QnA 관련 엔드포인트
│       └── ws.py                  # WebSocket 채팅 엔드포인트
├── core                           # 핵심 설정 및 앱 초기화 코드
│   ├── config.py                  # 환경변수, 설정값 로딩 및 Config 객체
│   ├── db.py                      # DB 세션/엔진 설정
│   └── setup.py                   # 앱 구동 시 초기 설정/의존성 등록
├── crud                           # DB CRUD (데이터베이스 접근 로직)
│   ├── chat.py                    # 채팅 기록/세션 관련 CRUD 함수
│   ├── persona.py                 # 페르소나 관련 CRUD 함수
│   ├── qna.py                     # QnA 데이터 관련 CRUD 함수
│   └── session.py                 # 사용자 세션/토큰 관련 CRUD 함수
├── data                           # 애플리케이션이 사용하는 정적 데이터
│   └── personas.json              # 사용자 페르소나 정보 시딩 목적 JSON 데이터
├── docker-scripts                 # Docker 빌드/실행 자동화 스크립트
│   ├── build.sh                   # Docker 이미지 빌드 스크립트
│   └── run.sh                     # Docker 컨테이너 실행 스크립트
├── main.py                        # FastAPI 앱 엔트리포인트 (uvicorn 실행 대상)
├── models.py                      # ORM 모델 정의
├── requirements.in                # 의존성 원본 목록 (pip-compile 입력용)
├── requirements.txt               # 고정된 의존성 버전 목록 (배포/빌드용)
├── schemas                        # 요청·응답/도메인 스키마
│   ├── chat.py                    # 채팅 관련 요청/응답 스키마
│   ├── login.py                   # 로그인/인증 관련 스키마
│   └── persona.py                 # 페르소나 관련 스키마
└── tests                          # 테스트 코드
    ├── conftest.py                # pytest 공통 설정 및 fixture 정의
    ├── data                       # 테스트용 샘플 데이터
    │   ├── chat_history.json      # 채팅 이력 테스트 데이터
    │   └── personas.json          # 페르소나 테스트 데이터
    ├── test_dummy_chat_api.py     # 단위 테스트 (더미/기본 채팅 API 테스트)
    └── test_integration_chat_api.py # 통합 테스트 (실제 API 플로우 테스트)
```

## ⚙️ 환경 변수 & 서버 실행
- 환경 변수 (`.env`)
    ```bash
    FRONTEND_HOST=http://127.0.0.1:4173  # CORS 허용 도메인/포트
    LLMSERVER_URL=http://127.0.0.1:8000  # LLM 서버 주소
    DATABASE_URL=postgresql+asyncpg://<USER>:<PASSWORD>@<PG_URL>/ChatDB     # 채팅 로그 DB
    FAQ_DATABASE_URL=postgresql+asyncpg://<USER>:<PASSWORD>@<PG_URL>/card_qna_db # QnA DB
    HTTPX_TIMEOUT=300.0                  # LLM 응답 제한 시간 설정
    ENVIRONMENT=development              # 개발/운영 환경 설정
    MCP_SERVER_URL=http://127.0.0.1:8011 # MCP 서버 주소
    ```

- 서버 실행 
    ```bash
    docker build -t chatbot-backend . # Docker 이미지 빌드
    # Docker 컨테이너 실행
    docker run -d -p 8001:8001 --env-file .env --name chatbot-backend chatbot-backend
    ```
    - 브라우저에서 `http://127.0.0.1:8001/docs` 로 OpenAPI 문서를 확인할 수 있습니다.

- 서버 실행 (Docker 미사용)
    - `python-3.12.12`
    ```bash 
    python -m venv .venv            # 가상환경 생성
    source .venv/bin/activate       # 가상환경 활성화 (Windows: .venv\Scripts\activate)
    pip install -r requirements.txt # 의존성 설치
    uvicorn main:app --host 0.0.0.0 --port 8001 # 서버 실행
    ```