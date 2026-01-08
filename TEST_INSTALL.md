# 설치 테스트 가이드

새로운 사용자 경험을 시뮬레이션하기 위한 테스트 절차입니다.

## 방법 1: uv 사용 (권장 - 빠름!)

### 1. uv 설치 확인
```bash
# uv가 설치되어 있는지 확인
uv --version

# 없으면 설치
curl -LsSf https://astral.sh/uv/install.sh | sh
# 또는
pip install uv
```

### 2. 프로젝트로 이동
```bash
cd workshop-translator/WsTranslator
```

### 3. 의존성 설치
```bash
# uv가 자동으로 가상환경을 만들고 모든 의존성 설치
# (bedrock-agentcore, strands-agents, bedrock-agentcore-starter-toolkit 포함)
uv sync
```

### 4. Agent 설정
```bash
# uv 환경에서 실행
uv run agentcore configure --name WsTranslator_Agent
```

설정 시:
- **Agent Name**: WsTranslator_Agent (그대로 Enter)
- **Entrypoint**: (Enter를 눌러 건너뛰기)
- **Memory**: n (비활성화)

### 5. 테스트 실행

#### 5.1 CLI 명령어 확인
```bash
uv run wstranslator --help
```

#### 5.2 단일 쿼리 테스트
```bash
uv run wstranslator "안녕하세요"
```

#### 5.3 대화형 모드 테스트
```bash
uv run wstranslator
```

#### 5.4 세션 ID 테스트
```bash
uv run wstranslator --session-id test-session "첫 번째 질문"
uv run wstranslator --session-id test-session "두 번째 질문"
```

---

## 방법 2: pip 사용 (전통적인 방법)

### 1. 새 가상환경 생성

```bash
# WsTranslator 디렉토리로 이동
cd workshop-translator/WsTranslator

# 새 가상환경 생성 (테스트용)
python -m venv .venv_test

# 가상환경 활성화
source .venv_test/bin/activate  # macOS/Linux
# 또는
.venv_test\Scripts\activate  # Windows
```

### 2. 패키지 설치

```bash
# 개발 모드로 설치 (모든 의존성 포함)
pip install -e .
```

### 3. Agent 설정

```bash
# Agent 설정 (처음 한 번만)
agentcore configure --name WsTranslator_Agent
```

설정 시:
- **Agent Name**: WsTranslator_Agent (그대로 Enter)
- **Entrypoint**: (Enter를 눌러 건너뛰기)
- **Memory**: n (비활성화)

### 4. 테스트 실행

#### 4.1 CLI 명령어 확인
```bash
# wstranslator 명령어가 설치되었는지 확인
which wstranslator
wstranslator --help
```

#### 4.2 단일 쿼리 테스트
```bash
# 간단한 질문으로 테스트
wstranslator "안녕하세요"
```

#### 4.3 대화형 모드 테스트
```bash
# 대화형 모드 시작
wstranslator

# 테스트 대화:
# 사용자: 안녕하세요
# 사용자: exit
```

#### 4.4 세션 ID 테스트
```bash
# 같은 세션으로 여러 질문
wstranslator --session-id test-session "첫 번째 질문"
wstranslator --session-id test-session "두 번째 질문"
```

#### 4.5 로컬 모드 테스트 (선택사항)
```bash
# 로컬 모드 (Bedrock 직접 호출)
wstranslator --local
```

---

## 예상 결과

### 성공 케이스
- ✅ `wstranslator` 명령어가 실행됨
- ✅ Agent 응답이 깔끔하게 표시됨 (정보 패널 없음)
- ✅ 대화형 모드가 정상 작동
- ✅ 세션 ID로 컨텍스트 유지

### 실패 케이스 및 해결

#### "agentcore CLI가 설치되지 않았습니다"
```bash
pip install bedrock-agentcore strands-agents bedrock-agentcore-starter-toolkit
```

#### "Agent 'WsTranslator_Agent'가 설정되지 않았습니다"
```bash
agentcore configure --name WsTranslator_Agent
```

#### AWS 자격 증명 오류
```bash
# AWS 자격 증명 확인
aws sts get-caller-identity

# 없으면 설정
aws configure
```

---

## 테스트 완료 후 정리

### uv 사용 시
```bash
# uv가 자동으로 관리하므로 별도 정리 불필요
# 원하면 .venv 디렉토리 삭제
rm -rf .venv
```

### pip 사용 시
```bash
# 가상환경 비활성화
deactivate

# 테스트 가상환경 삭제 (선택사항)
rm -rf .venv_test
```

---

## 체크리스트

- [ ] uv 또는 가상환경 설정 완료
- [ ] 프로젝트 설치 성공
- [ ] AgentCore 도구 설치 성공
- [ ] `agentcore configure` 완료
- [ ] `wstranslator --help` 작동
- [ ] 단일 쿼리 테스트 성공
- [ ] 대화형 모드 테스트 성공
- [ ] 세션 ID 테스트 성공
- [ ] 에러 메시지가 명확하고 도움이 됨

---

## 문제 발견 시

문제를 발견하면 다음 정보를 기록해주세요:
- 실행한 명령어
- 에러 메시지 전체
- Python 버전 (`python --version`)
- OS 정보
