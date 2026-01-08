# Workshop Translator

AWS Workshop 문서를 자동으로 번역하는 AI Agent 기반 CLI 도구입니다.

## 설치

### 방법 1: uv (권장 - 가장 빠름!)

```bash
cd workshop-translator/WsTranslator

# 의존성 설치 (한 번만, 모든 도구 포함)
uv sync

# Agent 설정 (한 번만)
uv run agentcore configure --name WsTranslator_Agent

# 실행!
uv run wstranslator "안녕하세요"
```

### 방법 2: pip (전통적인 방법)

```bash
# 프로젝트 설치 (모든 의존성 포함)
pip install -e .

# Agent 설정 (한 번만)
agentcore configure --name WsTranslator_Agent

# 실행!
wstranslator "안녕하세요"
```

## 사용 방법

### 1. 원격 모드 (권장)

이미 배포된 AgentCore Runtime을 사용하여 실행합니다. AWS 자격 증명만 있으면 됩니다.

#### 필수 요구사항
- AWS 자격 증명 설정 (AWS CLI 또는 환경 변수)
- Agent 설정 (한 번만):
  ```bash
  # uv 사용 시
  uv run agentcore configure --name WsTranslator_Agent
  
  # pip 사용 시
  agentcore configure --name WsTranslator_Agent
  ```

#### 대화형 모드
```bash
# uv 사용 (빠름!)
uv run wstranslator

# 또는 pip 설치 후
wstranslator
```

#### 단일 쿼리
```bash
uv run wstranslator "워크샵 분석"
# 또는
wstranslator "워크샵 분석"
```

#### 세션 ID 지정 (대화 컨텍스트 유지)
```bash
uv run wstranslator --session-id my-session "첫 번째 질문"
uv run wstranslator --session-id my-session "두 번째 질문"
```

### 2. 로컬 모드

로컬에서 직접 Bedrock을 호출하여 실행합니다.

#### 필수 요구사항
- AWS 자격 증명 설정
- Bedrock 모델 접근 권한

```bash
uv run wstranslator --local
# 또는
wstranslator --local
```

## Agent 설정

처음 사용 시 Agent를 설정해야 합니다:

```bash
# uv 사용 시
uv run agentcore configure --name WsTranslator_Agent

# 또는 pip 설치 후
agentcore configure --name WsTranslator_Agent
```

설정 시 다음 정보를 입력하세요:
- **Agent Name**: WsTranslator_Agent (기본값)
- **Entrypoint**: (Enter를 눌러 건너뛰기 - 원격 Runtime 사용)
- **Memory**: 비활성화 (기본값)

## 환경 변수

다른 Agent를 사용하려면 환경 변수를 설정할 수 있습니다:

```bash
export WSTRANSLATOR_AGENT_NAME=MyCustomAgent
wstranslator
```

## 옵션

```
wstranslator [OPTIONS] [PROMPT]

옵션:
  --local              로컬 모드로 실행 (Bedrock 직접 호출)
  --agent NAME         Agent 이름 (기본값: WsTranslator_Agent)
  --session-id ID      세션 ID (대화 컨텍스트 유지)
  --region REGION      AWS 리전 (기본값: us-east-1)
  -h, --help           도움말 표시
```

## 문제 해결

### Agent not found 에러
```bash
# Agent 설정
agentcore configure --name WsTranslator_Agent
```

### agentcore CLI가 없는 경우
```bash
# 프로젝트를 다시 설치하면 모든 의존성이 포함됩니다
pip install -e .

# 또는 직접 설치
pip install bedrock-agentcore strands-agents bedrock-agentcore-starter-toolkit
```

### AWS 자격 증명 오류
```bash
# AWS CLI 설정
aws configure

# 또는 환경 변수 설정
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=us-east-1
```

## 개발자 정보

- **Runtime ARN**: `arn:aws:bedrock-agentcore:us-east-1:287870618970:runtime/WsTranslator_Agent-c5xpge73P0`
- **Agent Name**: `WsTranslator_Agent`
- **Region**: `us-east-1`
